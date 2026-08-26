"""解析 MNIST raw 原始文件,看看数据到底是怎么存的。

datasets/mnist/MNIST/raw/ 下的 .ubyte 是 IDX 二进制格式:
  images: [魔数 4字节][图片数 4字节][行数 4字节][列数 4字节][像素...]
  labels: [魔数 4字节][标签数 4字节][标签...]

运行: python parse_raw.py
"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np


def read_idx_images(path, count=5):
    with open(path, "rb") as f:
        magic = struct.unpack(">I", f.read(4))[0]      # 大端 4 字节魔数
        n, rows, cols = struct.unpack(">III", f.read(12))
        print(f"  魔数      : {magic} (2051 = 图片集)")
        print(f"  图片数量  : {n}")
        print(f"  每张尺寸  : {rows} x {cols}")
        print(f"  像素总量  : {n * rows * cols} 字节 (每像素 1 字节, 0~255 灰度)")
        data = np.frombuffer(f.read(), dtype=np.uint8).reshape(n, rows, cols)
    return data[:count]


def read_idx_labels(path, count=5):
    with open(path, "rb") as f:
        magic = struct.unpack(">I", f.read(4))[0]      # 大端 4 字节魔数
        n = struct.unpack(">I", f.read(4))[0]
        print(f"  魔数      : {magic} (2049 = 标签集)")
        print(f"  标签数量  : {n} (每个 1 字节, 值 0~9)")
        data = np.frombuffer(f.read(), dtype=np.uint8)
    return data[:count]


def ascii_digit(arr):
    """把 28x28 灰度图转成终端字符画 (0~255 -> 10 级灰度字符)。"""
    chars = " .:-=+*#%@"
    return "\n".join(
        "".join(chars[min(int(v / 25.6), 9)] for v in row) for row in arr
    )


BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, ".."))
raw_dir = os.path.join(ROOT, "datasets", "mnist", "MNIST", "raw")
print("=== 解析训练集图片文件 ===")
images = read_idx_images(f"{raw_dir}/train-images-idx3-ubyte")
print("\n=== 解析训练集标签文件 ===")
labels = read_idx_labels(f"{raw_dir}/train-labels-idx1-ubyte")

print(f"\n=== raw 文件里真实保存的前 {len(images)} 张图 ===")
for i in range(len(images)):
    print(f"--- 第 {i + 1} 张 | 对应标签 = {labels[i]} ---")
    print(ascii_digit(images[i]))
    print()

print("结论: 图片存像素值, 标签存数字, 靠位置一一对应 (第N张图 <-> 第N个标签)")
