"""MNIST 手写数字识别入门示例：CNN 训练 + 评估。

运行: python train.py
首次运行会自动下载 MNIST 数据集（约 10MB）到 datasets/mnist。
"""
import os
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

from model import CNN   # 模型结构唯一来源: model.py

# ---------- 路径 (整理后: 数据集在仓库根 datasets/, 权重存本模块 models/) ----------
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, "..", ".."))
DATA_ROOT = os.path.join(ROOT, "datasets", "mnist")
MODELS_DIR = os.path.join(BASE, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# ---------- 1. 超参数 ----------
BATCH_SIZE = 64
EPOCHS = 5
LR = 1e-3
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"使用设备: {DEVICE}")

# ---------- 2. 数据 ----------
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.1307,), (0.3081,)),
])
train_data = datasets.MNIST(DATA_ROOT, train=True, download=True, transform=transform)
test_data = datasets.MNIST(DATA_ROOT, train=False, download=True, transform=transform)
train_loader = DataLoader(train_data, batch_size=BATCH_SIZE, shuffle=True)
test_loader = DataLoader(test_data, batch_size=BATCH_SIZE, shuffle=False)

# ---------- 3. 模型：见 model.py (CNN) ----------
model = CNN().to(DEVICE)
optimizer = torch.optim.Adam(model.parameters(), lr=LR)

# ---------- 4. 训练循环 ----------
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
    print(f"Epoch {epoch}/{EPOCHS} | 训练损失 {loss:.4f} | 训练准确率 {acc:.4f} | 测试准确率 {test_acc:.4f}")

# ---------- 5. 保存模型 ----------
torch.save(model.state_dict(), os.path.join(MODELS_DIR, "mnist_cnn.pth"))
print(f"模型已保存: {os.path.join(MODELS_DIR, 'mnist_cnn.pth')}")
