# Auto-News-30-
This allows you to automatically play news 30'. It's designed to work with Classisland.
# CCTV News Auto Player \(Firefox Version\)

## Project Introduction

This is a fully automatic **CCTV News 30\-Minute auto\-play program** developed with Python \+ Selenium \+ Firefox, designed exclusively for Windows\.

It realizes one\-click automated workflow: clean background processes, launch Firefox browser, auto play video, fullscreen with keyboard simulation, timed standby, log recording, and top\-left desktop popup notification\. All file paths follow fixed standardized rules for easy deployment\.

## Core Features

- Automatically kill residual `yelin\.exe` old process

- Close all running Firefox browser processes in one click

- Press `Win \+ D` automatically to return to desktop

- Top\-left always\-on\-top popup with customizable text content

- Auto launch Firefox and access CCTV official news page

- Auto click play button \&amp; press F key for fullscreen mode

- Custom playable duration, auto close browser after countdown

- Auto save running logs to `D:/newslog` with timestamp

- Reserved system volume control via nircmd \(enable with one comment uncomment\)

- Fixed unified path rule: tools in `C:/yelintools/`, logs in `D:/newslog`

## Environment Dependencies

### Install Python Libraries

```bash
pip install pyautogui psutil selenium
```

### Runtime Requirements

- Windows System only \(hotkey, process management and nircmd are Windows exclusive\)

- Install **Mozilla Firefox Browser**

- Selenium version recommended: `\&gt;=4\.6\.0` \(built\-in driver, no manual geckodriver required\)

## Fixed Path Specifications

|Resource|Fixed Path|
|---|---|
|nircmd Tool|`C:/yelintools/nircmd\.exe`|
|Log Directory|`D:/newslog/`|
|Log File|`D:/newslog/news\.log`|

> The program will **automatically create the D:/newslog folder** if it does not exist\.
> 
> 

## File Structure

```Plain Text
news-auto-play/
├── main.py          # Main program source code
├── README.md        # Project documentation
```

## Prerequisites

1. Put `nircmd\.exe` into `C:\\yelintools\\`

2. Install the latest Mozilla Firefox browser on your PC

3. Install required Python libraries with the command above

4. Directly run `main\.py` to start

## Custom Configuration

All configurable parameters are placed at the top of the code:

- Popup text: Modify variable `POPUP\_CONTENT`

- Play duration: Adjust `PLAY\_MINUTES`

- System volume: Uncomment `vol\(80\)` and set value from 0\~100

- Video source link: Change `VIDEO\_URL`

- Player element location: Modify `XPATH\_PATH`

## Program Workflow

1. Program starts → Show top\-left always\-on\-top popup \(auto close after a few seconds\)

2. Auto clean environment: Kill old yelin process \+ all Firefox processes

3. Automatically minimize all windows and return to desktop

4. Write startup record to log file

5. Launch Firefox, maximize browser window

6. Auto enter news page, click play, simulate F key fullscreen

7. Keep playing for set minutes, auto close browser when time up

8. Write finished record to log file

## Notes

- Only compatible with **Windows**, not support Mac / Linux

- Keep network connected during runtime to load CCTV web page

- Do not modify fixed process names and default paths arbitrarily

- The program will forcibly close redundant Firefox background processes automatically

## License

This project is licensed under the **GNU General Public License v3\.0**\.

You are free to use, modify, redistribute and open\-source your derivative works under the terms of the GPLv3 license\.

> （注：文档部分内容可能由 AI 生成）
