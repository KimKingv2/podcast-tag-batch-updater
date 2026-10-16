#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch-update podcast tags with persistent per-show episode numbering."""
from __future__ import annotations

import argparse
import base64
import csv
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from mutagen import File as MutagenFile
    from mutagen.flac import FLAC, Picture
    from mutagen.id3 import (
        APIC, COMM, TALB, TCOM, TCON, TCOP, TDRC, TIT1, TIT2, TIT3,
        TPE1, TPE2, TPUB, TRCK, TPOS, ID3,
    )
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4, MP4Cover
    from mutagen.oggopus import OggOpus
    from mutagen.oggvorbis import OggVorbis
    from mutagen.wave import WAVE
    from mutagen.aiff import AIFF
except ImportError:
    print("缺少依赖 mutagen。请运行 setup.bat，或执行：python -m pip install mutagen")
    raise SystemExit(2)

AUDIO_EXTS = {
    ".mp3", ".m4a", ".m4b", ".mp4", ".flac", ".ogg", ".opus",
    ".wav", ".wave", ".aif", ".aiff",
}
COVER_NAMES = ("cover.jpg", "cover.jpeg", "cover.png", "folder.jpg", "folder.png", "front.jpg", "front.png")
TRACK_STATE_NAME = "podcast_track_state.json"
CLEAR_TOKEN = "!CLEAR"

# JSON/CSV field name -> canonical name for Vorbis/MP4/ID3 handling.
TEXT_FIELDS = {
    "title", "artist", "album", "album_artist", "genre", "date",
    "publisher", "comment", "composer", "copyright", "grouping", "subtitle",
}
FIELD_ALIASES = {
    "year": "date",
    "albumartist": "album_artist",
    "album artist": "album_artist",
    "track": "track_number",
    "tracknumber": "track_number",
    "disc": "disc_number",
    "discnumber": "disc_number",
}
ID3_FRAMES = {
    "title": ("TIT2", TIT2),
    "artist": ("TPE1", TPE1),
    "album": ("TALB", TALB),
    "album_artist": ("TPE2", TPE2),
    "genre": ("TCON", TCON),
    "date": ("TDRC", TDRC),
    "publisher": ("TPUB", TPUB),
    "composer": ("TCOM", TCOM),
    "copyright": ("TCOP", TCOP),
    "grouping": ("TIT1", TIT1),
    "subtitle": ("TIT3", TIT3),
    "track_number": ("TRCK", TRCK),
    "disc_number": ("TPOS", TPOS),
}
VORBIS_KEYS = {
    "title": "TITLE", "artist": "ARTIST", "album": "ALBUM",
    "album_artist": "ALBUMARTIST", "genre": "GENRE", "date": "DATE",
    "publisher": "PUBLISHER", "comment": "COMMENT", "composer": "COMPOSER",
    "copyright": "COPYRIGHT", "grouping": "GROUPING", "subtitle": "SUBTITLE",
    "track_number": "TRACKNUMBER", "disc_number": "DISCNUMBER",
}
MP4_KEYS = {
    "title": "\xa9nam", "artist": "\xa9ART", "album": "\xa9alb",
    "album_artist": "aART", "genre": "\xa9gen", "date": "\xa9day",
    "publisher": "\xa9pub", "comment": "\xa9cmt", "composer": "\xa9wrt",
    "copyright": "cprt", "grouping": "\xa9grp", "subtitle": "desc",
}


def natural_key(value: str):
    return [(0, int(part)) if part.isdigit() else (1, part.casefold()) for part in re.split(r"(\d+)", value)]


def normalize_field(name: str) -> str:
    key = name.strip().casefold().replace("-", "_")
    return FIELD_ALIASES.get(key, key)


def clean_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value.upper() == CLEAR_TOKEN:
            return CLEAR_TOKEN
        if value == "":
            return None
        return value
    return str(value)


def load_config(config_path: Path) -> dict[str, Any]:
    try:
        obj = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 格式错误：第 {exc.lineno} 行，第 {exc.colno} 列：{exc.msg}") from exc
    if not isinstance(obj, dict):
        raise ValueError("podcast.json 最外层必须是 JSON 对象")
    return obj


def get_cover(show_dir: Path, config: dict[str, Any]) -> Path | None:
    configured = config.get("cover")
    if isinstance(configured, str) and configured.strip():
        cover = (show_dir / configured.strip()).resolve()
        if not cover.is_file():
            raise ValueError(f"配置的封面不存在：{configured}")
        return cover
    for name in COVER_NAMES:
        candidate = show_dir / name
        if candidate.is_file():
            return candidate
    return None


def discover_show_audio(show_dir: Path, all_config_dirs: set[Path]) -> list[Path]:
    files: list[Path] = []
    for path in show_dir.rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in AUDIO_EXTS:
            continue
        # A nested folder with its own podcast.json belongs to that nested show, not this one.
        if any(parent in all_config_dirs and parent != show_dir for parent in path.parents):
            continue
        if any(part.startswith(".") or part in {"__tag_backup__", "__pycache__"} for part in path.relative_to(show_dir).parts):
            continue
        files.append(path)
    return sorted(files, key=lambda p: natural_key(p.relative_to(show_dir).as_posix()))


def sort_audio_files(files: list[Path], show_dir: Path, mode: str) -> list[Path]:
    """Sort files for assigning numbers to newly discovered episodes."""
    mode = mode.strip().casefold()
    if mode in {"filename", "name", "natural"}:
        return sorted(files, key=lambda p: natural_key(p.relative_to(show_dir).as_posix()))
    if mode in {"modified", "mtime", "download_time"}:
        # Oldest modification time first; filename is a deterministic tie-breaker.
        return sorted(
            files,
            key=lambda p: (p.stat().st_mtime, natural_key(p.relative_to(show_dir).as_posix())),
        )
    raise ValueError("track_sort_order 只能填写 filename 或 modified")


def load_track_state(show_dir: Path) -> tuple[dict[str, Any], bool]:
    """Load persistent episode numbers, including entries for deleted files."""
    state_path = show_dir / TRACK_STATE_NAME
    if not state_path.exists():
        return {"version": 1, "assignments": {}}, False
    try:
        state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"编号记录 {TRACK_STATE_NAME} 无法读取：{exc}") from exc
    if not isinstance(state, dict) or not isinstance(state.get("assignments", {}), dict):
        raise ValueError(f"编号记录 {TRACK_STATE_NAME} 格式无效")
    assignments: dict[str, int] = {}
    for rel, number in state.get("assignments", {}).items():
        try:
            n = int(number)
        except (TypeError, ValueError):
            continue
        if n >= 1:
            assignments[str(rel).replace("\\", "/").casefold()] = n
    state["assignments"] = assignments
    state.setdefault("version", 1)
    return state, True


def save_track_state(show_dir: Path, state: dict[str, Any]) -> None:
    """Write state atomically so a partial write does not destroy numbering history."""
    target = show_dir / TRACK_STATE_NAME
    temporary = show_dir / (TRACK_STATE_NAME + ".tmp")
    state["last_updated"] = datetime.now().isoformat(timespec="seconds")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)


def track_key(path: Path, show_dir: Path) -> str:
    return path.relative_to(show_dir).as_posix().casefold()


def load_episode_overrides(show_dir: Path) -> dict[str, dict[str, str]]:
    csv_path = show_dir / "episodes.csv"
    if not csv_path.exists():
        return {}
    result: dict[str, dict[str, str]] = {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "file" not in {h.strip().casefold() for h in reader.fieldnames if h}:
            raise ValueError("episodes.csv 必须有 file 列，值为文件名或相对路径")
        file_header = next(h for h in reader.fieldnames if h and h.strip().casefold() == "file")
        for row in reader:
            raw_file = (row.get(file_header) or "").strip()
            if not raw_file:
                continue
            key = raw_file.replace("\\", "/").casefold()
            overrides: dict[str, str] = {}
            for header, raw_value in row.items():
                if not header or header == file_header:
                    continue
                field = normalize_field(header)
                if field not in TEXT_FIELDS | {"track_number", "disc_number"}:
                    continue
                value = clean_value(raw_value)
                if value is not None:
                    overrides[field] = value
            result[key] = overrides
    return result


def locate_override(path: Path, show_dir: Path, overrides: dict[str, dict[str, str]]) -> dict[str, str]:
    rel = path.relative_to(show_dir).as_posix().casefold()
    return overrides.get(rel, overrides.get(path.name.casefold(), {}))


def id3_set(tags, field: str, value: str | None) -> None:
    if field == "comment":
        tags.delall("COMM")
        if value and value != CLEAR_TOKEN:
            tags.add(COMM(encoding=3, lang="eng", desc="", text=[value]))
        return
    if field == "track_number":
        frame_id, frame_cls = ID3_FRAMES[field]
    elif field == "disc_number":
        frame_id, frame_cls = ID3_FRAMES[field]
    else:
        if field not in ID3_FRAMES:
            return
        frame_id, frame_cls = ID3_FRAMES[field]
    tags.delall(frame_id)
    if value and value != CLEAR_TOKEN:
        tags.add(frame_cls(encoding=3, text=[value]))


def apply_common_fields(audio, fields: dict[str, str]) -> None:
    """Apply textual tags, preserving any fields not specified in config/CSV."""
    if not fields:
        return
    if isinstance(audio, (MP3, WAVE, AIFF)):
        if audio.tags is None:
            audio.add_tags()
        for field, value in fields.items():
            id3_set(audio.tags, field, value)
        return

    if isinstance(audio, MP4):
        if audio.tags is None:
            audio.add_tags()
        tags = audio.tags
        for field, value in fields.items():
            if field in {"track_number", "disc_number"}:
                key = "trkn" if field == "track_number" else "disk"
                if value == CLEAR_TOKEN:
                    tags.pop(key, None)
                elif value:
                    num = int(value.split("/", 1)[0])
                    total = int(value.split("/", 1)[1]) if "/" in value and value.split("/", 1)[1].isdigit() else 0
                    tags[key] = [(num, total)]
                continue
            key = MP4_KEYS.get(field)
            if not key:
                continue
            if value == CLEAR_TOKEN:
                tags.pop(key, None)
            elif value:
                tags[key] = [value]
        return

    if isinstance(audio, (FLAC, OggVorbis, OggOpus)):
        if audio.tags is None:
            audio.add_tags()
        tags = audio.tags
        for field, value in fields.items():
            key = VORBIS_KEYS.get(field)
            if not key:
                continue
            if value == CLEAR_TOKEN:
                tags.pop(key, None)
            elif value:
                tags[key] = [value]
        return

    raise ValueError(f"暂不支持此音频封装/标签类型：{type(audio).__name__}")


def set_cover(audio, cover_bytes: bytes, cover_path: Path) -> None:
    suffix = cover_path.suffix.casefold()
    mime = "image/png" if suffix == ".png" else "image/jpeg"
    if isinstance(audio, (MP3, WAVE, AIFF)):
        if audio.tags is None:
            audio.add_tags()
        audio.tags.delall("APIC")
        audio.tags.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=cover_bytes))
    elif isinstance(audio, MP4):
        if audio.tags is None:
            audio.add_tags()
        imageformat = MP4Cover.FORMAT_PNG if suffix == ".png" else MP4Cover.FORMAT_JPEG
        audio.tags["covr"] = [MP4Cover(cover_bytes, imageformat=imageformat)]
    elif isinstance(audio, FLAC):
        picture = Picture()
        picture.data = cover_bytes
        picture.type = 3
        picture.mime = mime
        picture.desc = "Cover"
        picture.width = picture.height = picture.depth = 0
        picture.colors = 0
        audio.clear_pictures()
        audio.add_picture(picture)
    elif isinstance(audio, (OggVorbis, OggOpus)):
        picture = Picture()
        picture.data = cover_bytes
        picture.type = 3
        picture.mime = mime
        picture.desc = "Cover"
        picture.width = picture.height = picture.depth = 0
        picture.colors = 0
        encoded = base64.b64encode(picture.write()).decode("ascii")
        audio["metadata_block_picture"] = [encoded]
    else:
        raise ValueError(f"暂不支持给此音频类型写入封面：{type(audio).__name__}")


def set_title_from_filename(audio, path: Path) -> None:
    apply_common_fields(audio, {"title": path.stem})


def read_tags_summary(audio) -> str:
    try:
        tags = audio.tags or {}
        title = ""
        if isinstance(audio, (MP3, WAVE, AIFF)):
            vals = tags.get("TIT2")
            title = str(vals.text[0]) if vals and vals.text else ""
        elif isinstance(audio, MP4):
            vals = tags.get("\xa9nam")
            title = str(vals[0]) if vals else ""
        else:
            vals = tags.get("TITLE")
            title = str(vals[0]) if isinstance(vals, list) and vals else ""
        return f"标题={title or '（未设置/未读取）'}"
    except Exception:
        return "标签读取成功，但无法生成摘要"


def process_show(show_dir: Path, config_path: Path, all_config_dirs: set[Path], apply: bool,
                 backup: bool, log_lines: list[str]) -> tuple[int, int, int]:
    config = load_config(config_path)
    audio_files = discover_show_audio(show_dir, all_config_dirs)
    if not audio_files:
        log_lines.append(f"[跳过] {show_dir}: 没找到支持的音频文件")
        return 0, 0, 1

    cover_path = get_cover(show_dir, config)
    cover_bytes = cover_path.read_bytes() if cover_path else None
    overrides = load_episode_overrides(show_dir)

    fields: dict[str, str] = {}
    for key, value in config.items():
        field = normalize_field(key)
        if field in TEXT_FIELDS:
            cleaned = clean_value(value)
            if cleaned is not None:
                fields[field] = cleaned

    title_from_filename = bool(config.get("title_from_filename", False))
    track_mode = str(config.get("track_numbering", "auto")).strip().casefold()
    track_start = int(config.get("track_number_start", 1))
    sort_mode = str(config.get("track_sort_order", "filename")).strip().casefold()
    if track_start < 1:
        raise ValueError("track_number_start 必须大于等于 1")
    if track_mode not in {"auto", "none", "keep", ""}:
        raise ValueError("track_numbering 只能填写 auto 或 none")
    if track_mode == "auto":
        # New files are assigned in the chosen order; existing assignments never change.
        audio_files = sort_audio_files(audio_files, show_dir, sort_mode)
        state, state_exists = load_track_state(show_dir)
        assignments: dict[str, int] = dict(state.get("assignments", {}))
        existing_max = max(assignments.values(), default=track_start - 1)
        next_number = max(track_start, existing_max + 1)
        new_files = [p for p in audio_files if track_key(p, show_dir) not in assignments]
        new_files = sort_audio_files(new_files, show_dir, sort_mode)
        for path in new_files:
            assignments[track_key(path, show_dir)] = next_number
            next_number += 1
        state["assignments"] = assignments
        max_track_number = max(assignments.values(), default=track_start)
    else:
        state, state_exists = {"version": 1, "assignments": {}}, False
        assignments = {}
        max_track_number = 0

    changed = skipped = errors = 0
    log_lines.append(f"\n=== {show_dir.name} ===")
    log_lines.append(
        f"配置：{config_path.name} | 音频：{len(audio_files)} 个 | "
        f"封面：{cover_path.name if cover_path else '不更改'} | "
        f"编号：{('连续记忆' if track_mode == 'auto' else '保留现有')} | 排序：{sort_mode if track_mode == 'auto' else '不适用'}"
    )
    if track_mode == "auto":
        log_lines.append(f"编号记录：{TRACK_STATE_NAME}（{'已读取' if state_exists else '首次建立，预览模式不会保存'}）")

    for path in audio_files:
        rel = path.relative_to(show_dir).as_posix()
        try:
            audio = MutagenFile(path)
            if audio is None:
                log_lines.append(f"[跳过] {rel}: Mutagen 无法识别")
                skipped += 1
                continue
            if not isinstance(audio, (MP3, MP4, FLAC, OggVorbis, OggOpus, WAVE, AIFF)):
                log_lines.append(f"[跳过] {rel}: 当前版本未支持 {type(audio).__name__}")
                skipped += 1
                continue

            target_fields = dict(fields)
            if title_from_filename:
                target_fields["title"] = path.stem
            if track_mode == "auto":
                track_no = assignments[track_key(path, show_dir)]
                target_fields["track_number"] = str(track_no)

            ep = locate_override(path, show_dir, overrides)
            for field, value in ep.items():
                target_fields[field] = value

            summary = ", ".join(f"{k}={v}" for k, v in target_fields.items())
            if cover_bytes is not None:
                summary += (", " if summary else "") + f"封面={cover_path.name}"
            if not apply:
                log_lines.append(f"[预览] {rel}: {summary or '没有需要改动的字段'}")
                changed += 1
                continue

            if backup:
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_root = show_dir / "__tag_backup__" / stamp
                destination = backup_root / path.relative_to(show_dir)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)
            apply_common_fields(audio, target_fields)
            if cover_bytes is not None:
                set_cover(audio, cover_bytes, cover_path)
            audio.save()
            log_lines.append(f"[完成] {rel}: {summary or '无字段更新'}")
            changed += 1
        except Exception as exc:
            log_lines.append(f"[错误] {rel}: {type(exc).__name__}: {exc}")
            errors += 1

    # Saving this small manifest is what lets numbering continue after old audio is deleted.
    if apply and track_mode == "auto":
        try:
            save_track_state(show_dir, state)
            log_lines.append(f"[编号记录] 已保存：{TRACK_STATE_NAME}（保留已删除文件的历史编号）")
        except Exception as exc:
            log_lines.append(f"[编号记录错误] {type(exc).__name__}: {exc}")
            errors += 1
    return changed, skipped, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="按每个 Podcast 文件夹中的 podcast.json 批量更新音频标签")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="真正写入标签；不加此参数时只预览")
    mode.add_argument("--dry-run", action="store_true", help="仅预览，不写入（默认）")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent,
                        help="播客总目录，默认是脚本所在目录")
    parser.add_argument("--backup", action="store_true", help="写入前复制原音频到对应节目的 __tag_backup__ 目录（占用额外磁盘空间）")
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        print(f"目录不存在：{root}")
        return 2

    config_paths = sorted(root.rglob("podcast.json"), key=lambda p: natural_key(p.as_posix()))
    config_paths = [p for p in config_paths if "__tag_backup__" not in p.parts and not any(part.startswith(".") for part in p.relative_to(root).parts)]
    if not config_paths:
        print(f"没有找到 podcast.json。请把配置文件放进每个 Podcast 文件夹。\n扫描目录：{root}")
        return 1
    config_dirs = {p.parent.resolve() for p in config_paths}
    apply = bool(args.apply)
    banner = "实际写入模式" if apply else "预览模式（不会修改任何文件）"
    log_lines = [f"Podcast 批量标签工具 v2.1 | {banner}", f"总目录：{root}", f"发现节目配置：{len(config_paths)} 份"]
    total_changed = total_skipped = total_errors = 0
    for cfg in config_paths:
        try:
            c, s, e = process_show(cfg.parent.resolve(), cfg, config_dirs, apply, args.backup, log_lines)
            total_changed += c
            total_skipped += s
            total_errors += e
        except Exception as exc:
            log_lines.append(f"[配置错误] {cfg}: {type(exc).__name__}: {exc}")
            total_errors += 1

    log_lines.extend([
        "", "=== 汇总 ===",
        f"{'已处理' if apply else '预览'}：{total_changed} 个 | 跳过：{total_skipped} 个 | 错误：{total_errors} 个",
    ])
    output = "\n".join(log_lines)
    print(output)
    report_path = root / "podcast_tag_update_log.txt"
    try:
        report_path.write_text(output + "\n", encoding="utf-8")
        print(f"\n日志已保存：{report_path}")
    except OSError as exc:
        print(f"无法写入日志：{exc}")
    if not apply:
        print("\n确认预览无误后，再运行 一键更新标签.bat 或添加参数 --apply。")
    return 1 if total_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
