📺 新闻自动播放器 (News Auto Player)
> 自动启动 Firefox 播放 CCTV 新闻直播，支持音量控制、定时播放、全图形化设置界面。  
> **v4.2.0** · 便携打包，即开即用。
---
✨ 功能特性
✅ 自动播放 — 使用 Selenium 控制 Firefox，打开指定新闻页面并点击播放按钮。
🔊 音量自动调节 — 集成 nircmd，一键静音/恢复，播放前设置系统音量到指定百分比。
🖥️ 全屏控制 — 支持按 `F` 键进入全屏，并可在全屏后自动隐藏状态弹窗。
💬 启动状态弹窗 — 播放时显示半透明提示窗，可自定义文字和自动关闭时间。
⏱️ 定时播放 — 可设置播放时长（分钟），到时间自动关闭浏览器。
🧹 环境清理 — 启动前自动结束指定进程（如 edge、powerpnt），并自动回到桌面。
🎨 全图形化设置界面 — 内置侧边栏导航，所有设置项即时自动保存，无需手动点击保存按钮。
📜 完整日志 — 本地保存每日日志文件，GUI 内实时滚动显示，支持日志级别着色。
🌓 深色/浅色主题 — 一键切换，适配不同光线环境。
📦 便携打包 — 通过 PyInstaller 打包为单个 EXE，解压即用。
🔗 外部联动 — 支持被 ClassIsland 等第三方工具带参数拉起，实现定时自动播报。
---
🚀 快速开始
1. 环境要求
Windows 10/11（主要开发测试平台）
Python 3.10+（若从源码运行）
Mozilla Firefox（浏览器）
geckodriver.exe（与程序放在同一目录）
2. 安装依赖（仅针对源码运行）
```bash
pip install selenium pyautogui psutil
```
> 注意：nircmd 用于音量控制，需自行下载放到工具目录，非必需。
3. 下载运行（推荐便携版）
从 Releases 下载最新的 `新闻播放器.exe`。
将 `geckodriver.exe` 放在 EXE 同目录下。
双击运行，即可看到主界面。
4. 命令行参数
```bash
app.exe play   # 启动后立即开始播放，不显示主窗口弹窗
```
---
🧩 配置说明
程序首次运行会自动生成 `config.json`，所有设置在 GUI 中修改后自动保存，无需手动编辑。
配置项	说明	默认值
`video_url`	新闻视频页面 URL	CCTV 新闻30分直播页
`play_minutes`	自动播放时长（分钟）	25
`xpath_path`	播放按钮 XPath	预置的央视播放按钮路径
`full_screen_delay`	进入全屏前的等待秒数	5
`firefox_path`	Firefox 浏览器路径	`C:\Program Files\Mozilla Firefox\firefox.exe`
`geckodriver_path`	geckodriver 路径（空则自动查找同目录）	空
`volume_enable`	是否自动调节音量	`true`
`volume_percent`	目标音量百分比	80
`tool_path`	nircmd.exe 所在目录	`C:\yelintools`
`step_use_f_key`	使用 F 键全屏（否则用浏览器 API）	`true`
`step_hide_popup`	全屏后自动隐藏弹窗	`true`
`popup_text`	弹窗显示文字（`\n` 换行）	新闻自动播放程序运行中...
`theme`	主题（`light` / `dark`）	`light`
> 完整配置项请参考 `config.json` 文件，GUI 中所有设置页均对应配置键。
---
🔗 联动适配 – ClassIsland 自动播报
本程序支持通过命令行参数 `play` 直接开始播放新闻，无需手动点击界面按钮。这使得它可以轻松与 ClassIsland（一款 Windows 课表软件）联动，实现上课/下课自动播放新闻。
在 ClassIsland 中配置触发操作
打开 ClassIsland 的 【设置】 → 【提醒】 或 【行动】 界面。
新建一个触发规则（例如：每天 19:00 执行）。
在 【执行操作】 中选择 【启动程序】（或“运行外部程序”）。
在 程序路径 中填入 `新闻播放器.exe` 的完整路径。
在 命令行参数 中输入：`play`
保存即可。
当 ClassIsland 到达设定时间，便会自动运行新闻播放器并立刻开始播放新闻，实现定时自动播报。
自定义播放时长
若希望每次自动播报的时长与默认配置不同，可以直接在 `config.json` 中修改 `play_minutes` 值，或在主界面播放设置里调整（所有更改自动保存）。
---
📖 使用指南
主界面左侧为导航栏，鼠标滚轮可滚动（窗口较小时）。
🏠 主页
显示运行状态（就绪/运行中）
开始播放 / 停止 按钮
实时日志摘要区域
🎬 播放设置
视频 URL、播放时长、播放按钮 XPath
全屏前等待时间
要清理的进程列表（英文逗号分隔）
🦊 浏览器
指定 Firefox 和 geckodriver 的路径
留空即自动检测同目录下的 geckodriver.exe
🔊 音量
启用/禁用自动音量调节
拖拽滑块设置目标音量（0-100%）
指定 nircmd.exe 所在文件夹
💬 弹窗提示
是否在播放时显示状态弹窗
自定义弹窗尺寸、文字和关闭延时
🔧 启动行为
所有流程步骤均可独立开关：
关闭指定后台进程
退回桌面（Win+D）
自动调节音量
点击播放按钮
进入全屏 → 子选项：使用 F 键全屏、全屏后隐藏弹窗（v4.2.0 新增）
启动 EXE 时自动开始播放
📋 日志
启用/禁用日志记录
设置日志目录和最大显示行数
支持清空显示内容
🎨 外观
浅色/深色主题切换
基础字号调节（需重启生效）
ℹ️ 关于
版本号、作者、许可证、路径信息
---
📦 打包为 EXE
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "新闻播放器" --icon app.ico news_player.py
```
打包后，将 `geckodriver.exe` 与生成的 EXE 放在同一目录，并创建 `tools` 文件夹存放 `nircmd.exe`（可选）。
---
❓ 常见问题
Q：启动后提示找不到 geckodriver.exe？  
A：请从 Mozilla geckodriver 下载，放在程序同目录，或在浏览器设置页手动指定路径。
Q：音量调节不起作用？  
A：需要下载 nircmd 并放在工具目录中，然后在音量设置页指定该目录。
Q：如何回到之前的旧版本？  
A：在 GitHub 仓库的 Releases 页面下载历史版本，或使用 Git 回滚到对应提交。
Q：播放时浏览器没有全屏？  
A：检查启动行为设置中“进入全屏”是否开启，并确认“使用 F 键全屏”选项已勾选。若使用 nircmd 等方式可能有延迟。
Q：ClassIsland 拉不起程序或没反应？  
A：请确保 `新闻播放器.exe` 的路径填写正确，且 ClassIsland 有权限执行外部程序。可以尝试在命令行手动运行 `新闻播放器.exe play` 验证是否正常。
---
🤝 贡献与反馈
欢迎提交 Issue 或 Pull Request。  
如有问题，请先查看 Issues 是否已有相同反馈。
---
📄 许可证
本项目采用 MIT License。
---
🙏 致谢
Selenium
pyautogui
nircmd
PyInstaller
ClassIsland – 优秀的 Windows 课表软件
---
⭐ 如果这个项目对你有帮助，欢迎点个 Star！
```
