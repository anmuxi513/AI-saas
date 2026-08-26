"""诊断你自己的图片: 模型到底看到了什么? 为什么预测和你想的不一样?

用法: python inspect_image.py 图片路径
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
from PIL import Image


def ascii_digit(arr):
    """28x28 灰度图 -> 终端字符画 (0~255 -> 10 级灰度字符)。"""
    chars = " .:-=+*#%@"
    return "\n".join(
        "".join(chars[min(int(v / 25.6), 9)] for v in row) for row in arr
    )


def analyze(path):
    img = Image.open(path)
    print(f"原始图片: {path}")
    print(f"  尺寸      : {img.size} (宽 x 高)")
    print(f"  颜色模式  : {img.mode} (L=灰度, RGB=彩色)")
    print(f"  文件格式  : {img.format}")

    gray = img.convert("L")
    arr = np.array(gray, dtype=np.float32)

    # ---------- 关键诊断 1: 颜色方向 ----------
    dark = (arr < 128).mean()
    light = (arr >= 128).mean()
    print(f"\n[诊断1] 颜色分布: 暗像素 {dark:.1%}, 亮像素 {light:.1%}")
    if dark < 0.5:
        print("  → 你的图是【白底 + 深色笔迹】")
        print("  → MNIST 训练样本是【黑底 + 白色笔迹】= 正好相反!")
        print("  → 模型看到的等于你图片的'负片', 这是最可能认错的原因")
    else:
        print("  → 你的图是【黑底 + 浅色笔迹】, 方向与 MNIST 一致 ✅")

    # ---------- 关键诊断 2: 缩放变形 ----------
    w, h = img.size
    print(f"\n[诊断2] 宽高比: {w / h:.2f} (MNIST 样本是正方形 1.00)")
    if abs(w / h - 1) > 0.2:
        print("  → 非正方形! 被拉伸成 28x28 后数字会变形")

    # ---------- 关键诊断 3: 内容占比 ----------
    if dark < 0.5:
        content = arr < 128          # 笔迹=暗像素
    else:
        content = arr > 128          # 笔迹=亮像素
    ratio = content.mean()
    print(f"\n[诊断3] 笔迹占画面比例: {ratio:.1%} (MNIST 样本约 10%~25%)")
    if ratio < 0.05:
        print("  → 笔迹太细/太小, resize 后可能模糊成一团")
    if ratio > 0.4:
        print("  → 笔画太粗/太大, 可能占满整图")

    # ---------- 关键诊断 4: 居中情况 ----------
    rows = np.where(content.any(axis=1))[0]
    cols = np.where(content.any(axis=0))[0]
    if len(rows) and len(cols):
        cy, cx = (rows.min() + rows.max()) / 2 / h, (cols.min() + cols.max()) / 2 / w
        print(f"\n[诊断4] 数字中心: 水平 {cx:.2f}, 垂直 {cy:.2f} (理想是 0.5, 0.5)")
        if abs(cx - 0.5) > 0.15 or abs(cy - 0.5) > 0.15:
            print("  → 数字明显偏斜/不居中 (MNIST 样本都居中)")

    # ---------- 模型眼中的图 (两种方向都展示) ----------
    resized = gray.resize((28, 28), Image.LANCZOS)
    a = np.array(resized, dtype=np.float32)
    print("\n[模型看到的输入, 保持你的颜色方向]:")
    print(ascii_digit(a))
    print("\n[MNIST 方向 (反色后, 白字黑底)]:")
    print(ascii_digit(255 - a))


if __name__ == "__main__":
    analyze(sys.argv[1])
