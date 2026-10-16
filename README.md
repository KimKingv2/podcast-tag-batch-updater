# Podcast Tag Batch Updater

[简体中文](#简体中文) | [English](README.en.md)

为本地 Podcast 音频库设计的批量标签工具。每档节目维护自己的 `podcast.json` 与封面图片，运行一次脚本即可批量更新该节目目录中的音频元数据。

## 功能

- 按节目文件夹独立配置专辑名、主播、专辑艺术家、流派、日期、发行方、备注等标签。
- 将 JPG/JPEG/PNG 封面嵌入音频文件。
- 支持曲目编号连续记忆。首次处理 1–10 集后，即使删除旧音频，只要保留 `podcast_track_state.json`，新下载的集数仍可从 11 开始。
- 曲目标签只写单个整数，如 `1`、`2`、`11`，不写 `/总集数`。
- 新文件支持按文件名自然排序，或按文件修改时间（近似下载时间）排序。
- 可选 `episodes.csv` 为不同集指定独立标题、日期、曲目编号等。
- 默认预览，不写入标签；确认后再使用 `--apply`。
- 可选 `--backup` 在写入前复制音频文件。

## 系统要求

- Windows 10/11（提供 `.bat` 快捷入口）；也可在安装 Python 的其他系统上用命令行运行。
- Python 3.10 或更高版本建议。
- Python 依赖：[`mutagen`](https://mutagen.readthedocs.io/)，可运行 `python -m pip install -r requirements.txt` 安装。

## 快速开始（Windows）

1. 下载并解压项目文件。
2. 将 `update_podcast_tags.py`、`一键更新标签.bat`、`预览标签.bat` 放在你的播客总目录。播客总目录下的每档节目单独放一个文件夹。
3. 参考 `example_podcast/podcast.json`，在每档节目文件夹创建 `podcast.json`，填写该档节目的标签信息。
4. 把封面图片放在对应节目文件夹，并在 `podcast.json` 中设置 `cover`。
5. 先双击 `预览标签.bat` 检查日志，再双击 `一键更新标签.bat`，输入 `Y` 确认写入。

> `.bat` 会在缺少 `mutagen` 时尝试安装依赖，因此首次运行需要能访问 pip 软件源。也可先双击 `setup.bat` 安装依赖。

## 文件夹示例

```text
我的 Podcast/
├─ update_podcast_tags.py
├─ 预览标签.bat
├─ 一键更新标签.bat
├─ 节目 A/
│  ├─ podcast.json
│  ├─ cover.jpg
│  ├─ 01 - 第一集.mp3
│  └─ podcast_track_state.json  # 正式运行后自动生成，请保留
└─ 节目 B/
   ├─ podcast.json
   ├─ cover.png
   └─ 第001集.m4a
```

每个节目文件夹可包含子目录；如果子目录也有自己的 `podcast.json`，它会按另一档节目处理。

## 配置示例

```json
{
  "album": "科技闲聊",
  "artist": "张三、李四",
  "album_artist": "科技闲聊制作组",
  "genre": "Podcast",
  "date": "2025",
  "publisher": "独立播客",
  "comment": "从官方 RSS 下载",
  "cover": "cover.jpg",
  "track_numbering": "auto",
  "track_number_start": 1,
  "track_sort_order": "filename",
  "title_from_filename": false
}
```

字段说明、`episodes.csv` 列表、编号记忆机制和排错建议请看 [中文使用说明](README_使用说明.txt)。

## 命令行

在项目脚本所在目录：

```powershell
# 只预览，不修改音频
python update_podcast_tags.py --dry-run --root "D:\My Podcasts"

# 正式写入
python update_podcast_tags.py --apply --root "D:\My Podcasts"

# 正式写入前备份原音频（会额外占用磁盘空间）
python update_podcast_tags.py --apply --backup --root "D:\My Podcasts"
```

默认根目录为脚本所在目录。所有运行结果会写入根目录的 `podcast_tag_update_log.txt`。

## 支持的格式

MP3、M4A/M4B/MP4、FLAC、OGG Vorbis、Opus、WAV/WAVE、AIFF/AIF。不同容器支持的元数据字段会有所不同；该程序修改元数据和内嵌封面，不重新编码音频。

## 重要提醒

- 首次正式运行前先预览，并建议先用少量音频副本测试。
- `podcast_track_state.json` 保存连续编号历史。听完并删除音频时请保留该文件，并把它纳入备份。
- 如果旧集已删除且此前从未生成编号记录，程序无法推断历史编号；请在首次运行前手动设置 `track_number_start`。
- 按修改时间排序只有在下载器确实保留下载时间时才可靠。文件名中带集数时，通常更推荐 `filename`。
- 请勿将个人音频、真实的节目配置、封面或日志提交到公开仓库。仓库的 `.gitignore` 已忽略常见音频文件、状态文件、日志和配置文件（示例目录除外）。

## 许可证

MIT，见 [LICENSE](LICENSE)。

---

## 简体中文

这个项目的目标是把逐档节目手工更新标签的工作，变成“每档一份配置，全库一键处理”。欢迎提交问题反馈和改进建议。
