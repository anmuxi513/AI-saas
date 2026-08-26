"""一键下载聊天模型（Qwen2.5-0.5B-Instruct，约 1GB）。

用法（打包版）: 双击本程序，或命令行运行
    python server/tools/download_chat_model.py

下载位置: <程序目录>/chat_model/Qwen2.5-0.5B-Instruct
自动使用国内镜像 hf-mirror.com（可改环境变量 HF_ENDPOINT 覆盖）。
下载完成后重启门户服务即可对话。
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

# 与 projects/chat/model.py 保持一致的 Windows 兼容设置（必须在 import transformers 前）
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
# 国内镜像（可被外部 HF_ENDPOINT 覆盖）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

MODEL_REPO = "Qwen/Qwen2.5-0.5B-Instruct"


def target_dir() -> str:
    """下载目标目录: exe/脚本同级的 chat_model/。"""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    return os.path.join(base, "chat_model", "Qwen2.5-0.5B-Instruct")


def main():
    dest = target_dir()
    os.makedirs(dest, exist_ok=True)
    print(f"📥 目标位置: {dest}")
    print(f"   模型: {MODEL_REPO}（约 1GB，首次下载需要几分钟到几十分钟）")
    print(f"   镜像: {os.environ.get('HF_ENDPOINT', '默认 HuggingFace')}")
    print("开始下载...\n")

    from huggingface_hub import snapshot_download

    snapshot_download(MODEL_REPO, local_dir=dest)

    print("\n✅ 下载完成！")
    print(f"   模型已保存到: {dest}")
    print("   请重启门户服务（AI训练平台.exe），即可使用聊天功能。")
    print("\n   提示：如果下载失败，可手动设置镜像后重试：")
    print("      set HF_ENDPOINT=https://hf-mirror.com")
    print("      然后重新运行本程序")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"\n❌ 下载失败: {e}")
        print("   可尝试: 1) 检查网络  2) 更换镜像（设置 HF_ENDPOINT 环境变量）")
        sys.exit(1)
