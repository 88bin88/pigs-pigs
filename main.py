# -*- coding: utf-8 -*-
"""
公告看板主程序
功能：卡片看板 + 托盘驻留 + 媒体缓存（断网可用）
"""
import os
import sys
import uuid
import json
import socket
import threading
import ctypes

try:
    import requests
except ImportError:
    requests = None

import webview

# ---------------------------------------------------------------
# 缓存目录：放在用户文档目录，避免 onefile 打包后临时目录被清空
# ---------------------------------------------------------------
CACHE_FOLDER = os.path.join(os.path.expanduser("~"), "Documents", "NoticeBoard_cache")
DATA_FILE = os.path.join(CACHE_FOLDER, "cards.json")
os.makedirs(CACHE_FOLDER, exist_ok=True)

DEVICE_ID = "NB-" + str(uuid.getnode())[-6:].upper()

# ---------------------------------------------------------------
# 启动地址：优先加载线上网址（GitHub Pages），连不上回退本地文件
# ---------------------------------------------------------------
ONLINE_URL = "https://88bin88.github.io/pigs-pigs/"
LOCAL_HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
MEDIA_PORT = 8124


def _pick_start_url():
    """能访问线上网址就用线上（自动最新版），否则用本地（离线可用）"""
    if requests is not None:
        try:
            r = requests.get(ONLINE_URL, timeout=6)
            if r.status_code == 200:
                return ONLINE_URL
        except Exception:
            pass
    return LOCAL_HTML


def _start_media_server():
    """把缓存目录做成 http://127.0.0.1:8124/xxx 静态服务，
    让 https 线上页面也能加载本地缓存的图片/视频（Chromium 允许 https 加载 localhost）"""
    import functools
    import http.server

    class _Handler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            super().end_headers()

        def log_message(self, fmt, *args):
            pass

    handler = functools.partial(_Handler, directory=CACHE_FOLDER)
    try:
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", MEDIA_PORT), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    except OSError:
        pass  # 端口被占用说明服务已在运行


class Api:
    """前端 js_api 调用的接口"""

    def getDeviceCode(self):
        """返回本机设备码"""
        return DEVICE_ID

    def downloadMedia(self, url, filename):
        """下载图片/GIF/视频到本地缓存，返回 http://127.0.0.1:8124/xxx 本地服务地址"""
        if requests is None:
            return url
        try:
            save_path = os.path.join(CACHE_FOLDER, filename)
            if not os.path.exists(save_path):
                resp = requests.get(url, timeout=15)
                if resp.status_code == 200:
                    with open(save_path, "wb") as f:
                        f.write(resp.content)
            return f"http://127.0.0.1:{MEDIA_PORT}/{filename}"
        except Exception as e:
            print("媒体下载失败:", e)
        return url

    def saveCards(self, data):
        """前端把卡片数据存到本地文件（离线缓存用）"""
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            return True
        except Exception as e:
            print("保存卡片失败:", e)
            return False

    def loadCards(self):
        """前端读取本地缓存卡片"""
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print("读取卡片缓存失败:", e)
        return None

    def getCachePath(self):
        """返回缓存文件夹路径，前端可展示"""
        return CACHE_FOLDER

    def showNotify(self, title, text):
        """接收前端发来的通知（打印日志，可扩展系统通知）"""
        print(f"[通知] {title}: {text}")
        return True

    # ---------------- 多电脑协作 ----------------
    def getLocalIP(self):
        """获取本机局域网IP，方便配置协作服务器地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def syncPush(self, url, group, cards):
        """前端调用：把本地卡片全量推送到协作服务器，返回服务器合并后的最新列表"""
        if requests is None:
            return None
        try:
            r = requests.post(
                url.rstrip("/") + "/api/sync",
                json={"group": group, "cards": cards},
                timeout=10,
            )
            if r.status_code == 200:
                j = r.json()
                if j.get("ok"):
                    return j.get("cards", [])
        except Exception as e:
            print("推送同步失败:", e)
        return None

    def syncPull(self, url, group):
        """前端调用：从协作服务器拉取本组公告列表"""
        if requests is None:
            return None
        try:
            r = requests.get(
                url.rstrip("/") + "/api/sync",
                params={"group": group},
                timeout=10,
            )
            if r.status_code == 200:
                j = r.json()
                if j.get("ok"):
                    return j.get("cards", [])
        except Exception as e:
            print("拉取同步失败:", e)
        return None


# ---------------------------------------------------------------
# 托盘
# ---------------------------------------------------------------
_tray_icon = None


def _on_show():
    try:
        webview.windows[0].show()
        webview.windows[0].restore()
    except Exception:
        pass


def _on_quit():
    try:
        _tray_icon.stop()
    except Exception:
        pass
    try:
        webview.windows[0].destroy()
    except Exception:
        pass
    os._exit(0)


def _setup_tray():
    import pystray
    from PIL import Image
    global _tray_icon
    # 生成一个简单的蓝色图标
    img = Image.new("RGB", (64, 64), (52, 120, 220))
    _tray_icon = pystray.Icon(
        "notice_board",
        img,
        "公告看板",
        menu=pystray.Menu(
            pystray.MenuItem("显示窗口", lambda: _on_show()),
            pystray.MenuItem("退出", lambda: _on_quit()),
        ),
    )
    _tray_icon.run_detached()


def _check_webview2():
    """检查 WebView2 运行时是否安装，缺失则提示"""
    try:
        import webview.util as _u
        if _u.gui == "edgechromium":
            key_paths = [
                r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
                r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
            ]
            import winreg
            found = False
            for kp in key_paths:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, kp) as key:
                        winreg.QueryValueEx(key, "pv")
                        found = True
                        break
                except OSError:
                    continue
            if not found:
                ctypes.windll.user32.MessageBoxW(
                    0,
                    "未检测到 WebView2 运行时。\n\n程序需要微软 Edge WebView2 才能显示界面。\n请从微软官网下载并安装 WebView2 常驻版（Evergreen Standalone）。",
                    "公告看板 - 缺少组件",
                    0x10 | 0x40000,
                )
    except Exception:
        pass


if __name__ == "__main__":
    _check_webview2()
    _start_media_server()
    api = Api()
    start_url = _pick_start_url()
    print("启动加载:", start_url)
    window = webview.create_window(
        "公告看板",
        start_url,
        js_api=api,
        width=1120,
        height=720,
        min_size=(800, 500),
    )
    # 点关闭按钮 -> 隐藏到托盘而不是退出
    window.events.closing += lambda: (window.hide(), False)
    webview.start(_setup_tray)
