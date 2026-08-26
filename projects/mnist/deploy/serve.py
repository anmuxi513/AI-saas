"""MNIST ONNX 推理服务: 托管网页 + 提供 /api/predict 推理接口。

这是"把模型交付给别人"的服务端形态 —— 和真实项目架构一致:
  浏览器(前端手写板)  --POST /api/predict-->  本服务(onnxruntime 推理)

对方使用:
  pip install onnxruntime
  python serve.py
  浏览器打开 http://localhost:8000

依赖: 仅 onnxruntime (不需要 torch / torchvision / 训练代码)
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")   # Windows 控制台默认 GBK, 强制 UTF-8

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

import numpy as np
import onnxruntime as ort

# PyInstaller 打包后运行在临时解压目录 (sys._MEIPASS), 未打包时用脚本所在目录
if getattr(sys, "frozen", False):
    BASE = sys._MEIPASS
else:
    BASE = os.path.dirname(os.path.abspath(__file__))

MODEL = os.path.join(BASE, "mnist_cnn.onnx")
PORT = 8000

# 前端页面统一由 Vue 3 工程提供（frontend/dist，`npm run build` 生成）：
# 本服务只负责 API + 静态托管，页面全部来自新前端
WORKSPACE = os.path.abspath(os.path.join(BASE, "..", "..", ".."))
DIST = os.path.join(WORKSPACE, "frontend", "dist")
INDEX = os.path.join(DIST, "index.html")

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
}

# 模型加载: 结构 + 权重都在一个 ONNX 文件里
session = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])
print(f"✅ 模型加载成功: {MODEL} (onnxruntime {ort.__version__})")
if os.path.isfile(INDEX):
    print(f"   浏览器打开: http://localhost:{PORT}")
else:
    print(f"⚠️  未找到前端构建产物: {INDEX}")
    print(f"   请先执行: cd frontend && npm run build")


def softmax(logits):
    e = np.exp(logits - logits.max())
    return e / e.sum()


class Handler(BaseHTTPRequestHandler):
    # ---------- GET: 托管前端构建产物（frontend/dist）----------
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/mnist_cnn.onnx":
            self._serve_file(MODEL, "application/octet-stream")
            return
        rel = "index.html" if path in ("/", "/index.html") else path.lstrip("/")
        target = os.path.join(DIST, rel)
        if os.path.isfile(target):
            ext = os.path.splitext(target)[1].lower()
            self._serve_file(target, MIME.get(ext, "application/octet-stream"))
        else:
            self.send_error(404, "Not Found")

    # ---------- POST /api/predict: 推理接口 ----------
    # 请求: {"pixels": [784 个归一化后的 float]}  (前端已完成预处理)
    # 返回: {"pred": 数字, "probs": [10 个概率]}
    def do_POST(self):
        if urlparse(self.path).path != "/api/predict":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            x = np.array(body["pixels"], dtype=np.float32).reshape(1, 1, 28, 28)
            logits = session.run(["logits"], {"image": x})[0][0]
            probs = softmax(logits)
            pred = int(np.argmax(probs))
            resp = json.dumps({"pred": pred, "probs": [float(p) for p in probs]})
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(resp.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(resp.encode("utf-8"))
        except Exception as e:
            resp = json.dumps({"error": str(e)}).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)

    def _serve_file(self, name, ctype):
        try:
            with open(name, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_error(404)

    def log_message(self, fmt, *args):
        sys.stdout.write(f"[{self.address_string()}] {fmt % args}\n")


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
