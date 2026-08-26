"""迁移学习实战: 把 MNIST 训练好的模型, 迁移到 FashionMNIST 衣物分类。

对比实验 (同一 CNN 结构, 唯一区别是初始权重从哪来):
  A. 从零训练: 随机初始化权重 → 在 FashionMNIST 上训练
  B. 迁移学习: 加载 mnist_cnn.pth 的卷积特征层 → 重置分类头 → 微调

预期结果:
  - B 收敛更快 (第 1 个 epoch 准确率就明显高于 A)
  - 相同 epoch 数下 B 的最终准确率更高
  - 因为 MNIST 学到的"边缘/笔画/形状"特征, 对衣物图片同样有效

运行: python transfer_learning.py
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

# ---------- 路径 (整理后: 各模块独立, 数据集统一在仓库根 datasets/) ----------
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, "..", ".."))
FASHION_ROOT = os.path.join(ROOT, "datasets", "fashion")
MNIST_WEIGHTS = os.path.join(ROOT, "projects", "mnist", "models", "mnist_cnn.pth")
MODELS_DIR = os.path.join(BASE, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# 复用 MNIST 模块的模型结构 (model.py 在 projects/mnist/, 跨模块复用)
sys.path.insert(0, os.path.join(ROOT, "projects", "mnist"))
from model import CNN  # 复用同一模型结构 (model.py)

# ---------- 超参数 ----------
BATCH_SIZE = 64
EPOCHS = 3
LR = 1e-3
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"使用设备: {DEVICE}")

# ---------- 数据: FashionMNIST (10 类衣物, 与 MNIST 同为 28x28 灰度) ----------
FASHION_CLASSES = ["T恤", "裤子", "套头衫", "连衣裙", "外套", "凉鞋", "衬衫", "运动鞋", "包", "靴子"]
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.1307,), (0.3081,)),
])
train_data = datasets.FashionMNIST(FASHION_ROOT, train=True, download=True, transform=transform)
test_data = datasets.FashionMNIST(FASHION_ROOT, train=False, download=True, transform=transform)
train_loader = DataLoader(train_data, batch_size=BATCH_SIZE, shuffle=True)
test_loader = DataLoader(test_data, batch_size=BATCH_SIZE, shuffle=False)
print(f"FashionMNIST: 训练 {len(train_data)} 张, 测试 {len(test_data)} 张")


def train_one_epoch(model, optimizer):
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


def evaluate(model):
    model.eval()
    correct, total = 0, 0
    with torch.no_grad():
        for images, labels in test_loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            outputs = model(images)
            correct += (outputs.argmax(1) == labels).sum().item()
            total += labels.size(0)
    return correct / total


def run_experiment(name, model):
    print(f"\n=== {name} ===")
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    for epoch in range(1, EPOCHS + 1):
        loss, acc = train_one_epoch(model, optimizer)
        test_acc = evaluate(model)
        print(f"Epoch {epoch}/{EPOCHS} | 训练损失 {loss:.4f} | 训练准确率 {acc:.4f} | 测试准确率 {test_acc:.4f}")


# ---------- A. 从零训练 (对照组: 随机初始化) ----------
model_a = CNN().to(DEVICE)
run_experiment("A. 从零训练 (随机初始化)", model_a)

# ---------- B. 迁移学习 (实验组: 加载 MNIST 权重) ----------
model_b = CNN().to(DEVICE)
pretrained = torch.load(MNIST_WEIGHTS, map_location="cpu")

# 迁移策略: 卷积层 + fc1 (特征提取器) 继承 MNIST 学到的特征;
# fc2 (分类头) 重置, 因为两个任务的"10 个类别"含义不同
state = model_b.state_dict()
for key, value in pretrained.items():
    if key.startswith("fc2"):
        print(f"[迁移] 跳过分类头 {key} (重置, 任务类别不同)")
        continue
    state[key] = value
model_b.load_state_dict(state)
print("[迁移] 特征层已加载 MNIST 权重 (conv1/conv2/fc1)")

run_experiment("B. 迁移学习 (MNIST 特征 + 新分类头)", model_b)

# ---------- 最终对比 ----------
print("\n=== 最终对比 (FashionMNIST 测试集) ===")
acc_a = evaluate(model_a)
acc_b = evaluate(model_b)
print(f"A. 从零训练   : 测试准确率 {acc_a:.4f}")
print(f"B. 迁移学习   : 测试准确率 {acc_b:.4f}")
print(f"迁移学习提升  : {acc_b - acc_a:+.4f}")

torch.save(model_b.state_dict(), os.path.join(MODELS_DIR, "fashion_cnn_transferred.pth"))
print(f"\n已保存迁移学习模型: {os.path.join(MODELS_DIR, 'fashion_cnn_transferred.pth')}")
