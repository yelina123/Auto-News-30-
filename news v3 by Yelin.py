# 放在所有导入的最前面，帮助PyInstaller识别依赖
import selenium.webdriver.firefox.webdriver
import selenium.webdriver.firefox.options
#正常导入
import pyautogui as pa
import time, os
import psutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from datetime import datetime
import tkinter as tk
from tkinter import ttk

# ======================================
# 【全部可编辑配置区 - 直接在这里改】
# ======================================
# 1. 弹窗尺寸
POPUP_WIDTH = 900      # 弹窗宽度
POPUP_HEIGHT = 400     # 弹窗高度

# 2. 播放时长（分钟）
PLAY_MINUTES = 25

# 3. 日志路径
LOG_DIR = r"D:\newslog"

# 4. 音量设置
VOLUME_ENABLE = True    # 是否开启音量调节 True/False
VOLUME_PERCENT = 80     # 音量 0~100

# 5. 固定路径
TOOL_PATH = r"C:\yelintools"
INFO_TXT_PATH = os.path.join(TOOL_PATH, "yelinav3info.txt")
NIRCMD_PATH = os.path.join(TOOL_PATH, "nircmd.exe")

# 6. 新闻页面固定配置
VIDEO_URL = "https://tv.cctv.com/lm/xw30f/"
XPATH_PATH = '//*[@id="content"]/li[1]/a'
# ======================================

LOG_PATH = os.path.join(LOG_DIR, "news.log")

# 读取弹窗文案 从 yelinav3info.txt
def get_popup_text():
    default_text = "新闻自动播放程序\n状态：启动成功，未检测到自述文件\n准备拉起Firefox浏览器"
    try:
        # 兜底编码 + 忽略非法字符，避免txt乱码/特殊符号报路径错误
        with open(INFO_TXT_PATH, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            # 过滤掉空行、空白
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            if lines:
                return "\n".join(lines)
            else:
                return default_text
    except:
        return default_text

# 日志初始化：出错自动禁用不写日志
log_enabled = False
try:
    os.makedirs(LOG_DIR, exist_ok=True)
    log_enabled = True
except:
    log_enabled = False

# ===================== 超大左上角置顶弹窗 =====================
def show_top_popup():
    text_content = get_popup_text()
    window = tk.Tk()
    window.title("程序状态")
    window.geometry(f"{POPUP_WIDTH}x{POPUP_HEIGHT}+0+0")
    window.attributes("-topmost", True)
    window.resizable(False, False)

    label = ttk.Label(
        window,
        text=text_content,
        font=("微软雅黑", 11),
        justify=tk.LEFT,        # 左上角左对齐
        wraplength=POPUP_WIDTH-40  # 自动换行宽度
    )
    # 靠左上布局，不用居中拉伸
    label.pack(anchor="nw", padx=20, pady=20)

    # 60秒自动关闭
    window.after(1620000, window.destroy)
    # 不阻塞主程序
    window.update()
# =================================================================

# ===================== 环境清理：只关 Firefox / Edge / PPT =====================
def clean_environment():
    # 需要关闭的进程列表
    kill_proc_names = ["firefox.exe", "msedge.exe", "powerpnt.exe"]

    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() in kill_proc_names:
                proc.kill()
                time.sleep(0.3)
        except:
            pass

'''    # 等待一下 返回桌面
    time.sleep(1)
    pa.hotkey('win', 'd')
    time.sleep(1) '''
# =================================================================

# ===================== 音量调节 =====================
def set_volume():
    if not VOLUME_ENABLE:
        return
    try:
        cmd = f'"{NIRCMD_PATH}" mutesysvolume 0 && "{NIRCMD_PATH}" setsysvolume {int(65535 * VOLUME_PERCENT / 100)}'
        os.system(cmd)
    except:
        pass
# ====================================================

# ===================== 拉起 Firefox 播放 =====================
def play(minutes):
    pa.PAUSE = 1
    firefox_options = Options()
    firefox_options.add_argument("--no-sandbox")
    firefox_options.add_argument("--disable-notifications")

    driver = webdriver.Firefox(options=firefox_options)
    driver.maximize_window()
    driver.implicitly_wait(15)
    driver.get(VIDEO_URL)

    try:
        play_btn = driver.find_element(By.XPATH, XPATH_PATH)
        play_btn.click()
    except:
        pass

    time.sleep(9)
    pa.press('f')
    time.sleep(minutes * 60)
    driver.quit()
# ================================================================

# ===================== 日志写入（失败自动跳过） =====================
def write_log(text):
    if not log_enabled:
        return
    try:
        dt = datetime.now().strftime('[%Y-%m-%d %H:%M:%S]')
        with open(LOG_PATH, 'a+', encoding='utf-8') as f:
            f.write(f"{dt} {text}\n")
    except:
        return

# ===================== 主程序 =====================
if __name__ == '__main__':
    show_top_popup()
    clean_environment()
    set_volume()

    write_log("------------------------------")
    write_log("程序启动")
    write_log("开始播放")

    play(PLAY_MINUTES)
    write_log("播放结束")