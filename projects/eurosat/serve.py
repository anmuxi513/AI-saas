"""EuroSAT 遥感地物识别服务: 网页上传图片 → 分类识别。

企业级部署形态: ONNX 模型 + HTTP API + 浏览器前端
  (与 projects/mnist/deploy 相同的架构, 模型换成了真实遥感分类模型)

用法:
  python serve.py
  浏览器打开 http://localhost:8001

依赖: pip install onnxruntime pillow
"""
import base64
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

import numpy as np
import onnxruntime as ort
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, "..", ".."))
MODEL = os.path.join(BASE, "models", "eurosat_resnet18.onnx")
PORT = 8001

# 前端页面统一由 Vue 3 工程提供（frontend/dist，`npm run build` 生成）：
# 本服务只负责 API + 静态托管，页面全部来自新前端
DIST = os.path.join(ROOT, "frontend", "dist")
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
CLASS_NAMES_CN = {
    "AnnualCrop": "农作物", "Forest": "森林", "HerbaceousVegetation": "草本植被",
    "Highway": "高速公路", "Industrial": "工业区", "Pasture": "牧场",
    "PermanentCrop": "多年生作物", "Residential": "居民区", "River": "河流", "SeaLake": "海洋/湖泊",
}
with open(os.path.join(ROOT, "datasets", "eurosat", "class_names.json"), encoding="utf-8") as f:
    CLASS_LIST = json.load(f)   # 索引 -> 英文类别名
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

session = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])
print(f"✅ 模型加载成功: {MODEL} (onnxruntime {ort.__version__})")
if os.path.isfile(INDEX):
    print(f"   浏览器打开: http://localhost:{PORT}")
else:
    print(f"⚠️  未找到前端构建产物: {INDEX}")
    print(f"   请先执行: cd frontend && npm run build")


def preprocess(img):
    """上传图片 → (1,3,224,224) 归一化张量 (与训练预处理一致)。"""
    img = img.convert("RGB").resize((224, 224), Image.LANCZOS)
    arr = np.asarray(img, dtype=np.float32) / 255.0
    for c in range(3):
        arr[:, :, c] = (arr[:, :, c] - IMAGENET_MEAN[c]) / IMAGENET_STD[c]
    return arr.transpose(2, 0, 1)[None].astype(np.float32)


def softmax(x):
    e = np.exp(x - x.max())
    return e / e.sum()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        rel = "index.html" if path in ("/", "/index.html") else path.lstrip("/")
        target = os.path.join(DIST, rel)
        if os.path.isfile(target):
            ext = os.path.splitext(target)[1].lower()
            self._serve_file(target, MIME.get(ext, "application/octet-stream"))
        else:
            self.send_error(404)

    def do_POST(self):
        if urlparse(self.path).path != "/api/predict":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            img = Image.open(io.BytesIO(base64.b64decode(body["image"])))
            x = preprocess(img)
            logits = session.run(["logits"], {"image": x})[0][0]
            probs = softmax(logits)
            order = np.argsort(probs)[::-1]
            results = [{
                "index": int(i),
                "name": CLASS_NAMES_CN.get(CLASS_LIST[int(i)], CLASS_LIST[int(i)]),
                "prob": float(probs[i]),
            } for i in order[:3]]
            resp = json.dumps({"results": results}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
        except Exception as e:
            resp = json.dumps({"error": str(e)}).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)

    def _serve_file(self, name, ctype):
        with open(name, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        sys.stdout.write(f"[{self.address_string()}] {fmt % args}\n")


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
