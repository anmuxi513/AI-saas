"""桌面版入口：启动门户服务 + 打开桌面窗口（无需浏览器）。

- 无控制台窗口（打包版 noconsole）：日志写入 <程序目录>/logs/app.log
- 启动画面 → 服务就绪后自动切换到主应用
- 关闭窗口即停止服务并退出
"""
import os
import sys
import threading
import time
import urllib.request


def _init_logging():
    """打包版（windowed，无控制台）: 日志重定向到 <exe 目录>/logs/app.log。

    注意: 不能靠 sys.stdout is None 判断——PyInstaller 6 windowed 模式
    的 stdout 可能仍是有效句柄（继承父进程管道），需无条件重定向。
    """
    if not getattr(sys, "frozen", False):
        return   # 源码运行: 保留控制台输出
    try:
        log_dir = os.path.join(os.path.dirname(sys.executable), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log = open(os.path.join(log_dir, "app.log"), "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = log
    except Exception:  # noqa: BLE001 兜底: 丢弃输出
        sys.stdout = sys.stderr = open(os.devnull, "w")


_init_logging()

import webview  # noqa: E402
from http.server import ThreadingHTTPServer  # noqa: E402

import app as portal  # noqa: E402（复用门户服务：模型加载 + 全部 API）


def _splash_url() -> str | None:
    if getattr(sys, "frozen", False):
        p = os.path.join(sys._MEIPASS, "splash.html")
    else:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "splash.html")
    if not os.path.isfile(p):
        return None
    return "file:///" + p.replace("\\", "/")


def main():
    # 后台线程启动 HTTP 服务
    httpd = ThreadingHTTPServer(("0.0.0.0", portal.PORT), portal.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://localhost:{portal.PORT}"
    print(f"✅ 服务已启动: {url}", flush=True)

    # 先显示启动画面，服务就绪后自动切换到主应用
    splash = _splash_url()
    window = webview.create_window(
        "AImomo",
        splash or url,
        width=1280,
        height=840,
        min_size=(980, 640),
        background_color="#10204f",
    )

    def _wait_ready():
        for _ in range(180):   # 最多等 3 分钟（首次 import 慢）
            try:
                with urllib.request.urlopen(url, timeout=2):
                    break
            except Exception:  # noqa: BLE001
                time.sleep(1)
        try:
            window.load_url(url)
        except Exception:  # noqa: BLE001 窗口可能已关闭
            pass

    threading.Thread(target=_wait_ready, daemon=True).start()
    webview.start()

    # 窗口关闭 → 停止服务并退出
    httpd.shutdown()
    print("窗口已关闭，服务停止。", flush=True)


if __name__ == "__main__":
    main()
