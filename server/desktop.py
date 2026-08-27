"""桌面版入口：启动门户服务 + 打开桌面窗口（无需浏览器）。

用法:
    python server/desktop.py        # 源码运行
    打包后: AI训练平台.exe 直接双击（PyInstaller 入口改为本文件）

关闭窗口即停止服务并退出程序。
"""
import os
import sys
import threading

sys.stdout.reconfigure(encoding="utf-8")

import webview

from http.server import ThreadingHTTPServer

import app as portal   # 复用门户服务（模型加载 + 全部 API）


def main():
    # 后台线程启动 HTTP 服务
    httpd = ThreadingHTTPServer(("0.0.0.0", portal.PORT), portal.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://localhost:{portal.PORT}"
    print(f"✅ 服务已启动: {url}", flush=True)
    print("   桌面窗口即将打开，关闭窗口即退出程序。", flush=True)

    # 桌面窗口（Windows WebView2 内核，系统自带）
    window = webview.create_window(
        "AI 训练平台",
        url,
        width=1280,
        height=840,
        min_size=(980, 640),
        background_color="#10204f",
    )
    webview.start()

    # 窗口关闭 → 停止服务并退出
    httpd.shutdown()
    print("窗口已关闭，服务停止。", flush=True)


if __name__ == "__main__":
    main()
