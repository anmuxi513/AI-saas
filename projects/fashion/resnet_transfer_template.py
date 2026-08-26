"""标准迁移学习模板: ImageNet 预训练 ResNet18 → 自己的数据集微调。

这是实际工作中最常用的"AI 使用姿势":
  1. 下载在 ImageNet (1400万张图) 上预训练好的 ResNet18
  2. 替换最后一层分类头, 匹配你的类别数
  3. 用小学习率微调 (或只训练分类头)

与 transfer_learning.py 的区别: 那里用自己训练的 MNIST 权重做源,
这里用官方 ImageNet 预训练权重 (download.pytorch.org), 适用于任意图片数据集。

用法 (示例: CIFAR-10 彩色图):
  pip install torchvision
  python resnet_transfer_template.py
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models

# ---------- 路径 (整理后: 数据集统一放仓库根 datasets/, 权重存本模块 models/) ----------
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, "..", ".."))
DATA_ROOT = os.path.join(ROOT, "datasets", "cifar")
MODELS_DIR = os.path.join(BASE, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# ---------- 超参数 ----------
BATCH_SIZE = 64
EPOCHS = 5
LR = 1e-3           # 微调用小学习率 (预训练权重已经很好了, 步子要小)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
NUM_CLASSES = 10    # 改成你自己的类别数
print(f"使用设备: {DEVICE}")

# ---------- 1. 数据: 与 ImageNet 预训练匹配的预处理 ----------
# 预训练模型"见过"的是 224x224 的彩色图, 必须用相同的归一化参数
transform = transforms.Compose([
    transforms.Resize(224),                    # 预训练模型输入尺寸
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],  # ImageNet 统计值
                         std=[0.229, 0.224, 0.225]),
])

# 换成你自己的数据: 把图片按 类别名/图片 组织, ImageFolder 直接加载
train_data = datasets.CIFAR10(DATA_ROOT, train=True, download=True, transform=transform)
test_data = datasets.CIFAR10(DATA_ROOT, train=False, download=True, transform=transform)
train_loader = DataLoader(train_data, batch_size=BATCH_SIZE, shuffle=True, num_workers=2)
test_loader = DataLoader(test_data, batch_size=BATCH_SIZE, shuffle=False, num_workers=2)

# ---------- 2. 模型: 预训练 ResNet18 + 替换分类头 ----------
model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)  # 下载预训练权重
print("[迁移] 已加载 ImageNet 预训练权重")

# 替换最后一层: 原模型输出 1000 类 (ImageNet), 改成你的类别数
in_features = model.fc.in_features            # 512
model.fc = nn.Linear(in_features, NUM_CLASSES)  # 新的分类头 (随机初始化)
model = model.to(DEVICE)

# ---------- 3. 两种微调策略 (选一种) ----------
STRATEGY = "finetune"  # "finetune": 全模型微调 | "head_only": 只训练分类头

if STRATEGY == "head_only":
    # 冻结特征层: 只训练新分类头 (数据少 / 想快速出结果时用)
    for param in model.parameters():
        param.requires_grad = False
    for param in model.fc.parameters():
        param.requires_grad = True
    print("[策略] 冻结特征层, 只训练分类头 (特征提取器模式)")
else:
    # 全模型微调: 通常给特征层更小学习率
    print("[策略] 全模型微调 (小学习率)")

optimizer = torch.optim.Adam(model.parameters(), lr=LR)

# ---------- 4. 训练 + 评估 (与 mnist/train.py 相同的循环) ----------
def train_one_epoch():
    model.train()
    total, correct, loss_sum = 0, 0, 0.0
    for images, labels in train_loader:
        images, labels = images.to(DEVICE), labels.to(DEVICE)
        optimizer.zero_grad()
        outputs = model(images)
        loss = F.cross_entropy(outputs, labels)
        loss.backward()
        optimizer.step()
        loss_sum += loss.item() * images.size(0)
        correct += (outputs.argmax(1) == labels).sum().item()
        total += images.size(0)
    return loss_sum / total, correct / total

def evaluate():
    model.eval()
    correct, total = 0, 0
    with torch.no_grad():
        for images, labels in test_loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            outputs = model(images)
            correct += (outputs.argmax(1) == labels).sum().item()
            total += labels.size(0)
    return correct / total

for epoch in range(1, EPOCHS + 1):
    loss, acc = train_one_epoch()
    test_acc = evaluate()
    print(f"Epoch {epoch}/{EPOCHS} | 损失 {loss:.4f} | 训练 {acc:.4f} | 测试 {test_acc:.4f}")

torch.save(model.state_dict(), os.path.join(MODELS_DIR, "resnet_transferred.pth"))
print(f"模型已保存: {os.path.join(MODELS_DIR, 'resnet_transferred.pth')}")

# ---------- 5. 之后: 导出 ONNX 部署 (复用 export_onnx.py 的思路) ----------
# dummy = torch.randn(1, 3, 224, 224)
# torch.onnx.export(model, dummy, "resnet_transferred.onnx", input_names=["image"], output_names=["logits"])
