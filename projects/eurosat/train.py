"""EuroSAT 遥感图像分类: 企业级迁移学习完整流程。

数据: torchgeo/eurosat (HuggingFace) — 10 类卫星影像, 64x64 RGB
流程: 数据整理 → 预训练 ResNet18 微调 → 评估 → 保存模型

训练策略 (企业标准做法):
  - 特征层 (ResNet 卷积)   : 小学习率 1e-4 (只微调, 不大动)
  - 新分类头 (fc)          : 大学习率 1e-3 (重点学习)
  - 数据增强 (遥感适用): 随机水平/垂直翻转 + 旋转 (卫星图方向任意)

用法: python train.py
"""
import json
import os
import random
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms
from PIL import Image

# ---------- 配置 (整理后: 数据集在仓库根 datasets/, 权重存本模块 models/) ----------
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, "..", ".."))
DATA_DIR = os.path.join(ROOT, "datasets", "eurosat")
MODELS_DIR = os.path.join(BASE, "models")
os.makedirs(MODELS_DIR, exist_ok=True)
IMG_ROOT = os.path.join(DATA_DIR, "2750")   # 解压后的类别目录根 (10 类)
TRAIN_PER_CLASS = 100    # 每类训练样本数 (CPU 友好; 全量是 ~1800/类)
VAL_PER_CLASS = 20       # 每类验证样本数
BATCH_SIZE = 32
EPOCHS = 3
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"使用设备: {DEVICE}")

# ---------- 1. 数据整理: 从官方划分文件构建子集 ----------
def read_list(path):
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]

# 官方划分文件格式: 每行 "类别名_编号.jpg" (类别从文件名前缀提取)
def group_by_class(paths):
    groups = {}
    for name in paths:
        cls = name.split("_")[0]
        groups.setdefault(cls, []).append(name)
    return groups

train_all = read_list(os.path.join(DATA_DIR, "eurosat-train.txt"))
val_all = read_list(os.path.join(DATA_DIR, "eurosat-val.txt"))
test_all = read_list(os.path.join(DATA_DIR, "eurosat-test.txt"))
print(f"官方划分: 训练 {len(train_all)} | 验证 {len(val_all)} | 测试 {len(test_all)}")

train_groups = group_by_class(train_all)
val_groups = group_by_class(val_all)
classes = sorted(train_groups.keys())
print(f"检测到 {len(classes)} 类: {classes}")

# 抽样子集
def sample(groups, per_class, seed=42):
    rng = random.Random(seed)
    out = []
    for cls in classes:
        out.extend(rng.sample(groups[cls], min(per_class, len(groups[cls]))))
    return out

train_sub = sample(train_groups, TRAIN_PER_CLASS)
val_sub = sample(val_groups, VAL_PER_CLASS)
print(f"子集: 训练 {len(train_sub)} 张 ({TRAIN_PER_CLASS}/类) | 验证 {len(val_sub)} 张 ({VAL_PER_CLASS}/类)")

# 构建镜像目录 (ImageFolder 直接可用)
sub_root = os.path.join(DATA_DIR, "subset")
for split, names in [("train", train_sub), ("val", val_sub)]:
    for cls in classes:
        os.makedirs(os.path.join(sub_root, split, cls), exist_ok=True)
    for name in names:
        cls = name.split("_")[0]
        shutil.copy(os.path.join(IMG_ROOT, cls, name), os.path.join(sub_root, split, cls, name))
print(f"子集镜像目录构建完成: {DATA_DIR}/subset/{{train,val}}/类别/图片.jpg")

# ---------- 2. 预处理: 预训练匹配 + 遥感数据增强 ----------
train_transform = transforms.Compose([
    transforms.Resize(224),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),          # 卫星图方向任意, 垂直翻转也合理
    transforms.RandomRotation(15),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])
val_transform = transforms.Compose([
    transforms.Resize(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

train_data = datasets.ImageFolder(os.path.join(sub_root, "train"), transform=train_transform)
val_data = datasets.ImageFolder(os.path.join(sub_root, "val"), transform=val_transform)
train_loader = DataLoader(train_data, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
val_loader = DataLoader(val_data, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

# 类别映射保存 (部署时使用)
with open(os.path.join(DATA_DIR, "class_names.json"), "w", encoding="utf-8") as f:
    json.dump(train_data.classes, f, ensure_ascii=False, indent=2)
print(f"类别映射已保存: {train_data.classes}")

# ---------- 3. 模型: ImageNet 预训练 ResNet18 + 新分类头 ----------
model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
in_features = model.fc.in_features
model.fc = nn.Linear(in_features, len(classes))
model = model.to(DEVICE)
print("[迁移] ResNet18 ImageNet 预训练权重加载, 分类头替换为", len(classes), "类")

# ---------- 4. 分组学习率 (企业标准: 特征层小步, 分类头大步) ----------
feature_params = [p for n, p in model.named_parameters() if not n.startswith("fc.")]
head_params = [p for n, p in model.named_parameters() if n.startswith("fc.")]
optimizer = torch.optim.Adam([
    {"params": feature_params, "lr": 1e-4},
    {"params": head_params, "lr": 1e-3},
])


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


def evaluate(loader):
    model.eval()
    correct, total = 0, 0
    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            outputs = model(images)
            correct += (outputs.argmax(1) == labels).sum().item()
            total += labels.size(0)
    return correct / total


# ---------- 5. 训练 ----------
best_acc = 0.0
for epoch in range(1, EPOCHS + 1):
    loss, acc = train_one_epoch()
    val_acc = evaluate(val_loader)
    print(f"Epoch {epoch}/{EPOCHS} | 损失 {loss:.4f} | 训练 {acc:.4f} | 验证 {val_acc:.4f}")
    if val_acc > best_acc:
        best_acc = val_acc
        torch.save(model.state_dict(), os.path.join(MODELS_DIR, "eurosat_resnet18.pth"))
        print(f"  ✅ 保存最佳模型 (验证准确率 {val_acc:.4f})")

print(f"\n最佳验证准确率: {best_acc:.4f}")
print(f"模型已保存: {os.path.join(MODELS_DIR, 'eurosat_resnet18.pth')}")
