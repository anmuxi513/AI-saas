"""企业级体验: ImageNet 预训练 ResNet18 对真实图片做 1000 类分类推理。

这是"企业级迁移学习"的起点体验:
  1. 自动下载 ImageNet (1400万张图) 预训练权重 (约 45MB, download.pytorch.org)
  2. 对任意真实图片做 1000 类分类 (top-5)
  3. 同一个模型, 不训练一行参数, 直接推理

用法:
  python imagenet_inference.py                     # 自动测试内置的真实图片
  python imagenet_inference.py 图片路径            # 测试你自己的图片
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

import torch
import torch.nn.functional as F
from torchvision import models
from PIL import Image

# ---------- 路径 (数据集在仓库根 datasets/) ----------
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, "..", ".."))
FASHION_ROOT = os.path.join(ROOT, "datasets", "fashion")

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"使用设备: {DEVICE}")

# ---------- 1. 加载 ImageNet 预训练权重 (含 1000 类标签, 无需额外文件) ----------
print("正在下载/加载 ImageNet 预训练 ResNet18 (约 45MB)...")
weights = models.ResNet18_Weights.IMAGENET1K_V1
model = models.resnet18(weights=weights).to(DEVICE)
model.eval()
categories = weights.meta["categories"]  # 1000 个类别英文名
print(f"✅ 模型就绪: 1000 类 | 示例: {categories[0]} / {categories[281]} / {categories[888]}")

# 官方推荐的预处理 (Resize 256 → CenterCrop 224 → ImageNet 归一化)
preprocess = weights.transforms()


def predict(path, topk=5):
    img = Image.open(path).convert("RGB")
    tensor = preprocess(img).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        logits = model(tensor)
        probs = F.softmax(logits, dim=1)
    top = probs.topk(topk)
    print(f"\n🖼 图片: {path}  原始尺寸 {img.size}")
    for i in range(topk):
        idx = top.indices[0, i].item()
        print(f"   #{i + 1}  {categories[idx]:45s} {top.values[0, i].item():.2%}")
    return top.indices[0, 0].item()


# ---------- 2. 推理: 内置真实图片 + 命令行参数图片 ----------
images = [
    r"C:\Windows\Web\Wallpaper\Windows\img0.jpg",     # Windows 自带壁纸 (真实风景照)
    r"C:\Windows\Web\Wallpaper\Windows\img19.jpg",
    r"C:\Users\cc\Downloads\AI实操2_files\1688107277Z3NJ7Y.png",  # 用户下载的长图
]
if len(sys.argv) > 1:
    images.append(sys.argv[1])

for p in images:
    try:
        predict(p)
    except FileNotFoundError:
        print(f"\n⚠️ 找不到图片: {p}")

# ---------- 3. 附加: 用 FashionMNIST 真实衣物图测试 (分布外输入) ----------
print("\n--- 附加实验: FashionMNIST 衣物图 (模型没见过的低分辨率输入) ---")
from torchvision import datasets
test_data = datasets.FashionMNIST(FASHION_ROOT, train=False, download=False)
img_pil, label = test_data[0]  # 第 1 张: 通常是 T 恤/套头衫
label_names = ["T恤", "裤子", "套头衫", "连衣裙", "外套", "凉鞋", "衬衫", "运动鞋", "包", "靴子"]
big = img_pil.resize((224, 224), Image.LANCZOS).convert("RGB")
tensor = preprocess(big).unsqueeze(0).to(DEVICE)
with torch.no_grad():
    probs = F.softmax(model(tensor), dim=1)
top = probs.topk(3)
print(f"真实类别: {label_names[label]} (索引 {label})")
for i in range(3):
    idx = top.indices[0, i].item()
    print(f"   #{i + 1}  {categories[idx]:45s} {top.values[0, i].item():.2%}")
