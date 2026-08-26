"""把训练好的模型导出为 ONNX 格式 (跨平台通用格式)。

为什么用 ONNX?
  - 对方不需要安装 PyTorch, 任何语言都能推理 (Python/JS/C++/Java/C#...)
  - 可以在浏览器里跑 (onnxruntime-web, 配 CesiumJS/OpenLayers 项目很合适)
  - 可以在手机上跑 (Android/iOS), 在服务端跑 (Spring Boot 里调 Java API)

运行: python export_onnx.py
产物: mnist_cnn.onnx (模型 + 结构一体, 约 1.7 MB)
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

import torch
from model import CNN

# ---------- 路径 (整理后: 权重在本模块 models/) ----------
BASE = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

model = CNN()
model.load_state_dict(torch.load(os.path.join(MODELS_DIR, "mnist_cnn.pth"), map_location="cpu"))
model.eval()

# 声明输入形状: (batch=1, 通道=1, 28, 28)
dummy_input = torch.randn(1, 1, 28, 28)

torch.onnx.export(
    model,                      # 模型
    dummy_input,                # 示例输入 (只为确定形状)
    os.path.join(MODELS_DIR, "mnist_cnn.onnx"),  # 输出文件
    input_names=["image"],      # 输入节点名
    output_names=["logits"],    # 输出节点名: 10 个数字的得分
    dynamic_axes={"image": {0: "batch"}},   # 允许任意 batch 数
    opset_version=14,
)
print(f"✅ 已导出: {os.path.join(MODELS_DIR, 'mnist_cnn.onnx')}")
print("   ONNX = 模型结构 + 权重 一体, 对方不需要 PyTorch")
