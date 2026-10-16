# Podcast Tag Batch Updater

A small Python utility for batch-updating metadata and embedded cover art in a local Podcast library. Each show gets its own `podcast.json`; one run processes all configured show folders.

## Features

- Set common tags per show: album/show title, artist/host, album artist, genre, date, publisher, comments, and more.
- Embed JPG/JPEG/PNG cover art.
- Persistent track numbering: after processing tracks 1–10, delete those audio files but keep `podcast_track_state.json`; the next new files can continue at 11.
- Track tags are single numbers (`1`, `2`, `11`), without a `/total` suffix.
- Sort new files by natural filename order or modification time.
- Optional `episodes.csv` for per-episode metadata.
- Preview mode by default; use `--apply` to write tags.
- Optional `--backup` before modifying files.

## Requirements

- Python 3.10+ recommended.
- Dependency: `mutagen` (`python -m pip install -r requirements.txt`).
- Windows `.bat` launchers are included; command-line usage also works on other Python-enabled systems.

## Quick start on Windows

1. Download and extract the project files.
2. Place `update_podcast_tags.py`, `Preview Tags.bat` (named `预览标签.bat`), and `一键更新标签.bat` in the root of your Podcast library.
3. Create one folder per show and add a `podcast.json` based on `example_podcast/podcast.json`.
4. Place the show’s cover image in that folder and set the `cover` key.
5. Run `预览标签.bat` first. Review `podcast_tag_update_log.txt`, then run `一键更新标签.bat` and enter `Y` to apply changes.

See [README_使用说明.txt](README_使用说明.txt) for detailed Chinese documentation and the `episodes.csv` format.

## CLI

```powershell
# Preview only
python update_podcast_tags.py --dry-run --root "D:\My Podcasts"

# Apply changes
python update_podcast_tags.py --apply --root "D:\My Podcasts"

# Back up source audio before writing tags
python update_podcast_tags.py --apply --backup --root "D:\My Podcasts"
```

Supported formats include MP3, M4A/M4B/MP4, FLAC, OGG Vorbis, Opus, WAV/WAVE, AIFF/AIF. Supported fields vary by container. The tool modifies metadata and embedded artwork, not the encoded audio stream.

**Important:** Keep `podcast_track_state.json` when deleting listened-to episodes. It stores numbering history. Preview before applying changes and test on copies first.

## License

MIT. See [LICENSE](LICENSE).
