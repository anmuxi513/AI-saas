"""AI 模型训练平台 · 统一门户服务（单端口 6660）。

一个服务整合所有能力:
  - 前端页面托管        frontend/dist 的 Vue 3 构建产物
  - 聊天对话 API        SSE 流式（本地 Qwen2.5-0.5B，复用 projects/chat 引擎）
  - MNIST 识别 API      ONNX 手写数字识别（projects/mnist/deploy）
  - EuroSAT 识别 API    ONNX 遥感地物分类（projects/eurosat）

用法:
  python projects/portal/app.py
  浏览器打开 http://localhost:6660

依赖: onnxruntime pillow transformers torch（均已在各模块使用过）
"""
import base64
import io
import json
import os
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
from PIL import Image

# ---------------- 路径 ----------------
# 打包版（PyInstaller）: 资源在 _MEIPASS，用户数据在 exe 同目录
if getattr(sys, "frozen", False):
    BASE = sys._MEIPASS
    WORKSPACE = BASE
    APP_DIR = os.path.dirname(sys.executable)            # exe 所在目录
    DIST = os.path.join(BASE, "frontend", "dist")
    INDEX = os.path.join(DIST, "index.html")
    MNIST_ONNX = os.path.join(BASE, "models", "mnist_cnn.onnx")
    EUROSAT_ONNX = os.path.join(BASE, "models", "eurosat_resnet18.onnx")
    CLASS_NAMES = os.path.join(BASE, "datasets", "eurosat", "class_names.json")
    CHAT_MODEL_DIR = os.path.join(APP_DIR, "chat_model", "Qwen2.5-0.5B-Instruct")
else:
    BASE = os.path.dirname(os.path.abspath(__file__))
    WORKSPACE = os.path.abspath(os.path.join(BASE, ".."))   # server/ 为顶层服务层
    APP_DIR = WORKSPACE
    DIST = os.path.join(WORKSPACE, "frontend", "dist")
    INDEX = os.path.join(DIST, "index.html")
    MNIST_ONNX = os.path.join(WORKSPACE, "projects", "mnist", "deploy", "mnist_cnn.onnx")
    EUROSAT_ONNX = os.path.join(WORKSPACE, "projects", "eurosat", "models", "eurosat_resnet18.onnx")
    CLASS_NAMES = os.path.join(WORKSPACE, "datasets", "eurosat", "class_names.json")
    CHAT_MODEL_DIR = ""

CHAT_DIR = os.path.join(WORKSPACE, "projects", "chat")

PORT = 6660   # 注意: 6665-6669 被浏览器列为不安全端口（IRC），不可用
MAX_SESSIONS = 20          # 聊天会话上限（超出淘汰最旧）
MAX_PROB_BARS = 10         # MNIST 概率条数量（10 个数字）

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

# ---------------- ONNX 推理（启动时加载，轻量） ----------------
import onnxruntime as ort

_mnist_session = ort.InferenceSession(
    MNIST_ONNX, providers=["CPUExecutionProvider"])
print("✅ MNIST 模型加载成功", flush=True)

_eurosat_session = ort.InferenceSession(
    EUROSAT_ONNX, providers=["CPUExecutionProvider"])
with open(CLASS_NAMES, encoding="utf-8") as f:
    _CLASS_LIST = json.load(f)
_CLASS_NAMES_CN = {
    "AnnualCrop": "农作物", "Forest": "森林", "HerbaceousVegetation": "草本植被",
    "Highway": "高速公路", "Industrial": "工业区", "Pasture": "牧场",
    "PermanentCrop": "多年生作物", "Residential": "居民区", "River": "河流",
    "SeaLake": "海洋/湖泊",
}
_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD = [0.229, 0.224, 0.225]
print("✅ EuroSAT 模型加载成功", flush=True)


def _softmax(x):
    e = np.exp(x - x.max())
    return e / e.sum()


def _mnist_predict(pixels):
    x = np.array(pixels, dtype=np.float32).reshape(1, 1, 28, 28)
    logits = _mnist_session.run(["logits"], {"image": x})[0][0]
    probs = _softmax(logits)
    return {"pred": int(np.argmax(probs)), "probs": [float(p) for p in probs]}


def _eurosat_predict(img):
    img = img.convert("RGB").resize((224, 224), Image.LANCZOS)
    arr = np.asarray(img, dtype=np.float32) / 255.0
    for c in range(3):
        arr[:, :, c] = (arr[:, :, c] - _IMAGENET_MEAN[c]) / _IMAGENET_STD[c]
    x = arr.transpose(2, 0, 1)[None].astype(np.float32)
    probs = _softmax(_eurosat_session.run(["logits"], {"image": x})[0][0])
    order = np.argsort(probs)[::-1]
    return [{
        "index": int(i),
        "name": _CLASS_NAMES_CN.get(_CLASS_LIST[int(i)], _CLASS_LIST[int(i)]),
        "prob": float(probs[i]),
    } for i in order[:3]]


from PIL import Image  # noqa: E402（在 eurosat 预处理前导入）


# ---------------- 聊天引擎（后台预加载，约 1GB 权重） ----------------
if not getattr(sys, "frozen", False):
    # 源码运行: projects/chat 需加入搜索路径；打包版由 PyInstaller 收集（--paths）
    sys.path.insert(0, CHAT_DIR)
from chat import ChatEngine  # noqa: E402

_chat_ready = False
_chat_error = None
_loading_msg = "⏳ 聊天模型加载中（Qwen2.5-0.5B，约需 10-60 秒）..."


def _load_chat_model():
    """后台线程: 预加载语言模型，加载完成前聊天接口返回 503。"""
    global _chat_ready, _chat_error
    try:
        if getattr(sys, "frozen", False):
            # 打包版：模型需先通过 tools/下载聊天模型 安装到 exe 旁 chat_model/
            if not os.path.isdir(CHAT_MODEL_DIR) or not os.listdir(CHAT_MODEL_DIR):
                _chat_error = ("聊天模型未安装：请运行同目录下「下载聊天模型.exe」（约 1GB，"
                               "自动使用国内镜像下载）。下载完成后重启本程序即可对话。")
                print(f"⚠️  {_chat_error}", flush=True)
                return
            os.environ["QWEN_MODEL_NAME"] = CHAT_MODEL_DIR
            os.environ["QWEN_MODEL_DIR"] = os.path.dirname(CHAT_MODEL_DIR)
        from model import get_model
        get_model()
        _chat_ready = True
        print("✅ 聊天模型加载成功，对话功能可用", flush=True)
    except Exception as e:  # noqa: BLE001
        _chat_error = str(e)
        print(f"❌ 聊天模型加载失败: {e}", flush=True)


threading.Thread(target=_load_chat_model, daemon=True).start()

SESSIONS: dict = {}          # sid -> ChatEngine
_SESSIONS_LOCK = threading.RLock()   # RLock: 可重入，避免 _title_of 等嵌套加锁死锁
_META: dict = {}             # sid -> {"title": str, "created": float, "updated": float}
DEFAULT_SYSTEM = "你是Qwen，一个乐于助人的中文AI助手。请用简洁、准确的中文回答。"


def _new_session(system: str | None = None) -> tuple[str, ChatEngine]:
    sid = uuid.uuid4().hex[:8]
    engine = ChatEngine(system=system or DEFAULT_SYSTEM)
    now = time.time()
    with _SESSIONS_LOCK:
        while len(SESSIONS) >= MAX_SESSIONS:
            old = next(iter(SESSIONS))
            SESSIONS.pop(old)
            _META.pop(old, None)
        SESSIONS[sid] = engine
        _META[sid] = {"title": "新对话", "created": now, "updated": now}
    return sid, engine


def _get_session(sid: str) -> ChatEngine | None:
    with _SESSIONS_LOCK:
        return SESSIONS.get(sid)


def _touch(sid: str):
    """更新会话活动时间。"""
    meta = _META.get(sid)
    if meta:
        meta["updated"] = time.time()


# ---------------- HTTP 处理 ----------------
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # ---------- 工具 ----------
    def _send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path):
        ext = os.path.splitext(path)[1].lower()
        ctype = MIME.get(ext, "application/octet-stream")
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        return json.loads(self.rfile.read(length))

    # ---------- GET ----------
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/status":
            self._send_json({
                "chat_ready": _chat_ready,
                "chat_error": _chat_error,
                "loading": not _chat_ready and _chat_error is None,
            })
            return
        if path == "/api/chat/list":
            with _SESSIONS_LOCK:
                sessions = [{
                    "sid": sid,
                    "title": _title_of(sid),
                    "created": _META[sid]["created"] if sid in _META else 0,
                    "updated": _META[sid]["updated"] if sid in _META else 0,
                } for sid in reversed(list(SESSIONS))]
            self._send_json({"sessions": sessions})
            return
        # 静态资源（前端 dist）
        rel = "index.html" if path in ("/", "/index.html") else path.lstrip("/")
        target = os.path.join(DIST, rel)
        if os.path.isfile(target):
            self._serve_file(target)
        else:
            self.send_error(404, "Not Found")

    # ---------- POST ----------
    def do_POST(self):
        path = urlparse(self.path).path
        try:
            if path == "/api/mnist/predict":
                body = self._read_json()
                self._send_json(_mnist_predict(body["pixels"]))
            elif path == "/api/eurosat/predict":
                body = self._read_json()
                img = Image.open(io.BytesIO(base64.b64decode(body["image"])))
                self._send_json({"results": _eurosat_predict(img)})
            elif path == "/api/chat/new":
                body = self._read_json()
                sid, engine = _new_session(body.get("system"))
                self._send_json({"session_id": sid, "title": _title_of(sid)})
            elif path == "/api/chat/history":
                body = self._read_json()
                engine = _get_session(body.get("session_id", ""))
                if not engine:
                    self._send_json({"error": "session not found"}, 404)
                    return
                msgs = [{"role": m["role"], "content": m["content"]}
                        for m in engine.messages if m["role"] != "system"]
                self._send_json({"messages": msgs})
            elif path == "/api/chat/delete":
                body = self._read_json()
                with _SESSIONS_LOCK:
                    SESSIONS.pop(body.get("session_id", ""), None)
                    _META.pop(body.get("session_id", ""), None)
                self._send_json({"ok": True})
            elif path == "/api/chat/clear":
                body = self._read_json()
                engine = _get_session(body.get("session_id", ""))
                if not engine:
                    self._send_json({"error": "session not found"}, 404)
                    return
                engine.reset()
                _set_title(body["session_id"], "新对话")
                self._send_json({"ok": True})
            elif path == "/api/chat/send":
                self._handle_chat_send()
            else:
                self._send_json({"error": "not found"}, 404)
        except KeyError as e:
            self._send_json({"error": f"missing field: {e}"}, 400)
        except Exception as e:  # noqa: BLE001
            self._send_json({"error": str(e)}, 400)

    # ---------- 聊天 SSE 流式 ----------
    def _handle_chat_send(self):
        if not _chat_ready:
            self._send_json({"error": "model_loading", "message": _loading_msg}, 503)
            return
        body = self._read_json()
        sid = body.get("session_id", "")
        engine = _get_session(sid)
        if not engine:
            self._send_json({"error": "session not found"}, 404)
            return
        message = (body.get("message") or "").strip()
        if not message:
            self._send_json({"error": "empty message"}, 400)
            return

        # 首条消息确定会话标题
        if not any(m["role"] == "user" for m in engine.messages):
            _set_title(sid, message[:20])
        _touch(sid)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        # SSE 必须用 chunked 传输（无 Content-Length），否则浏览器会一直等待响应结束
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

        def emit(obj):
            payload = f"data: {json.dumps(obj, ensure_ascii=False)}\n\n".encode("utf-8")
            self.wfile.write(f"{len(payload):X}\r\n".encode("utf-8") + payload + b"\r\n")
            self.wfile.flush()

        def finish_stream():
            # chunked 终止块 + 关闭连接
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
            self.close_connection = True

        try:
            for chunk in engine.stream_chat(message):
                emit({"delta": chunk})
            emit({"done": True, "title": _title_of(sid)})
            finish_stream()
        except Exception as e:  # noqa: BLE001
            try:
                emit({"error": str(e)})
                finish_stream()
            except Exception:  # noqa: BLE001 连接已断开
                pass

    def log_message(self, fmt, *args):
        sys.stdout.write(f"[{self.address_string()}] {fmt % args}\n")


# 会话标题存在 _META 里，避免污染 messages
def _set_title(sid: str, title: str):
    meta = _META.get(sid)
    if meta:
        meta["title"] = title


def _title_of(sid: str) -> str:
    meta = _META.get(sid)
    if not meta:
        return ""
    if meta["title"] != "新对话":
        return meta["title"]
    # 有历史时用最后一条用户消息
    with _SESSIONS_LOCK:
        engine = SESSIONS.get(sid)
    if engine:
        for m in reversed(engine.messages):
            if m["role"] == "user":
                return m["content"][:20]
    return "新对话"


if __name__ == "__main__":
    print(f"🚀 AI 模型训练平台门户启动: http://localhost:{PORT}")
    if not os.path.isfile(INDEX):
        print(f"⚠️  未找到前端构建产物: {INDEX}")
        print(f"   请先执行: cd frontend && npm run build")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
