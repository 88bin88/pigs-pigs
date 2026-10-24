@echo off
chcp 65001 >nul
echo ============================================
echo   公告看板 - 一键打包脚本 (PyInstaller)
echo ============================================
echo.

echo [1/3] 安装依赖...
python -m pip install -U pywebview pystray pillow requests pyinstaller
if errorlevel 1 (
  echo 依赖安装失败，请检查网络后重试
  pause
  exit /b 1
)

echo.
echo [2/3] 开始打包 (单文件模式，HTML/CSS 已内嵌)...
python -m PyInstaller --noconfirm --clean ^
  --noconsole --onefile ^
  --name "NoticeBoard" ^
  --add-data "index.html;." ^
  main.py
if errorlevel 1 (
  echo 打包失败
  pause
  exit /b 1
)

echo.
echo [3/3] 打包完成！
echo 成品位置: %cd%\dist\NoticeBoard.exe
echo 说明: 单文件exe，HTML/CSS已打包进exe内部，可直接拷给其他电脑运行。
echo 注意: 目标电脑需安装 WebView2 运行时（Win10/11 一般自带）。
echo.
pause
