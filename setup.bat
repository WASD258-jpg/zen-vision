@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo zen-vision 一键配置（看不懂教程的，跑这个就对了）
echo ==============================================
py -3 setup.py
if errorlevel 1 (
  echo.
  echo 出错了？试试手动执行: python setup.py
)
pause
