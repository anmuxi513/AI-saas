@echo off
chcp 65001 >nul
cd /d %~dp0
echo ============================================
echo  MNIST 手写数字识别服务
echo  启动后请用浏览器打开: http://localhost:8000
echo  关闭本窗口即停止服务
echo ============================================
python serve.py
pause
