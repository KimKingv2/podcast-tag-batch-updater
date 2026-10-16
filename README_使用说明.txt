Podcast 音频标签批量更新工具 v2.1（Windows）
========================================

一、文件夹怎么摆放

把本工具的 .py 和 .bat 文件放在播客总目录中，每个 Podcast 单独一个文件夹，并在节目文件夹中放入 podcast.json：

播客总目录\
  一键更新标签.bat
  预览标签.bat
  update_podcast_tags.py
  节目A\
    podcast.json
    cover.jpg
    01 - 第一集.mp3
    02 - 第二集.mp3
    episodes.csv                 （可选）
    podcast_track_state.json     （程序首次正式更新时自动生成）
  节目B\
    podcast.json
    cover.png
    第001集.m4a

也可以让节目文件夹中有按年份/季节划分的子文件夹。程序会递归处理；若子文件夹本身也有 podcast.json，则归子文件夹自己的配置处理。

二、编辑 podcast.json

示例：
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

常用字段说明：
- album：专辑/节目名
- artist：艺术家/主播
- album_artist：专辑艺术家/节目制作方
- genre：流派
- date：日期或年份
- publisher：发行方
- comment：备注
- composer、copyright、grouping、subtitle 也可设置
- cover：封面文件名或相对路径。支持 JPG/JPEG/PNG。若省略，会自动寻找 cover.jpg、cover.png、folder.jpg、front.jpg 等常见名称；找不到时就不改封面。
- track_numbering：auto 表示自动写曲目编号；none 表示不更改已有曲目编号。
- track_number_start：首次建立编号记录时的起始编号，默认 1。如果之前已经手工删除过 1-10 集，而且从没让本工具记录过旧编号，可先设为 11。
- track_sort_order：新文件的编号排序方式。filename 按文件名自然排序（默认，推荐文件名本来就含集数时使用）；modified 按文件修改时间从早到晚排序，适合下载时间戳能反映下载顺序的情况。修改时间相同则按文件名自然排序。
- title_from_filename：true 表示用文件名（不含扩展名）覆盖标题；false 表示保留各集原有标题。

三、重要：连续编号是怎么实现的

正式更新时，程序会在每个节目目录自动建立 podcast_track_state.json，用来记住“文件相对路径 -> 曲目编号”的对应关系。此记录会保留已经删除的旧文件，因此：

1. 第一次正式更新 1-10 集时，记录编号 1-10。
2. 听完后删掉这 10 个音频，但不要删除 podcast_track_state.json。
3. 下载第 11-15 集并运行更新，程序会给新文件接着编号 11-15，而不是从 1 重新开始。
4. 重复运行不会给同一批文件重复分配新编号。

曲目标签只写单个编号，例如 1、2、3……10，或续号后的 11、12、13……。不会写入斜杠后的总集数，因为播客库可能持续新增，程序也无法预先知道最终总数。

注意：如果某个节目以前从未用本工具建立编号记录，而 1-10 集已经被删掉，程序无法凭空知道曾经有 10 集。此时请在第一次运行前手动把 track_number_start 设为 11，或从现有文件标签中自行确认应从哪个编号开始。编号记录应与音频库一起备份；不要随手删除它，否则程序会失去历史编号。

编号记录用相对路径识别文件。尽量不要把一个新节目覆盖到和旧节目完全相同的文件名上，否则它会被视为之前的同一文件并复用旧编号。若节目文件名经常重复，建议先改成包含集数/标题的唯一文件名。

四、排序建议

优先推荐 filename：当文件名中包含集数或日期时，文件名自然排序通常比文件修改时间更稳定，比如“第9集.mp3”会排在“第10集.mp3”前面。

如果下载器保存的文件名没有集数，而修改时间确实就是下载时间，可以改为：
  "track_sort_order": "modified"

程序会按文件修改时间从早到晚给“新发现的文件”分配连续编号。要注意，有些下载器、解压工具、同步软件或复制操作会保留/重写时间戳，因此修改时间不一定等于真实下载顺序。如果多个文件的时间相同，程序会用文件名排序作为次级规则。想要最可靠的结果，可让文件名保留集数或下载顺序，或使用 episodes.csv 手动指定个别集的 track_number。

五、可选的 episodes.csv

如果不同集还需要单独设置标题、日期或备注，可在节目文件夹放 episodes.csv，UTF-8 编码。至少要有 file 列；其值可用文件名，也可用节目目录内的相对路径。

示例：
file,title,date,comment
01 - 第一集.mp3,第一集：入门,2025-01-02,正式版
02 - 第二集.mp3,第二集：进阶,2025-01-09,正式版

支持列：title、artist、album、album_artist、genre、date、publisher、comment、composer、copyright、grouping、subtitle、track_number、disc_number。episodes.csv 的非空值会覆盖 podcast.json 的对应值和自动曲目编号。用 !CLEAR 可清除单集对应标签。

六、如何运行

1. 先双击“预览标签.bat”，检查日志中的节目、文件、标签和封面是否正确。预览不会保存编号记录，也不会修改音频。
2. 确认无误后双击“一键更新标签.bat”，输入 Y。
3. 运行结果会写入 podcast_tag_update_log.txt；正式运行时也会生成/更新每个节目的 podcast_track_state.json。

首次运行时，脚本会尝试通过 Python 的 pip 自动安装 mutagen。需要 Windows 上已安装 Python 3，并且能访问 pip 软件源。

如果不想在脚本所在目录运行，也可以在命令行执行：
  python update_podcast_tags.py --dry-run --root "D:\My Podcasts"
  python update_podcast_tags.py --apply --root "D:\My Podcasts"

如希望写入前复制完整原音频作为备份，可以在命令行添加 --backup。备份放在每个节目目录的 __tag_backup__\时间戳\ 中，会额外占用约一份音频文件的磁盘空间。默认不复制音频，以免播客库体积翻倍。

七、支持范围与注意事项

支持 MP3、M4A/M4B/MP4、FLAC、OGG Vorbis、Opus、WAV、AIFF 的常见标签和封面写入。不同格式能存储的字段不完全一样，个别播放器对标签字段的显示方式也可能不同。

程序只修改元数据/标签和内嵌封面，不会重新编码音频内容。仍建议先预览，并先对少量副本试运行。当前版本不会自动读取 RSS，也不会下载封面；所有信息由你在文件夹配置中指定。
