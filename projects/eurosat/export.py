"""EuroSAT 模型导出 ONNX (企业级部署格式, 跨平台)。

运行前提: 已有 eurosat_resnet18.pth (由 train.py 训练)
用法: python export.py
"""
import json
import os
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

import torch
import torch.nn as nn
from torchvision import models

# ---------- 路径 (整理后: 权重在本模块 models/, 数据集在仓库根 datasets/) ----------
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, "..", ".."))
MODELS_DIR = os.path.join(BASE, "models")
DATA_DIR = os.path.join(ROOT, "datasets", "eurosat")

# 与训练时完全一致的模型结构
model = models.resnet18(weights=None)
model.fc = nn.Linear(model.fc.in_features, 10)
model.load_state_dict(torch.load(os.path.join(MODELS_DIR, "eurosat_resnet18.pth"), map_location="cpu"))
model.eval()

# 输入形状: (batch, 3通道, 224, 224) — 与训练预处理一致
dummy = torch.randn(1, 3, 224, 224)
torch.onnx.export(
    model,
    dummy,
    os.path.join(MODELS_DIR, "eurosat_resnet18.onnx"),
    input_names=["image"],
    output_names=["logits"],
    dynamic_axes={"image": {0: "batch"}},
    opset_version=18,
)
print(f"✅ 已导出: {os.path.join(MODELS_DIR, 'eurosat_resnet18.onnx')}")

with open(os.path.join(DATA_DIR, "class_names.json"), encoding="utf-8") as f:
    classes = json.load(f)
print(f"类别映射 ({len(classes)} 类): {classes}")
