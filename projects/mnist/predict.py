"""使用训练好的模型做推理(预测)。

用法:
  python predict.py                  # 从测试集随机抽 10 张图, 展示预测效果
  python predict.py 图片路径.png     # 预测你自己的 28x28 手写数字图片

运行前提: 已有训练好的权重文件 mnist_cnn.pth (由 train.py 生成)。
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import torch
import torch.nn.functional as F
from torchvision import datasets, transforms

from model import CNN   # 模型结构唯一来源: model.py (与训练共用同一份)

# ---------- 路径 (数据集在仓库根 datasets/, 权重在本模块 models/) ----------
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, "..", ".."))
DATA_ROOT = os.path.join(ROOT, "datasets", "mnist")
MODELS_DIR = os.path.join(BASE, "models")
# 模型学的是"归一化后的图", 输入前要做同样的变换
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.1307,), (0.3081,)),
])


def ascii_digit(arr):
    """28x28 灰度图 -> 终端字符画 (0~255 -> 10 级灰度字符)。"""
    chars = " .:-=+*#%@"
    return "\n".join(
        "".join(chars[min(int(v / 25.6), 9)] for v in row) for row in arr
    )


def predict(images, model):
    """输入 (N,1,28,28) 张量 -> 返回 (预测类别, 置信度)。"""
    model.eval()                          # 评估模式
    with torch.no_grad():                 # 推理不需要梯度, 省内存加速
        outputs = model(images)                       # (N,10) 各类得分
        probs = F.softmax(outputs, dim=1)             # 得分 -> 概率 (10个加起来=1)
        preds = outputs.argmax(1)                     # 得分最高的类
        confs = probs.gather(1, preds.view(-1, 1)).squeeze()
    return preds, confs


def load_user_image(path):
    """加载用户自绘图片 -> (1,1,28,28) 张量。

    专业预处理 4 步, 把任意图片变成 MNIST 风格的样本:
      ① 透明通道合成到白底 (RGBA -> RGB)
      ② 反色: 保证白字黑底, 与训练数据方向一致
      ③ 裁剪到笔迹边界框 (去掉多余空白)
      ④ 缩放 + 居中到 28x28 (MNIST 官方做法: 内容放 20x20 居中)
    """
    from PIL import Image

    img = Image.open(path)

    # ① 处理透明通道: 有 alpha 的图先合成到白色背景
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])         # alpha 作蒙版, 透明处露出白底
        img = bg
    gray = img.convert("L")
    arr = np.array(gray, dtype=np.float32)

    # ② 反色: 背景偏亮(白底深字) -> 翻成黑底白字, 与 MNIST 一致
    if arr.mean() > 128:
        arr = 255 - arr

    # ③ 裁剪到笔迹边界框 (留 4 像素边距)
    content = arr > 100
    rows = np.where(content.any(axis=1))[0]
    cols = np.where(content.any(axis=0))[0]
    if len(rows) and len(cols):
        r0, r1 = max(rows.min() - 4, 0), min(rows.max() + 5, arr.shape[0])
        c0, c1 = max(cols.min() - 4, 0), min(cols.max() + 5, arr.shape[1])
        arr = arr[r0:r1, c0:c1]
        print(f"  裁剪到笔迹区域: {arr.shape[0]}x{arr.shape[1]} (去掉多余空白)")

    # ③.5 加粗细笔画 (用户手绘通常比 MNIST 细, 用 3x3 膨胀补粗)
    from PIL import ImageFilter
    arr_img = Image.fromarray(arr.astype(np.uint8))
    arr_img = arr_img.filter(ImageFilter.MaxFilter(3))   # 3x3 膨胀: 亮像素向外扩 1 像素
    arr_img = arr_img.filter(ImageFilter.MaxFilter(3))   # 再来一次, 达到接近 MNIST 的粗细
    arr = np.array(arr_img, dtype=np.float32)

    # ④ 长边缩放到 20px, 居中放到 28x28 画布 (MNIST 官方预处理)
    h, w = arr.shape
    scale = 20 / max(h, w)
    nh, nw = max(round(h * scale), 1), max(round(w * scale), 1)
    small = Image.fromarray(arr.astype(np.uint8)).resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("L", (28, 28), 0)
    canvas.paste(small, ((28 - nw) // 2, (28 - nh) // 2))
    final = np.array(canvas, dtype=np.float32)

    print("  处理后的图 (黑底白字, 与训练样本同风格):")
    print(ascii_digit(final))

    tensor = transform(Image.fromarray(final.astype(np.uint8))).unsqueeze(0)
    return tensor


def main():
    model = CNN()
    model.load_state_dict(torch.load(os.path.join(MODELS_DIR, "mnist_cnn.pth"), map_location="cpu"))
    print(f"✅ 模型加载成功: {os.path.join(MODELS_DIR, 'mnist_cnn.pth')} (参数来自训练, 结构由本脚本搭建)\n")

    # ---------- 模式 2: 预测你自己的图片 ----------
    if len(sys.argv) > 1:
        print(f"加载图片: {sys.argv[1]}")
        tensor = load_user_image(sys.argv[1])
        pred, conf = predict(tensor, model)
        print(f"\n图片 {sys.argv[1]} 预测为: {pred.item()}  (置信度 {conf.item():.2%})")
        return

    # ---------- 模式 1: 从测试集随机抽 10 张演示 ----------
    test_data = datasets.MNIST(DATA_ROOT, train=False, download=False)  # 不预处理, 拿原始 PIL 图
    indices = torch.randperm(len(test_data))[:10]
    correct = 0
    for i in indices:
        img_pil, true_label = test_data[i]            # PIL 图 + 真实标签
        arr = np.array(img_pil)                       # (28,28) 0~255
        tensor = transform(img_pil).unsqueeze(0)      # 预处理后喂模型
        pred, conf = predict(tensor, model)
        ok = pred.item() == true_label
        correct += ok
        print(ascii_digit(arr))
        print(f"真实标签: {true_label} | 模型预测: {pred.item()} | 置信度: {conf.item():.2%} {'✅' if ok else '❌'}")
        print("-" * 46)

    print(f"\n10 张随机测试图, 猜对 {correct} 张")


if __name__ == "__main__":
    main()
