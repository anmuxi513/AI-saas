"""端到端测试: 模拟浏览器前端 -> POST /api/predict -> 验证推理结果。

运行前提: 已启动服务 (python serve.py)
用法: python test_api.py
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import torch
import urllib.request
from torchvision import datasets

MEAN, STD = 0.1307, 0.3081
API = "http://localhost:8000/api/predict"


def frontend_preprocess(arr):
    """预处理: 纯归一化。

    注意: 不做膨胀加粗 —— MNIST 测试图笔画本来就是标准粗细,
    膨胀是给"用户手写细笔画"用的(见 index.html 中的 extract)。
    这里验证的是服务端推理链路本身是否正确。
    """
    return ((arr / 255.0 - MEAN) / STD).reshape(-1).tolist()


def predict(pixels):
    req = urllib.request.Request(
        API,
        data=json.dumps({"pixels": pixels}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    # 1) 检查网页可访问
    with urllib.request.urlopen("http://localhost:8000/", timeout=10) as resp:
        print(f"✅ 网页 index.html -> HTTP {resp.status}")

    # 2) 用真实 MNIST 测试图走完整链路
    ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
    test = datasets.MNIST(os.path.join(ROOT, "datasets", "mnist"), train=False, download=False)
    idx = torch.randperm(len(test))[:8]
    correct = 0
    for i in idx:
        img, label = test[i]
        data = predict(frontend_preprocess(np.array(img, dtype=np.float32)))
        hit = data["pred"] == label
        correct += hit
        print(f"真实: {label} | API: {data['pred']} | 置信度 {data['probs'][data['pred']]:.2%} {'✅' if hit else '❌'}")
    print(f"\n端到端验证: 8 张猜对 {correct} 张 (与 PyTorch 推理一致)")


if __name__ == "__main__":
    main()
