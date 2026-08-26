"""语言对话模型加载封装（唯一来源）。

与 mnist/model.py 定位相同：所有脚本统一从这里拿模型，
保证「模型结构/权重来源只有一处」。

模型: Qwen/Qwen2.5-0.5B-Instruct（约 1GB，CPU 可流畅运行）
- 中文对话效果好，是这个尺寸下最合适的选择
- 权重缓存到本目录 models/ （与各项目 models/ 约定一致）

用法:
    from model import get_model, get_tokenizer
    model, tokenizer = get_model()   # 首次调用会自动下载，之后秒加载

注意:
- 国内网络下载慢/失败时，先执行:
    $env:HF_ENDPOINT = "https://hf-mirror.com"   (PowerShell)
  or export HF_ENDPOINT=https://hf-mirror.com    (Linux/macOS)
  脚本完全尊重该环境变量（transformers 原生支持）。
"""
import os

# Windows 无管理员权限时无法创建符号链接（WinError 1314），
# 让 huggingface_hub 用复制文件的方式组织缓存；并关闭 xet 存储后端
# （两者都必须在 import transformers 之前设置）
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"

BASE = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE, "models")

# 模型加载时打印的消息
_INIT_MSG = f"正在加载模型 {MODEL_NAME}（首次运行会从 HuggingFace 下载约 1GB，请耐心等待）..."

_holder = {"model": None, "tokenizer": None}


def _load():
    """真正加载模型（只执行一次）。"""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    os.makedirs(MODELS_DIR, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        cache_dir=MODELS_DIR,
        trust_remote_code=True,
    )
    # CPU 环境: float32；纯 CPU 版 PyTorch 默认就在 CPU 上，无需 device_map（那需要 accelerate）
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        cache_dir=MODELS_DIR,
        dtype=torch.float32,
        trust_remote_code=True,
    )
    model.eval()
    return model, tokenizer


def get_model():
    """返回 (model, tokenizer)，懒加载单例。"""
    if _holder["model"] is None:
        print(_INIT_MSG, flush=True)
        _holder["model"], _holder["tokenizer"] = _load()
    return _holder["model"], _holder["tokenizer"]


def get_tokenizer():
    return get_model()[1]
