# ╔══════════════════════════════════════════════════════════════════╗
# ║              新闻自动播放器  News Auto Player                    ║
# ║──────────────────────────────────────────────────────────────────║
# ║  作者     : (your name)                                          ║
# ║  版本     : 见下方 APP_VERSION                                   ║
# ║  描述     : 自动启动 Firefox 播放 CCTV 新闻直播，               ║
# ║             支持音量控制、弹窗提示、定时播放、全图形化设置界面。 ║
# ║  依赖     : selenium  pyautogui  psutil                          ║
# ║             geckodriver.exe 放于程序同目录 或 在设置中指定路径   ║
# ║  打包命令 : 见文件末尾注释                                       ║
# ║  许可证   : MIT                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

# ──────────────────────────────────────────────────────────────────
#  § 版本信息  ← 只需修改这里
# ──────────────────────────────────────────────────────────────────
APP_VERSION   = "4.2.0"           # 程序版本号
APP_NAME      = "新闻自动播放器"  # 程序显示名称
APP_AUTHOR    = "Yelin Jiang"       # 作者
APP_DATE      = "2026-05"         # 发布日期
APP_DESC      = (                 # 会显示在「关于」页
    "自动启动 Firefox 播放 CCTV 新闻直播。支持音量控制、启动弹窗、定时播放、\n"
    "全图形化设置界面，可打包为便携 EXE。\n"
    "特别提示：geckodriver.exe 请放在程序同目录，或在「浏览器」设置页中手动指定路径。\n"
    'https://github.com/yelina123/Auto-News-30-/'
)
APP_LICENSE   = "GPL3.0 License"

# ──────────────────────────────────────────────────────────────────
#  标准库
# ──────────────────────────────────────────────────────────────────
import os
import sys
import time
import json
import logging
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import ctypes

# ──────────────────────────────────────────────────────────────────
#  第三方库（任何一个缺失都给出友好提示而非直接崩溃）
# ──────────────────────────────────────────────────────────────────
try:
    import psutil
except ImportError:
    psutil = None  # type: ignore

try:
    import pyautogui as pa
except ImportError:
    pa = None  # type: ignore

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.firefox.options import Options as FFOptions
    from selenium.webdriver.firefox.service import Service as FFService
    _SELENIUM_OK = True
except ImportError:
    _SELENIUM_OK = False


# ══════════════════════════════════════════════════════════════════
#  § 0  路径工具
# ══════════════════════════════════════════════════════════════════

def app_dir() -> str:
    """返回 exe / .py 所在目录（兼容 PyInstaller --onefile）。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(app_dir(), "config.json")


# ══════════════════════════════════════════════════════════════════
#  § 1  DPI / 分辨率自适应
# ══════════════════════════════════════════════════════════════════

def _enable_dpi_awareness():
    """Windows：开启 Per-Monitor DPI 感知，避免系统强制缩放模糊。"""
    try:
        # Windows 8.1+
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # Windows Vista+
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

def get_scale_factor() -> float:
    """
    根据屏幕物理分辨率宽度自动决定 UI 缩放比例：
      ≥ 3840 (4K)    → 2.0
      ≥ 2560 (2K)    → 1.5
      ≥ 1920 (1080p) → 1.0
      <  1920        → 0.85
    """
    try:
        root = tk.Tk()
        root.withdraw()
        # 物理像素宽度
        w = root.winfo_screenwidth()
        root.destroy()
    except Exception:
        return 1.0

    if w >= 3840:
        return 2.0
    if w >= 2560:
        return 1.5
    if w >= 1920:
        return 1.0
    return 0.85

_enable_dpi_awareness()
SCALE = get_scale_factor()   # 全局缩放系数

def S(px: int) -> int:
    """将"标准 1080p 下的像素值"按当前屏幕缩放。"""
    return max(1, round(px * SCALE))

def FS(pt: int) -> int:
    """将"标准字号"按当前屏幕缩放。"""
    return max(8, round(pt * SCALE))


# ══════════════════════════════════════════════════════════════════
#  § 2  默认配置 & 读写
# ══════════════════════════════════════════════════════════════════

DEFAULT_CONFIG: dict = {
    # ── 播放参数
    "video_url":            "https://tv.cctv.com/lm/xw30f/",
    "play_minutes":         25,
    "xpath_path":           '//*[@id="content"]/li[1]/a',
    "full_screen_delay":    5,
    # ── 浏览器
    "firefox_path":         r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "geckodriver_path":     "",       # 空 → 自动查程序同目录
    # ── 音量
    "volume_enable":        True,
    "volume_percent":       80,
    "tool_path":            r"C:\yelintools",
    # ── 启动行为开关（用户可自由控制每个步骤）
    "step_clean_procs":     True,     # 启动前关闭指定进程
    "step_go_desktop":      True,     # 关闭进程后退到桌面
    "step_set_volume":      True,     # 自动设置音量
    "step_fullscreen":      True,     # 播放后按 F 全屏
    "step_click_play":      True,     # 点击播放按钮
    "step_hide_popup":      True,     # ★ 新增：全屏后自动隐藏弹窗
    "step_use_f_key":       True,     # ★ 新增：使用 F 按键实现全屏（默认开启）
    "autoplay_on_start":    False,    # 启动 EXE 时自动播放新闻
    # ── 状态弹窗
    "popup_enable":         True,     # 启动时弹出状态提示窗
    "popup_width":          520,
    "popup_height":         200,
    "popup_close_delay":    60,       # 秒
    "popup_text":           "新闻自动播放程序\n运行中，请勿关闭此窗口...",
    # ── 日志
    "log_enable":           True,
    "log_dir":              os.path.join(app_dir(), "logs"),
    "log_max_lines":        2000,
    # ── 清理进程列表
    "kill_procs":           "firefox.exe,msedge.exe,powerpnt.exe",
    # ── 外观
    "theme":                "light",  # light / dark
    "font_size":            10,       # 基础字号（pt，标准1080p下）
}


def load_config() -> dict:
    cfg = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved: dict = json.load(f)
            # 仅覆盖已知键，防止脏数据
            for k in DEFAULT_CONFIG:
                if k in saved:
                    cfg[k] = saved[k]
        except Exception as e:
            print(f"[配置] 读取失败，使用默认值: {e}")
    else:
        save_config(cfg)    # 首次运行 → 生成配置文件
    return cfg


def save_config(cfg: dict) -> None:
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[配置] 保存失败: {e}")


# ══════════════════════════════════════════════════════════════════
#  § 3  日志管理器
# ══════════════════════════════════════════════════════════════════

class AppLogger:
    """线程安全日志：同时写文件 + 推送 GUI 回调。"""

    def __init__(self):
        self._lg      = logging.getLogger("NewsPlayer")
        self._lg.propagate = False
        self._handler : logging.FileHandler | None = None
        self._gui_cb  = None
        self._enabled = False

    def setup(self, log_dir: str, enabled: bool, gui_cb=None):
        self._enabled = enabled
        self._gui_cb  = gui_cb
        # 移除旧 handler
        for h in self._lg.handlers[:]:
            self._lg.removeHandler(h)
            try: h.close()
            except Exception: pass
        self._handler = None

        if not enabled:
            return
        try:
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(
                log_dir,
                f"news_{datetime.now().strftime('%Y%m%d')}.log"
            )
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setFormatter(logging.Formatter(
                "[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            ))
            self._lg.setLevel(logging.INFO)
            self._lg.addHandler(fh)
            self._handler = fh
        except Exception as e:
            print(f"[日志] 初始化失败: {e}")
            self._enabled = False

    def _write(self, level: str, msg: str):
        text = f"[{level}] {msg}"
        print(text)
        if self._enabled:
            try: self._lg.info(msg)
            except Exception: pass
        if self._gui_cb:
            try: self._gui_cb(text)
            except Exception: pass

    def info (self, msg): self._write("INFO ", msg)
    def warn (self, msg): self._write("WARN ", msg)
    def error(self, msg): self._write("ERROR", msg)


logger = AppLogger()


# ══════════════════════════════════════════════════════════════════
#  § 4  主题配色
# ══════════════════════════════════════════════════════════════════

THEMES = {
    "light": {
        "bg":           "#F0F4F8",
        "sidebar":      "#1E3A5F",
        "sidebar_sel":  "#2563EB",
        "sidebar_txt":  "#FFFFFF",
        "sidebar_sub":  "#93C5FD",
        "card":         "#FFFFFF",
        "accent":       "#2563EB",
        "accent_h":     "#1D4ED8",
        "text":         "#1E293B",
        "subtext":      "#64748B",
        "border":       "#E2E8F0",
        "success":      "#16A34A",
        "warning":      "#D97706",
        "danger":       "#DC2626",
        "danger_h":     "#B91C1C",
        "log_bg":       "#0D1117",
        "log_fg":       "#58A6FF",
        "log_info":     "#79C0FF",
        "log_warn":     "#E3B341",
        "log_err":      "#F85149",
        "entry_bg":     "#F8FAFC",
        "entry_bd":     "#CBD5E1",
        "btn_fg":       "#FFFFFF",
        "sep":          "#E2E8F0",
        "badge_bg":     "#DBEAFE",
        "badge_fg":     "#1D4ED8",
    },
    "dark": {
        "bg":           "#0D1117",
        "sidebar":      "#161B22",
        "sidebar_sel":  "#1F6FEB",
        "sidebar_txt":  "#E6EDF3",
        "sidebar_sub":  "#8B949E",
        "card":         "#161B22",
        "accent":       "#1F6FEB",
        "accent_h":     "#388BFD",
        "text":         "#E6EDF3",
        "subtext":      "#8B949E",
        "border":       "#30363D",
        "success":      "#3FB950",
        "warning":      "#D29922",
        "danger":       "#F85149",
        "danger_h":     "#FF7B72",
        "log_bg":       "#010409",
        "log_fg":       "#58A6FF",
        "log_info":     "#79C0FF",
        "log_warn":     "#E3B341",
        "log_err":      "#F85149",
        "entry_bg":     "#0D1117",
        "entry_bd":     "#30363D",
        "btn_fg":       "#FFFFFF",
        "sep":          "#21262D",
        "badge_bg":     "#1F3A6E",
        "badge_fg":     "#79C0FF",
    },
}

_T: dict = THEMES["light"]   # 当前主题（运行时替换）

def C(key: str) -> str:
    return _T.get(key, "#888888")


# ══════════════════════════════════════════════════════════════════
#  § 5  自定义控件
# ══════════════════════════════════════════════════════════════════

class RoundButton(tk.Canvas):
    def __init__(self, master, text="", command=None,
                 color_key="accent", hover_key="accent_h",
                 fg_key="btn_fg", width=140, height=36,
                 radius=6, font_size=10, **kw):
        self._cfg_w = S(width)
        self._cfg_h = S(height)
        self._cfg_r = S(radius)
        
        super().__init__(master,
                         width=self._cfg_w, height=self._cfg_h,
                         highlightthickness=0, bd=0,
                         cursor="hand2", **kw)
        
        self._text      = text
        self._cmd       = command
        self._ck        = color_key
        self._hk        = hover_key
        self._fk        = fg_key
        self._font_size = font_size
        
        self._draw(C(self._ck))
        
        self.bind("<Enter>",    lambda _: self._draw(C(self._hk)))
        self.bind("<Leave>",    lambda _: self._draw(C(self._ck)))
        self.bind("<Button-1>", lambda _: command() if command else None)

    def _draw(self, bg: str):
        self.delete("all")
        r = self._cfg_r
        w = self._cfg_w
        h = self._cfg_h
        
        # 圆角矩形绘制
        self.create_arc(0,    0,    r*2, r*2, start=90,  extent=90,  fill=bg, outline=bg)
        self.create_arc(w-r*2,0,    w,   r*2, start=0,   extent=90,  fill=bg, outline=bg)
        self.create_arc(0,    h-r*2,r*2, h,   start=180, extent=90,  fill=bg, outline=bg)
        self.create_arc(w-r*2,h-r*2,w,  h,   start=270, extent=90,  fill=bg, outline=bg)
        self.create_rectangle(r, 0, w-r, h, fill=bg, outline=bg)
        self.create_rectangle(0, r, w, h-r, fill=bg, outline=bg)
        
        self.create_text(w//2, h//2, text=self._text,
                         fill=C(self._fk),
                         font=("微软雅黑", FS(self._font_size), "bold"))

class StyledEntry(tk.Frame):
    """带标签 + 可选浏览按钮的自绘输入框。"""

    def __init__(self, master, label="", browse=False,
                 browse_type="file", textvariable=None, **kw):
        super().__init__(master, bg=C("card"), **kw)
        self._btype = browse_type

        tk.Label(self, text=label,
                 bg=C("card"), fg=C("subtext"),
                 font=("微软雅黑", FS(8))).pack(anchor="w", pady=(S(4), S(1)))

        row = tk.Frame(self, bg=C("card"))
        row.pack(fill="x")

        self.var = textvariable or tk.StringVar()
        self._ent = tk.Entry(
            row, textvariable=self.var,
            bg=C("entry_bg"), fg=C("text"),
            insertbackground=C("text"),
            relief="flat",
            font=("微软雅黑", FS(9)),
            highlightthickness=1,
            highlightbackground=C("entry_bd"),
            highlightcolor=C("accent"),
        )
        self._ent.pack(side="left", fill="x", expand=True,
                       ipady=S(5), ipadx=S(4))

        if browse:
            btn = tk.Label(row, text="  📂 ",
                           bg=C("card"), fg=C("accent"),
                           font=("Segoe UI Emoji", FS(11)),
                           cursor="hand2")
            btn.pack(side="left", padx=(S(4), 0))
            btn.bind("<Button-1>", lambda _: self._browse())

    def _browse(self):
        p = (filedialog.askopenfilename() if self._btype == "file"
             else filedialog.askdirectory())
        if p: self.var.set(p)

    def get(self): return self.var.get()
    def set(self, v): self.var.set(v)


class SectionCard(tk.Frame):
    """带顶部色条 + 标题的卡片。"""

    def __init__(self, master, title="", icon="", **kw):
        super().__init__(master, bg=C("card"),
                         highlightthickness=1,
                         highlightbackground=C("border"), **kw)
        # 顶部3px色条
        tk.Frame(self, bg=C("accent"), height=S(3)).pack(fill="x")
        hdr = tk.Frame(self, bg=C("card"))
        hdr.pack(fill="x", padx=S(12), pady=(S(8), S(2)))
        if icon:
            tk.Label(hdr, text=icon, bg=C("card"),
                     font=("Segoe UI Emoji", FS(12))).pack(side="left")
        tk.Label(hdr, text=f"  {title}", bg=C("card"),
                 fg=C("text"),
                 font=("微软雅黑", FS(10), "bold")).pack(side="left")
        self.body = tk.Frame(self, bg=C("card"))
        self.body.pack(fill="both", padx=S(14), pady=(0, S(10)))


class ToggleSwitch(tk.Canvas):
    """iOS 风格开关。"""

    def __init__(self, master, variable: tk.BooleanVar, **kw):
        self._W = S(44); self._H = S(22)
        super().__init__(master, width=self._W, height=self._H,
                         highlightthickness=0, bd=0,
                         cursor="hand2", **kw)
        self._var = variable
        self._draw()
        variable.trace_add("write", lambda *_: self._draw())
        self.bind("<Button-1>", lambda _: variable.set(not variable.get()))

    def _draw(self):
        self.delete("all")
        on  = self._var.get()
        bg  = C("accent") if on else C("subtext")
        r   = self._H // 2
        w   = self._W; h = self._H
        # 背景胶囊
        self.create_oval(0, 0, h, h, fill=bg, outline=bg)
        self.create_oval(w-h, 0, w, h, fill=bg, outline=bg)
        self.create_rectangle(r, 0, w-r, h, fill=bg, outline=bg)
        # 滑块
        pad = S(3)
        x   = w - h + pad if on else pad
        self.create_oval(x, pad, x+(h-pad*2), h-pad,
                         fill="white", outline="white")


# ══════════════════════════════════════════════════════════════════
#  § 6  业务逻辑
# ══════════════════════════════════════════════════════════════════

def resolve_driver(configured: str) -> str | None:
    """配置路径优先；失败则查程序同目录 geckodriver.exe。"""
    if configured and os.path.isfile(configured):
        return configured
    fb = os.path.join(app_dir(), "geckodriver.exe")
    return fb if os.path.isfile(fb) else None


def clean_environment(cfg: dict):
    if not cfg.get("step_clean_procs", True):
        logger.info("[环境清理] 关闭进程步骤已禁用，跳过")
        return
    logger.info("[环境清理] 正在关闭指定后台进程...")
    if psutil is None:
        logger.warn("[环境清理] psutil 未安装，跳过进程清理")
    else:
        kill_list = [p.strip() for p in
                     cfg.get("kill_procs", "").split(",") if p.strip()]
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] in kill_list:
                    proc.kill()
                    logger.info(f"[环境清理] 已结束进程: {proc.info['name']}")
                    time.sleep(0.3)
            except Exception:
                pass

    if not cfg.get("step_go_desktop", True):
        logger.info("[环境清理] 退回桌面步骤已禁用，跳过")
        return
    try:
        time.sleep(0.5)
        if pa:
            pa.hotkey("win", "d")
        time.sleep(0.5)
        logger.info("[环境清理] 已返回桌面")
    except Exception as e:
        logger.warn(f"[环境清理] 返回桌面失败: {e}")


def set_volume(cfg: dict):
    if not cfg.get("step_set_volume", True):
        logger.info("[音量] 音量调节步骤已禁用，跳过")
        return
    if not cfg.get("volume_enable", True):
        logger.info("[音量] 音量自动调节已关闭")
        return
    pct    = int(cfg.get("volume_percent", 80))
    nircmd = os.path.join(cfg.get("tool_path", ""), "nircmd.exe")
    logger.info(f"[音量] 设置系统音量 → {pct}%")
    if not os.path.isfile(nircmd):
        logger.warn(f"[音量] 未找到 nircmd.exe（{nircmd}），跳过音量设置")
        return
    try:
        vol = int(65535 * pct / 100)
        os.system(f'"{nircmd}" mutesysvolume 0 && "{nircmd}" setsysvolume {vol}')
        logger.info("[音量] 音量设置完成")
    except Exception as e:
        logger.error(f"[音量] 设置失败: {e}")


def play_news(cfg: dict, stop_event: threading.Event, hide_popup_cb=None):
    if not _SELENIUM_OK:
        logger.error("[播放] selenium 未安装，无法播放")
        return

    logger.info("[播放] ══════ 播放流程开始 ══════")
    if pa: pa.PAUSE = 1

    gecko = resolve_driver(cfg.get("geckodriver_path", ""))
    if not gecko:
        logger.error("[播放] 未找到 geckodriver.exe！"
                     "请将其放到程序同目录，或在设置中指定路径。")
        return

    ff = cfg.get("firefox_path", "")
    if not os.path.isfile(ff):
        logger.error(f"[播放] Firefox 不存在: {ff}")
        return

    logger.info(f"[播放] 驱动: {gecko}")
    logger.info(f"[播放] Firefox: {ff}")

    options = FFOptions()
    options.binary_location = ff
    for arg in ("--no-sandbox", "--disable-notifications",
                "--disable-gpu", "--disable-extensions",
                "--disable-dev-shm-usage"):
        options.add_argument(arg)

    driver = None
    try:
        service = FFService(executable_path=gecko)
        driver  = webdriver.Firefox(service=service, options=options)
        driver.maximize_window()
        driver.implicitly_wait(15)
        logger.info("[播放] Firefox 启动成功")
    except Exception as e:
        logger.error(f"[播放] Firefox 启动失败: {e}")
        return

    try:
        url = cfg.get("video_url", "")
        logger.info(f"[播放] 加载页面: {url}")
        driver.get(url)
        logger.info("[播放] 页面加载完成")
    except Exception as e:
        logger.error(f"[播放] 页面加载失败: {e}")
        try: driver.quit()
        except Exception: pass
        return

    if cfg.get("step_click_play", True):
        try:
            driver.find_element(By.XPATH,
                                cfg.get("xpath_path", "")).click()
            logger.info("[播放] 点击播放按钮成功")
        except Exception as e:
            logger.warn(f"[播放] 点击播放按钮失败（可能无需点击）: {e}")
    else:
        logger.info("[播放] 点击播放按钮步骤已禁用，跳过")

    if cfg.get("step_fullscreen", True):
        try:
            delay = int(cfg.get("full_screen_delay", 5))
            time.sleep(delay)
            # ★ 优先使用 F 按键全屏
            if cfg.get("step_use_f_key", True):
                if pa: pa.press("f")
                logger.info("[播放] 已按 F 键进入全屏")
            else:
                # 备用：浏览器全屏 API
                driver.fullscreen_window()
                logger.info("[播放] 已通过浏览器 API 进入全屏")
            
            # ★ 新增：全屏后自动隐藏状态弹窗
            if cfg.get("step_hide_popup", True) and hide_popup_cb:
                hide_popup_cb()
                logger.info("[播放] 已隐藏状态弹窗")
        except Exception as e:
            logger.warn(f"[播放] 全屏操作失败: {e}")
    else:
        logger.info("[播放] 全屏步骤已禁用，跳过")

    minutes = int(cfg.get("play_minutes", 25))
    logger.info(f"[播放] 开始计时，共 {minutes} 分钟")
    for i in range(minutes * 60):
        if stop_event.is_set():
            logger.info("[播放] 收到停止信号，提前终止")
            break
        time.sleep(1)
        # 每分钟报一次进度
        if (i + 1) % 60 == 0:
            logger.info(f"[播放] 已播放 {(i+1)//60}/{minutes} 分钟")
    else:
        logger.info("[播放] 播放时间已到")

    try:
        driver.quit()
        logger.info("[播放] Firefox 已关闭")
    except Exception as e:
        logger.warn(f"[播放] 关闭浏览器时出错: {e}")

    logger.info("[播放] ══════ 播放流程结束 ══════")


# ══════════════════════════════════════════════════════════════════
#  § 7  主窗口
# ══════════════════════════════════════════════════════════════════

class MainApp(tk.Tk):

    # ── 初始化 ────────────────────────────────────────────────────
    def __init__(self, auto_play: bool = False):
        super().__init__()
        self.cfg        = load_config()
        self._auto_play = auto_play
        self._stop_evt  = threading.Event()
        self._task_thr  : threading.Thread | None = None
        self._running   = False
        self._popup_win : tk.Toplevel | None = None  # ★ 弹窗引用
        self._save_after_id = None  # ★ 自动保存防抖 ID

        # 主题
        global _T
        _T = THEMES.get(self.cfg.get("theme", "light"), THEMES["light"])

        # 日志（GUI 回调在控件建好后设置）
        logger.setup(
            log_dir = self.cfg.get("log_dir", os.path.join(app_dir(), "logs")),
            enabled = self.cfg.get("log_enable", True),
            gui_cb  = None,           # 稍后挂载
        )

        self._build_window()
        self._build_ui()
        logger.setup(
            log_dir = self.cfg.get("log_dir", os.path.join(app_dir(), "logs")),
            enabled = self.cfg.get("log_enable", True),
            gui_cb  = self._append_log,
        )

        logger.info(f"{'='*55}")
        logger.info(f"  {APP_NAME}  v{APP_VERSION}  启动")
        logger.info(f"  屏幕缩放系数: {SCALE}x  基础字号: {FS(10)}pt")
        logger.info(f"  配置文件: {CONFIG_PATH}")
        logger.info(f"{'='*55}")

        # 启动参数 autoplay 或 配置项 autoplay_on_start
        if auto_play or self.cfg.get("autoplay_on_start", False):
            self.after(800, self._start_task)

    # ── 窗口基础 ──────────────────────────────────────────────────
    def _build_window(self):
        self.title(f"{APP_NAME}  v{APP_VERSION}")
        base_w, base_h = S(1000), S(640)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - base_w) // 2
        y  = (sh - base_h) // 2
        self.geometry(f"{base_w}x{base_h}+{x}+{y}")
        self.minsize(S(760), S(520))
        self.resizable(True, True)
        self.configure(bg=C("bg"))

    # ── 整体布局 ──────────────────────────────────────────────────
    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self._build_sidebar()
        self._build_main()

    # ── 侧边栏（可滚动版本）───────────────────────────────────────
    def _build_sidebar(self):
        sb_w = S(190)
        
        # ★ 外层容器（固定宽度）
        self._sb_outer = tk.Frame(self, width=sb_w, bg=C("sidebar"))
        self._sb_outer.grid(row=0, column=0, sticky="ns")
        self._sb_outer.grid_propagate(False)
        self._sb_outer.grid_rowconfigure(0, weight=1)
        self._sb_outer.grid_columnconfigure(0, weight=1)
        
        # ★ Canvas + 滚动条 实现可滚动侧边栏
        sb_canvas = tk.Canvas(self._sb_outer, bg=C("sidebar"),
                               highlightthickness=0, width=sb_w)
        sb_scroll = ttk.Scrollbar(self._sb_outer, orient="vertical",
                                   command=sb_canvas.yview)
        sb_canvas.configure(yscrollcommand=sb_scroll.set)
        
        sb_canvas.grid(row=0, column=0, sticky="nsew")
        sb_scroll.grid(row=0, column=1, sticky="ns")
        
        # ★ 侧边栏内部框架（放在 Canvas 中）
        self._sb = tk.Frame(sb_canvas, bg=C("sidebar"), width=sb_w)
        self._sb.bind("<Configure>",
                       lambda e: sb_canvas.configure(
                           scrollregion=sb_canvas.bbox("all")))
        sb_canvas.create_window((0, 0), window=self._sb, anchor="nw",
                                 width=sb_w)
        
        # 鼠标滚轮支持
        def _on_mousewheel(event):
            sb_canvas.yview_scroll(int(-event.delta / 60), "units")
        sb_canvas.bind("<Enter>", lambda _: sb_canvas.bind_all("<MouseWheel>", _on_mousewheel))
        sb_canvas.bind("<Leave>", lambda _: sb_canvas.unbind_all("<MouseWheel>"))
        
        # Logo
        lg = tk.Frame(self._sb, bg=C("sidebar"), height=S(88))
        lg.pack(fill="x"); lg.pack_propagate(False)
        tk.Label(lg, text="📺",
                 font=("Segoe UI Emoji", FS(22)),
                 bg=C("sidebar"), fg=C("sidebar_txt")).pack(pady=(S(12), 0))
        tk.Label(lg, text=APP_NAME,
                 font=("微软雅黑", FS(9), "bold"),
                 bg=C("sidebar"), fg=C("sidebar_txt")).pack()

        tk.Frame(self._sb, bg=C("sidebar_sub"),
                 height=1).pack(fill="x", padx=S(16), pady=S(6))

        # 导航
        self._nav_frames: dict[str, tk.Frame] = {}
        pages = [
            ("🏠", "主页",     "home"),
            ("🎬", "播放设置", "play"),
            ("🦊", "浏览器",   "browser"),
            ("🔊", "音量",     "volume"),
            ("💬", "弹窗提示", "popup"),
            ("🔧", "启动行为", "startup"),
            ("📋", "日志",     "logpage"),
            ("🎨", "外观",     "appearance"),
            ("ℹ️",  "关于",     "about"),
        ]
        for icon, label, key in pages:
            f = tk.Frame(self._sb, bg=C("sidebar"),
                         cursor="hand2", height=S(42))
            f.pack(fill="x"); f.pack_propagate(False)
            inner = tk.Frame(f, bg=C("sidebar"))
            inner.place(relx=0, rely=0, relwidth=1, relheight=1)
            tk.Label(inner, text=icon,
                     font=("Segoe UI Emoji", FS(13)),
                     bg=C("sidebar"), fg=C("sidebar_txt"),
                     width=2).pack(side="left", padx=(S(14), S(4)))
            tk.Label(inner, text=label,
                     font=("微软雅黑", FS(9)),
                     bg=C("sidebar"), fg=C("sidebar_txt"),
                     anchor="w").pack(side="left", fill="both", expand=True)
            self._nav_frames[key] = f
            for w in (f, inner, *inner.winfo_children()):
                w.bind("<Button-1>", lambda _, k=key: self._switch(k))
                w.bind("<Enter>",   lambda _, w=inner: w.configure(bg=C("sidebar_sel")))
                w.bind("<Leave>",   lambda _, k=key, w=inner: w.configure(
                    bg=C("sidebar_sel") if k==self._active_page else C("sidebar")))
            for ch in inner.winfo_children():
                ch.configure(bg=C("sidebar"))

        tk.Label(self._sb, text=f"v{APP_VERSION}",
                 bg=C("sidebar"), fg=C("sidebar_sub"),
                 font=("微软雅黑", FS(8))).pack(side="bottom", pady=S(8))

        self._active_page = ""

    # ── 主内容区 ──────────────────────────────────────────────────
    def _build_main(self):
        self._main = tk.Frame(self, bg=C("bg"))
        self._main.grid(row=0, column=1, sticky="nsew")
        self._main.grid_rowconfigure(0, weight=1)
        self._main.grid_columnconfigure(0, weight=1)

        self._pages: dict[str, tk.Frame] = {}
        builders = {
            "home":       self._pg_home,
            "play":       self._pg_play,
            "browser":    self._pg_browser,
            "volume":     self._pg_volume,
            "popup":      self._pg_popup,
            "startup":    self._pg_startup,
            "logpage":    self._pg_log,
            "appearance": self._pg_appearance,
            "about":      self._pg_about,
        }
        for key, builder in builders.items():
            f = tk.Frame(self._main, bg=C("bg"))
            f.grid(row=0, column=0, sticky="nsew")
            self._pages[key] = f
            builder(f)

        self._switch("home")

    def _switch(self, key: str):
        self._active_page = key
        self._pages[key].tkraise()
        # 侧边栏高亮
        for k, f in self._nav_frames.items():
            inner = f.winfo_children()[0] if f.winfo_children() else f
            col   = C("sidebar_sel") if k == key else C("sidebar")
            inner.configure(bg=col)
            for ch in inner.winfo_children():
                ch.configure(bg=col)

    # ─────────────────────────────────────────────────────────────
    # § 7.1  页面：主页
    # ─────────────────────────────────────────────────────────────
    def _pg_home(self, p: tk.Frame):
        p.grid_rowconfigure(2, weight=1)
        p.grid_columnconfigure(0, weight=1)

        # 顶栏
        bar = tk.Frame(p, bg=C("card"), height=S(72))
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        tk.Label(bar, text=f"  {APP_NAME}",
                 font=("微软雅黑", FS(17), "bold"),
                 bg=C("card"), fg=C("text")).pack(side="left", pady=S(12))
        # 版本徽章
        badge = tk.Label(bar, text=f" v{APP_VERSION} ",
                         bg=C("badge_bg"), fg=C("badge_fg"),
                         font=("微软雅黑", FS(8), "bold"),
                         padx=S(6), pady=S(2))
        badge.pack(side="left", padx=S(8), pady=S(22))

        ttk.Separator(p).grid(row=1, column=0, sticky="ew")

        body = tk.Frame(p, bg=C("bg"))
        body.grid(row=2, column=0, sticky="nsew", padx=S(20), pady=S(16))
        body.grid_columnconfigure((0, 1), weight=1)
        body.grid_rowconfigure(1, weight=1)

        # ── 状态卡
        sc = SectionCard(body, "运行状态", "📊")
        sc.grid(row=0, column=0, sticky="ew", padx=(0, S(8)), pady=S(6))
        self._lbl_status = tk.Label(sc.body, text="● 就绪",
                                    font=("微软雅黑", FS(14), "bold"),
                                    bg=C("card"), fg=C("success"))
        self._lbl_status.pack(anchor="w", pady=S(4))
        self._lbl_info = tk.Label(sc.body, text="等待启动...",
                                  font=("微软雅黑", FS(9)),
                                  bg=C("card"), fg=C("subtext"))
        self._lbl_info.pack(anchor="w")

        # ── 操作卡
        cc = SectionCard(body, "操作控制", "🎮")
        cc.grid(row=0, column=1, sticky="ew", padx=(S(8), 0), pady=S(6))
        br = tk.Frame(cc.body, bg=C("card"))
        br.pack(pady=S(10))
        self._btn_start = RoundButton(br, "▶  开始播放",
                                      command=self._start_task,
                                      width=138, height=38, font_size=10)
        self._btn_start.pack(side="left", padx=S(6))
        self._btn_stop  = RoundButton(br, "■  停止",
                                      command=self._stop_task,
                                      color_key="danger", hover_key="danger_h",
                                      width=100, height=38, font_size=10)
        self._btn_stop.pack(side="left", padx=S(6))

        # ── 日志摘要卡
        lc = SectionCard(body, "实时日志摘要", "📜")
        lc.grid(row=1, column=0, columnspan=2,
                sticky="nsew", pady=(S(8), 0))
        body.grid_rowconfigure(1, weight=1)
        lc.grid_rowconfigure(0, weight=1)

        self._home_log = tk.Text(
            lc.body, state="disabled", wrap="word",
            font=("Consolas", FS(9)),
            bg=C("log_bg"), fg=C("log_info"),
            insertbackground=C("log_info"),
            relief="flat", padx=S(8), pady=S(6),
        )
        self._home_log.pack(fill="both", expand=True)

    # ─────────────────────────────────────────────────────────────
    # § 7.2  页面：播放设置（自动保存）
    # ─────────────────────────────────────────────────────────────
    def _pg_play(self, p: tk.Frame):
        self._v_url     = tk.StringVar(value=self.cfg.get("video_url", ""))
        self._v_mins    = tk.StringVar(value=str(self.cfg.get("play_minutes", 25)))
        self._v_xpath   = tk.StringVar(value=self.cfg.get("xpath_path", ""))
        self._v_fsd     = tk.StringVar(value=str(self.cfg.get("full_screen_delay", 5)))
        self._v_kills   = tk.StringVar(value=self.cfg.get("kill_procs", ""))

        # ★ 绑定自动保存
        for var in (self._v_url, self._v_mins, self._v_xpath, self._v_fsd, self._v_kills):
            var.trace_add("write", lambda *_: self._auto_save_play())

        _, inn = self._scrollable(p)
        self._sec(inn, "🎬", "视频播放参数")
        StyledEntry(inn, "视频页面 URL", textvariable=self._v_url).pack(fill="x", pady=S(3))
        StyledEntry(inn, "播放时长（分钟）", textvariable=self._v_mins).pack(fill="x", pady=S(3))
        StyledEntry(inn, "播放按钮 XPath", textvariable=self._v_xpath).pack(fill="x", pady=S(3))
        StyledEntry(inn, "进入全屏前等待（秒）", textvariable=self._v_fsd).pack(fill="x", pady=S(3))
        self._sec(inn, "🧹", "环境清理（英文逗号分隔进程名）")
        StyledEntry(inn, "要关闭的进程列表", textvariable=self._v_kills).pack(fill="x", pady=S(3))
        # ★ 不再需要保存按钮，底部留白
        tk.Frame(inn, bg=C("bg"), height=S(10)).pack()

    def _auto_save_play(self):
        """自动保存播放设置"""
        self.cfg.update({
            "video_url":         self._v_url.get().strip(),
            "play_minutes":      self._intv(self._v_mins, 25),
            "xpath_path":        self._v_xpath.get().strip(),
            "full_screen_delay": self._intv(self._v_fsd, 5),
            "kill_procs":        self._v_kills.get().strip(),
        })
        self._auto_save()

    # ─────────────────────────────────────────────────────────────
    # § 7.3  页面：浏览器（自动保存）
    # ─────────────────────────────────────────────────────────────
    def _pg_browser(self, p: tk.Frame):
        self._v_ff  = tk.StringVar(value=self.cfg.get("firefox_path", ""))
        self._v_gk  = tk.StringVar(value=self.cfg.get("geckodriver_path", ""))

        # ★ 绑定自动保存
        for var in (self._v_ff, self._v_gk):
            var.trace_add("write", lambda *_: self._auto_save_browser())

        _, inn = self._scrollable(p)
        self._sec(inn, "🦊", "Firefox 浏览器")
        StyledEntry(inn, "Firefox 可执行文件路径",
                    browse=True, browse_type="file",
                    textvariable=self._v_ff).pack(fill="x", pady=S(3))
        self._sec(inn, "🔧", "GeckoDriver 驱动路径")
        tk.Label(inn, text="  ℹ  留空 → 自动查找程序同目录的 geckodriver.exe",
                 font=("微软雅黑", FS(8)),
                 bg=C("bg"), fg=C("subtext")).pack(anchor="w")
        StyledEntry(inn, "geckodriver.exe 路径（可留空）",
                    browse=True, browse_type="file",
                    textvariable=self._v_gk).pack(fill="x", pady=S(3))
        tk.Frame(inn, bg=C("bg"), height=S(10)).pack()

    def _auto_save_browser(self):
        """自动保存浏览器设置"""
        self.cfg.update({
            "firefox_path":     self._v_ff.get().strip(),
            "geckodriver_path": self._v_gk.get().strip(),
        })
        self._auto_save()

    # ─────────────────────────────────────────────────────────────
    # § 7.4  页面：音量（自动保存）
    # ─────────────────────────────────────────────────────────────
    def _pg_volume(self, p: tk.Frame):
        self._v_vol_en  = tk.BooleanVar(value=self.cfg.get("volume_enable", True))
        self._v_vol_pct = tk.IntVar(value=int(self.cfg.get("volume_percent", 80)))
        self._v_tool    = tk.StringVar(value=self.cfg.get("tool_path", ""))

        # ★ 绑定自动保存
        self._v_vol_en.trace_add("write", lambda *_: self._auto_save_volume())
        self._v_vol_pct.trace_add("write", lambda *_: self._auto_save_volume())
        self._v_tool.trace_add("write", lambda *_: self._auto_save_volume())

        _, inn = self._scrollable(p)
        self._sec(inn, "🔊", "系统音量控制")

        sr = tk.Frame(inn, bg=C("bg")); sr.pack(fill="x", pady=S(6))
        ToggleSwitch(sr, self._v_vol_en).pack(side="left")
        tk.Label(sr, text=" 启用音量自动调节",
                 font=("微软雅黑", FS(9)),
                 bg=C("bg"), fg=C("text")).pack(side="left")

        slr = tk.Frame(inn, bg=C("bg")); slr.pack(fill="x", pady=S(4))
        tk.Label(slr, text="音量百分比",
                 font=("微软雅黑", FS(9)),
                 bg=C("bg"), fg=C("subtext")).pack(side="left")
        ttk.Scale(slr, from_=0, to=100, orient="horizontal",
                  variable=self._v_vol_pct, length=S(260)).pack(
            side="left", padx=S(10))
        self._lbl_vol = tk.Label(slr, text=f"{self._v_vol_pct.get():3d}%",
                                  font=("Consolas", FS(9)),
                                  bg=C("bg"), fg=C("accent"), width=5)
        self._lbl_vol.pack(side="left")
        self._v_vol_pct.trace_add(
            "write", lambda *_: self._lbl_vol.configure(
                text=f"{self._v_vol_pct.get():3d}%"))

        self._sec(inn, "🛠", "工具目录（nircmd.exe 所在文件夹）")
        StyledEntry(inn, "工具目录路径",
                    browse=True, browse_type="dir",
                    textvariable=self._v_tool).pack(fill="x", pady=S(3))
        tk.Frame(inn, bg=C("bg"), height=S(10)).pack()

    def _auto_save_volume(self):
        """自动保存音量设置"""
        self.cfg.update({
            "volume_enable":  self._v_vol_en.get(),
            "volume_percent": self._v_vol_pct.get(),
            "tool_path":      self._v_tool.get().strip(),
        })
        self._auto_save()

    # ─────────────────────────────────────────────────────────────
    # § 7.5  页面：弹窗提示（自动保存）
    # ─────────────────────────────────────────────────────────────
    def _pg_popup(self, p: tk.Frame):
        self._v_pop_en  = tk.BooleanVar(value=self.cfg.get("popup_enable", True))
        self._v_pop_w   = tk.StringVar(value=str(self.cfg.get("popup_width", 520)))
        self._v_pop_h   = tk.StringVar(value=str(self.cfg.get("popup_height", 200)))
        self._v_pop_d   = tk.StringVar(value=str(self.cfg.get("popup_close_delay", 60)))
        self._v_pop_t   = tk.StringVar(value=self.cfg.get("popup_text", ""))

        # ★ 绑定自动保存
        for var in (self._v_pop_en, self._v_pop_w, self._v_pop_h, self._v_pop_d, self._v_pop_t):
            var.trace_add("write", lambda *_: self._auto_save_popup())

        _, inn = self._scrollable(p)
        self._sec(inn, "💬", "状态弹窗配置")

        r = tk.Frame(inn, bg=C("bg")); r.pack(fill="x", pady=S(6))
        ToggleSwitch(r, self._v_pop_en).pack(side="left")
        tk.Label(r, text=" 启动时显示状态弹窗",
                 font=("微软雅黑", FS(9)),
                 bg=C("bg"), fg=C("text")).pack(side="left")

        StyledEntry(inn, "弹窗宽度（逻辑像素）", textvariable=self._v_pop_w).pack(fill="x", pady=S(3))
        StyledEntry(inn, "弹窗高度（逻辑像素）", textvariable=self._v_pop_h).pack(fill="x", pady=S(3))
        StyledEntry(inn, "自动关闭延时（秒）", textvariable=self._v_pop_d).pack(fill="x", pady=S(3))
        StyledEntry(inn, "弹窗显示文字（\\n 换行）", textvariable=self._v_pop_t).pack(fill="x", pady=S(3))
        tk.Frame(inn, bg=C("bg"), height=S(10)).pack()

    def _auto_save_popup(self):
        """自动保存弹窗设置"""
        self.cfg.update({
            "popup_enable":      self._v_pop_en.get(),
            "popup_width":       self._intv(self._v_pop_w, 520),
            "popup_height":      self._intv(self._v_pop_h, 200),
            "popup_close_delay": self._intv(self._v_pop_d, 60),
            "popup_text":        self._v_pop_t.get(),
        })
        self._auto_save()

    # ─────────────────────────────────────────────────────────────
    # § 7.6  页面：启动行为（所有步骤开关）★ 新增两项
    # ─────────────────────────────────────────────────────────────
    def _pg_startup(self, p: tk.Frame):
        self._v_autoplay  = tk.BooleanVar(value=self.cfg.get("autoplay_on_start", False))
        self._v_s_clean   = tk.BooleanVar(value=self.cfg.get("step_clean_procs",  True))
        self._v_s_desktop = tk.BooleanVar(value=self.cfg.get("step_go_desktop",   True))
        self._v_s_volume  = tk.BooleanVar(value=self.cfg.get("step_set_volume",   True))
        self._v_s_click   = tk.BooleanVar(value=self.cfg.get("step_click_play",   True))
        self._v_s_fullscr = tk.BooleanVar(value=self.cfg.get("step_fullscreen",   True))
        self._v_s_f_key   = tk.BooleanVar(value=self.cfg.get("step_use_f_key",    True))   # ★ 新增
        self._v_s_hide    = tk.BooleanVar(value=self.cfg.get("step_hide_popup",    True))   # ★ 新增

        # ★ 绑定自动保存
        all_vars = [self._v_autoplay, self._v_s_clean, self._v_s_desktop,
                    self._v_s_volume, self._v_s_click, self._v_s_fullscr,
                    self._v_s_f_key, self._v_s_hide]
        for var in all_vars:
            var.trace_add("write", lambda *_: self._auto_save_startup())

        _, inn = self._scrollable(p)

        self._sec(inn, "⚡", "自动播放行为")
        self._toggle_row(inn, self._v_autoplay,
                         "启动 EXE 时自动开始播放新闻",
                         "（等同于带 play 参数运行）")

        self._sec(inn, "🔧", "各步骤开关（全部默认开启）")

        steps = [
            (self._v_s_clean,   "关闭指定后台进程",   "任务开始前结束 kill_procs 中列出的进程"),
            (self._v_s_desktop, "退回桌面",           "关闭进程后发送 Win+D 回到桌面"),
            (self._v_s_volume,  "自动调节音量",        "调用 nircmd 设置系统音量"),
            (self._v_s_click,   "点击视频播放按钮",   "用 XPath 定位并点击播放控件"),
            (self._v_s_fullscr, "进入全屏",           "播放后进入全屏模式"),
            (self._v_s_f_key,   "  └ 使用 F 按键全屏", "★ 按键盘 F 键进入全屏（默认开启）"),
            (self._v_s_hide,    "  └ 全屏后隐藏弹窗", "★ 全屏后自动隐藏状态提示窗口（默认开启）"),
        ]
        for var, title, hint in steps:
            self._toggle_row(inn, var, title, hint)

        tk.Frame(inn, bg=C("bg"), height=S(10)).pack()

    def _toggle_row(self, parent, var: tk.BooleanVar, title: str, hint: str = ""):
        row = tk.Frame(parent, bg=C("bg"),
                       highlightthickness=1,
                       highlightbackground=C("border"))
        row.pack(fill="x", pady=S(4), ipady=S(6))
        left = tk.Frame(row, bg=C("bg"))
        left.pack(side="left", fill="both", expand=True, padx=S(12))
        tk.Label(left, text=title,
                 font=("微软雅黑", FS(10)),
                 bg=C("bg"), fg=C("text"), anchor="w").pack(anchor="w")
        if hint:
            tk.Label(left, text=hint,
                     font=("微软雅黑", FS(8)),
                     bg=C("bg"), fg=C("subtext"), anchor="w").pack(anchor="w")
        ToggleSwitch(row, var).pack(side="right", padx=S(14), pady=S(4))

    def _auto_save_startup(self):
        """自动保存启动行为设置"""
        self.cfg.update({
            "autoplay_on_start": self._v_autoplay.get(),
            "step_clean_procs":  self._v_s_clean.get(),
            "step_go_desktop":   self._v_s_desktop.get(),
            "step_set_volume":   self._v_s_volume.get(),
            "step_click_play":   self._v_s_click.get(),
            "step_fullscreen":   self._v_s_fullscr.get(),
            "step_use_f_key":    self._v_s_f_key.get(),   # ★ 新增
            "step_hide_popup":   self._v_s_hide.get(),    # ★ 新增
        })
        self._auto_save()

    # ─────────────────────────────────────────────────────────────
    # § 7.7  页面：日志（自动保存 + 修复浏览按钮）
    # ─────────────────────────────────────────────────────────────
    def _pg_log(self, p: tk.Frame):
        self._v_log_en  = tk.BooleanVar(value=self.cfg.get("log_enable", True))
        self._v_log_dir = tk.StringVar(value=self.cfg.get("log_dir", ""))
        self._v_log_max = tk.StringVar(value=str(self.cfg.get("log_max_lines", 2000)))

        # ★ 绑定自动保存
        self._v_log_en.trace_add("write", lambda *_: self._auto_save_log())
        self._v_log_dir.trace_add("write", lambda *_: self._auto_save_log())
        self._v_log_max.trace_add("write", lambda *_: self._auto_save_log())

        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        # 工具栏
        tb = tk.Frame(p, bg=C("card"), height=S(50))
        tb.grid(row=0, column=0, columnspan=2, sticky="ew")
        tb.pack_propagate(False)

        def tb_lbl(text, **kw):
            return tk.Label(tb, text=text, bg=C("card"),
                             fg=C("subtext"), font=("微软雅黑", FS(9)), **kw)

        ToggleSwitch(tb, self._v_log_en).pack(side="left", padx=(S(12),S(4)), pady=S(12))
        tb_lbl("启用日志").pack(side="left", padx=(0, S(16)))

        tb_lbl("日志目录:").pack(side="left")
        tk.Entry(tb, textvariable=self._v_log_dir,
                 width=28, bg=C("entry_bg"), fg=C("text"),
                 font=("微软雅黑", FS(9)),
                 relief="flat",
                 highlightthickness=1,
                 highlightbackground=C("entry_bd")).pack(
            side="left", padx=S(4), ipady=S(4))
        
        # ★ 修复：浏览文件夹按钮
        browse_btn = tk.Label(tb, text="📂", font=("Segoe UI Emoji", FS(11)),
                              bg=C("card"), fg=C("accent"), cursor="hand2")
        browse_btn.pack(side="left")
        browse_btn.bind("<Button-1>",
                        lambda _: self._v_log_dir.set(
                            filedialog.askdirectory() or self._v_log_dir.get()))

        tb_lbl("  最大行数:").pack(side="left")
        tk.Entry(tb, textvariable=self._v_log_max,
                 width=6, bg=C("entry_bg"), fg=C("text"),
                 font=("微软雅黑", FS(9)), relief="flat",
                 highlightthickness=1,
                 highlightbackground=C("entry_bd")).pack(
            side="left", padx=S(4), ipady=S(4))

        # ★ 保留清空按钮，移除保存按钮
        RoundButton(tb, "清空显示",
                    command=self._clear_log,
                    color_key="danger", hover_key="danger_h",
                    width=90, height=30, font_size=9).pack(side="left", padx=S(8))

        # 日志文本区
        self._log_text = tk.Text(
            p, state="disabled", wrap="word",
            font=("Consolas", FS(9)),
            bg=C("log_bg"), fg=C("log_info"),
            insertbackground=C("log_info"),
            relief="flat", padx=S(10), pady=S(8),
        )
        self._log_text.grid(row=1, column=0, sticky="nsew",
                            padx=(S(16), 0), pady=S(12))
        vsb = ttk.Scrollbar(p, orient="vertical",
                             command=self._log_text.yview)
        vsb.grid(row=1, column=1, sticky="ns", pady=S(12), padx=(0, S(12)))
        self._log_text.configure(yscrollcommand=vsb.set)

        # 给日志着色标签
        self._log_text.tag_configure("INFO",  foreground=C("log_info"))
        self._log_text.tag_configure("WARN",  foreground=C("log_warn"))
        self._log_text.tag_configure("ERROR", foreground=C("log_err"))

    def _auto_save_log(self):
        """自动保存日志设置"""
        self.cfg.update({
            "log_enable":    self._v_log_en.get(),
            "log_dir":       self._v_log_dir.get().strip(),
            "log_max_lines": self._intv(self._v_log_max, 2000),
        })
        self._auto_save()
        # 实时更新日志器
        logger.setup(self.cfg["log_dir"], self.cfg["log_enable"],
                     gui_cb=self._append_log)

    def _clear_log(self):
        for w in (getattr(self, "_log_text", None),
                  getattr(self, "_home_log", None)):
            if w:
                w.configure(state="normal")
                w.delete("1.0", "end")
                w.configure(state="disabled")

    # ─────────────────────────────────────────────────────────────
    # § 7.8  页面：外观（自动保存）
    # ─────────────────────────────────────────────────────────────
    def _pg_appearance(self, p: tk.Frame):
        self._v_theme = tk.StringVar(value=self.cfg.get("theme", "light"))
        self._v_fsize = tk.IntVar(value=int(self.cfg.get("font_size", 10)))

        # ★ 绑定自动保存
        self._v_theme.trace_add("write", lambda *_: self._auto_save_appearance())
        self._v_fsize.trace_add("write", lambda *_: self._auto_save_appearance())

        _, inn = self._scrollable(p)
        self._sec(inn, "🎨", "主题风格")

        for val, emoji, label in [
            ("light", "☀️", "浅色主题（默认）"),
            ("dark",  "🌙", "深色主题"),
        ]:
            rb = tk.Frame(inn, bg=C("bg"),
                          highlightthickness=1,
                          highlightbackground=C("border"))
            rb.pack(fill="x", pady=S(4), ipady=S(6))
            tk.Radiobutton(rb, text=f" {emoji}  {label}",
                           variable=self._v_theme, value=val,
                           bg=C("bg"), fg=C("text"),
                           selectcolor=C("card"),
                           activebackground=C("bg"),
                           font=("微软雅黑", FS(10))).pack(
                side="left", padx=S(12))

        self._sec(inn, "🔡", "界面基础字号（标准 1080p 下，pt）")
        frow = tk.Frame(inn, bg=C("bg")); frow.pack(fill="x", pady=S(4))
        ttk.Scale(frow, from_=8, to=16, orient="horizontal",
                  variable=self._v_fsize, length=S(220)).pack(side="left")
        tk.Label(frow, textvariable=self._v_fsize,
                 font=("Consolas", FS(10)),
                 bg=C("bg"), fg=C("accent"), width=3).pack(side="left", padx=S(8))
        tk.Label(frow, text="pt（需重启生效）",
                 font=("微软雅黑", FS(8)),
                 bg=C("bg"), fg=C("subtext")).pack(side="left")

        tk.Frame(inn, bg=C("bg"), height=S(10)).pack()

    def _auto_save_appearance(self):
        """自动保存外观设置"""
        self.cfg["theme"]     = self._v_theme.get()
        self.cfg["font_size"] = self._v_fsize.get()
        self._auto_save()
        global _T
        _T = THEMES.get(self.cfg["theme"], THEMES["light"])
        # 即时刷新侧边栏颜色
        self._sb.configure(bg=C("sidebar"))
        self._sb_outer.configure(bg=C("sidebar"))
        self._switch(self._active_page)

    # ─────────────────────────────────────────────────────────────
    # § 7.9  页面：关于
    # ─────────────────────────────────────────────────────────────
    def _pg_about(self, p: tk.Frame):
        p.grid_rowconfigure(0, weight=1)
        p.grid_columnconfigure(0, weight=1)

        center = tk.Frame(p, bg=C("bg"))
        center.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(center, text="📺",
                 font=("Segoe UI Emoji", FS(52)),
                 bg=C("bg"), fg=C("accent")).pack()

        tk.Label(center, text=APP_NAME,
                 font=("微软雅黑", FS(20), "bold"),
                 bg=C("bg"), fg=C("text")).pack(pady=(S(4), 0))

        tk.Label(center, text=f"版本  v{APP_VERSION}",
                 font=("微软雅黑", FS(11)),
                 bg=C("bg"), fg=C("accent")).pack()

        ttk.Separator(center).pack(fill="x", pady=S(14))

        tk.Label(center, text=APP_DESC,
                 font=("微软雅黑", FS(10)),
                 bg=C("bg"), fg=C("text"),
                 justify="center", wraplength=S(420)).pack()

        ttk.Separator(center).pack(fill="x", pady=S(14))

        meta = [
            ("作者", APP_AUTHOR),
            ("发布日期", APP_DATE),
            ("许可证", APP_LICENSE),
            ("配置文件", CONFIG_PATH),
            ("程序目录", app_dir()),
            ("屏幕缩放", f"{SCALE}x"),
        ]
        for k, v in meta:
            row = tk.Frame(center, bg=C("bg")); row.pack(anchor="center")
            tk.Label(row, text=f"{k}：", width=8,
                     font=("微软雅黑", FS(9), "bold"),
                     bg=C("bg"), fg=C("subtext"),
                     anchor="e").pack(side="left")
            tk.Label(row, text=v,
                     font=("微软雅黑", FS(9)),
                     bg=C("bg"), fg=C("text"),
                     anchor="w").pack(side="left")

    # ─────────────────────────────────────────────────────────────
    # § 7.10  任务控制
    # ─────────────────────────────────────────────────────────────
    def _start_task(self):
        if self._running:
            return
        self._running = True
        self._stop_evt.clear()
        self._lbl_status.configure(text="▶ 运行中", fg=C("success"))
        self._lbl_info.configure(
            text=f"播放中 · 预计 {self.cfg.get('play_minutes', 25)} 分钟")
        self._task_thr = threading.Thread(
            target=self._run_all, daemon=True)
        self._task_thr.start()

    def _stop_task(self):
        if not self._running: return
        self._stop_evt.set()
        self._lbl_status.configure(text="■ 停止中...", fg=C("warning"))
        logger.warn("[主程序] 用户请求停止任务")

    def _run_all(self):
        try:
            logger.info("[主程序] ══ 任务启动 ══")
            if self.cfg.get("popup_enable", True):
                self.after(0, self._show_popup)
            clean_environment(self.cfg)
            set_volume(self.cfg)
            # ★ 传递隐藏弹窗的回调
            play_news(self.cfg, self._stop_evt,
                      hide_popup_cb=self._hide_popup)
            logger.info("[主程序] ══ 任务完成 ══")
        except Exception as e:
            logger.error(f"[主程序] 意外异常: {e}")
        finally:
            self.after(0, self._task_done)

    def _task_done(self):
        self._running = False
        self._lbl_status.configure(text="● 就绪", fg=C("success"))
        self._lbl_info.configure(text="任务已结束，等待下次启动...")

    # ─────────────────────────────────────────────────────────────
    # § 7.11  状态弹窗（支持隐藏）
    # ─────────────────────────────────────────────────────────────
    def _show_popup(self):
        try:
            pw  = S(int(self.cfg.get("popup_width",  520)))
            ph  = S(int(self.cfg.get("popup_height", 200)))
            sec = int(self.cfg.get("popup_close_delay", 60))
            txt = self.cfg.get("popup_text", "").replace("\\n", "\n")
            sw  = self.winfo_screenwidth()

            self._popup_win = tk.Toplevel(self)
            self._popup_win.title("程序状态")
            self._popup_win.geometry(f"{pw}x{ph}+{(sw-pw)//2}+{S(20)}")
            self._popup_win.attributes("-topmost", True)
            self._popup_win.resizable(False, False)
            self._popup_win.configure(bg=C("card"))
            
            # ★ 绑定关闭事件
            self._popup_win.protocol("WM_DELETE_WINDOW", self._hide_popup)

            tk.Frame(self._popup_win, bg=C("accent"), height=S(4)).pack(fill="x")
            tk.Label(self._popup_win, text="📺",
                     font=("Segoe UI Emoji", FS(28)),
                     bg=C("card")).pack(pady=(S(12), 0))
            tk.Label(self._popup_win, text=txt,
                     font=("微软雅黑", FS(12)),
                     bg=C("card"), fg=C("text"),
                     justify="center", wraplength=pw - S(40)).pack(pady=S(8))
            tk.Label(self._popup_win,
                     text=f"将在 {sec} 秒后自动关闭",
                     font=("微软雅黑", FS(8)),
                     bg=C("card"), fg=C("subtext")).pack(pady=(0, S(8)))
            self._popup_win.after(sec * 1000, self._hide_popup)
            logger.info(f"[弹窗] 已显示，{sec}s 后自动关闭")
        except Exception as e:
            logger.error(f"[弹窗] 显示失败: {e}")

    def _hide_popup(self):
        """隐藏/销毁状态弹窗"""
        if self._popup_win and self._popup_win.winfo_exists():
            self._popup_win.destroy()
            self._popup_win = None
            logger.info("[弹窗] 已关闭")

    # ─────────────────────────────────────────────────────────────
    # § 7.12  自动保存防抖
    # ─────────────────────────────────────────────────────────────
    def _auto_save(self, delay: int = 800):
        """防抖自动保存：延迟 delay 毫秒后写入配置文件"""
        if self._save_after_id:
            self.after_cancel(self._save_after_id)
        self._save_after_id = self.after(delay, self._do_auto_save)

    def _do_auto_save(self):
        """执行实际保存"""
        save_config(self.cfg)
        self._save_after_id = None

    # ─────────────────────────────────────────────────────────────
    # § 7.13  日志追加（线程安全）
    # ─────────────────────────────────────────────────────────────
    def _append_log(self, text: str):
        self.after(0, lambda t=text: self._do_append(t))

    def _do_append(self, text: str):
        ts   = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {text}\n"
        max_l = int(self.cfg.get("log_max_lines", 2000))

        # 判断颜色标签
        tag = "INFO"
        if "WARN" in text:  tag = "WARN"
        if "ERROR" in text: tag = "ERROR"

        for widget in (
            getattr(self, "_log_text", None),
            getattr(self, "_home_log", None),
        ):
            if not widget or not widget.winfo_exists():
                continue
            widget.configure(state="normal")
            widget.insert("end", line, tag)
            cur = int(widget.index("end-1c").split(".")[0])
            if cur > max_l:
                widget.delete("1.0", f"{cur - max_l}.0")
            widget.see("end")
            widget.configure(state="disabled")

    # ─────────────────────────────────────────────────────────────
    # § 7.14  UI 辅助工具
    # ─────────────────────────────────────────────────────────────
    def _scrollable(self, parent: tk.Frame):
        """返回 (canvas, inner)，支持鼠标滚轮。"""
        outer = tk.Frame(parent, bg=C("bg"))
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=C("bg"), highlightthickness=0)
        vsb    = ttk.Scrollbar(outer, orient="vertical",
                                command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        inner = tk.Frame(canvas, bg=C("bg"))
        win   = canvas.create_window((0, 0), window=inner, anchor="nw")

        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(win, width=e.width))
        inner.bind("<Configure>",
                   lambda e: canvas.configure(
                       scrollregion=canvas.bbox("all")))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(
                            int(-e.delta / 60), "units"))

        inner.configure(padx=S(22), pady=S(14))
        return canvas, inner

    def _sec(self, parent, icon: str, title: str):
        """分节标题 + 分割线。"""
        f = tk.Frame(parent, bg=C("bg"))
        f.pack(fill="x", pady=(S(18), S(4)))
        tk.Label(f, text=f"{icon}  {title}",
                 font=("微软雅黑", FS(10), "bold"),
                 bg=C("bg"), fg=C("text")).pack(side="left")
        tk.Frame(f, bg=C("sep"), height=1).pack(
            side="left", fill="x", expand=True, padx=S(10), pady=S(7))

    @staticmethod
    def _intv(var, default: int) -> int:
        try: return int(var.get())
        except Exception: return default


# ══════════════════════════════════════════════════════════════════
#  § 8  程序入口
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 解析启动参数：news_player.exe play → 直接开始播放，不弹主窗口弹窗
    auto_play = "play" in [a.lower() for a in sys.argv[1:]]
    app = MainApp(auto_play=auto_play)
    app.mainloop()


# ══════════════════════════════════════════════════════════════════
#  § 9  打包命令（复制即用）
# ══════════════════════════════════════════════════════════════════
#
#  1. 安装依赖（首次）
#     pip install pyinstaller selenium pyautogui psutil
#

#
#  3. 如有自定义图标（.ico 文件）
#     pyinstaller --onefile --windowed --name "新闻播放器v4.x" --icon news30.ico app.py
#
#  4. 打包完成后，dist\ 目录下即为 EXE，按以下结构放置文件实现便携：
#
#     📁 便携目录/
#       ├── 新闻播放器.exe        ← PyInstaller 生成
#       ├── geckodriver.exe       ← Firefox WebDriver（与 EXE 同目录）
#       ├── config.json           ← 首次运行自动生成，可手动编辑
#       ├── logs/                 ← 日志目录（自动创建）
#       └── tools/
#             └── nircmd.exe      ← 可选，设置页中将工具目录改为 .\tools
