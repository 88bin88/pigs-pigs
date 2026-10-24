# 公告看板 NoticeBoard

一个本地运行的公告/通知看板桌面程序（Python + pywebview），支持卡片拖拽、离线缓存、多电脑协作同步。

## 功能

- 📋 卡片看板：新建、编辑、删除、拖拽、双击放大
- 🔔 新公告右下角弹窗通知
- 📶 离线缓存：联网时自动缓存文字与媒体素材，断网照常查看
- 🖥️ 托盘驻留：点关闭隐藏到托盘，后台运行
- 🤝 多电脑协作：一台电脑跑 server.py，其他电脑输入服务器地址 + 组号即可互相同步公告

## 文件说明

| 文件 | 作用 |
|---|---|
| `main.py` | 主程序（pywebview 窗口 + 托盘 + 缓存 + 同步接口） |
| `index.html` | 前端界面（界面样式 + 离线缓存 + 协作面板） |
| `server.py` | 协作中转服务器（任一台电脑运行，端口 8123） |
| `build.bat` | 一键打包成单文件 exe（PyInstaller） |

## 快速开始

```bash
# 安装依赖
pip install pywebview pystray pillow requests pyinstaller

# 运行
python main.py
```

## 打包成 exe

```bash
build.bat
```

打包产物：`dist/NoticeBoard.exe`，单文件，HTML/CSS 已内嵌，可直接拷到其他电脑运行。

> 目标电脑需安装 WebView2 运行时（Windows 10/11 一般自带）。

## 多电脑协作

1. 选一台电脑运行 `python server.py`，记住显示的局域网地址（如 `http://192.168.1.100:8123`）
2. 其他电脑打开程序，点顶部「协作」按钮
3. 填服务器地址 + 相同组号 → 连接协作

同一组号的电脑会每 10 秒自动同步一次公告；断网自动切回本地缓存。
