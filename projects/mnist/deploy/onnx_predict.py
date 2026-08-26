"""用 ONNX 模型推理 (对方视角: 不需要 PyTorch, 只有 onnxruntime)。

这是"把模型给别人"的最终形态:
  对方只需要: mnist_cnn.onnx + 本文件 + pip install onnxruntime
  不需要:      PyTorch / torchvision / 训练代码 / 数据集

用法: python onnx_predict.py                 # 测试集随机 10 张
      python onnx_predict.py 图片路径.png    # 预测自己的图片
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import onnxruntime as ort
from PIL import Image

# ---------- 路径 ----------
# 交付包自包含: 模型就在本目录 (与 serve.py 一致); 验证用的数据集在仓库根 datasets/
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, "..", "..", ".."))
DATA_ROOT = os.path.join(ROOT, "datasets", "mnist")

# ---------- ① 加载 ONNX 模型 (一句话, 结构权重都在这一个文件里) ----------
session = ort.InferenceSession(os.path.join(BASE, "mnist_cnn.onnx"), providers=["CPUExecutionProvider"])
print(f"✅ ONNX 模型加载成功 (推理引擎: {ort.__version__})")

# MNIST 归一化参数 (和训练时一致)
MEAN, STD = 0.1307, 0.3081


def preprocess(img):
    """图片 -> (1,1,28,28) float32 输入 (简化版预处理)。"""
    img = img.convert("L")
    arr = np.array(img, dtype=np.float32)
    if arr.mean() > 128:          # 白底深字 -> 反色成黑底白字
        arr = 255 - arr
    arr = (arr / 255.0 - MEAN) / STD    # 归一化
    return arr.reshape(1, 1, 28, 28).astype(np.float32)


def run_inference(tensor):
    # ---------- ② 推理: 一行代码 ----------
    logits = session.run(["logits"], {"image": tensor})[0]   # (1, 10) 得分
    pred = int(logits.argmax())
    probs = np.exp(logits - logits.max())                     # softmax
    probs /= probs.sum()
    return pred, float(probs[0, pred])


if len(sys.argv) > 1:
    img = Image.open(sys.argv[1])
    pred, conf = run_inference(preprocess(img))
    print(f"图片 {sys.argv[1]} 预测为: {pred} (置信度 {conf:.2%})")
else:
    # 用测试集验证 ONNX 与 PyTorch 结果一致
    from torchvision import datasets
    test_data = datasets.MNIST(DATA_ROOT, train=False, download=False)
    import torch
    idx = torch.randperm(len(test_data))[:10]
    correct = 0
    for i in idx:
        pil_img, true_label = test_data[i]
        pred, conf = run_inference(preprocess(pil_img))
        ok = pred == true_label
        correct += ok
        print(f"真实: {true_label} | ONNX 预测: {pred} | 置信度 {conf:.2%} {'✅' if ok else '❌'}")
    print(f"\n10 张猜对 {correct} 张 (应与 PyTorch 推理一致)")
