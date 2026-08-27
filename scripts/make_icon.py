"""生成应用图标 app.ico（多尺寸，贴合系统 UI 风格）。

设计: 深蓝渐变圆角方块（#1E40AF → #2563EB，对角渐变）
      + 白色三竖线（AI 芯片意象，与前端 logo/favicon 一致）

用法:
    python scripts/make_icon.py        # 生成 assets/app.ico
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "assets", "app.ico")

SIZE = 256
RADIUS = 58          # 圆角半径
C1 = (30, 64, 175)   # #1E40AF 主色
C2 = (37, 99, 235)   # #2563EB 亮蓝
WHITE = (255, 255, 255, 255)


def make_icon() -> Image.Image:
    # ---- 对角渐变背景 ----
    xx, yy = np.meshgrid(np.arange(SIZE), np.arange(SIZE))
    t = (xx + yy) / (2 * (SIZE - 1))
    t = np.clip(t, 0, 1)[..., None]
    c1 = np.array(C1, dtype=float)
    c2 = np.array(C2, dtype=float)
    rgb = (c1 + (c2 - c1) * t).astype(np.uint8)
    grad = Image.fromarray(rgb, "RGB")

    # ---- 白色三竖线（AI 芯片）----
    d = ImageDraw.Draw(grad)
    bar_w = 22
    for cx in (96, 128, 160):
        d.rounded_rectangle(
            [cx - bar_w // 2, 64, cx + bar_w // 2, 192],
            radius=bar_w // 2, fill=WHITE,
        )

    # ---- 圆角遮罩 ----
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1],
                                           radius=RADIUS, fill=255)

    icon = grad.convert("RGBA")
    icon.putalpha(mask)
    return icon


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    icon = make_icon()
    # 多尺寸写入 .ico（16/24/32/48/64/128/256）
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon.save(OUT, format="ICO", sizes=sizes)
    print(f"✅ 图标已生成: {OUT}")
    print(f"   尺寸: {sizes}")

    # 同时输出 PNG（供 README / 前端 favicon 使用）
    png_out = os.path.join(ROOT, "assets", "app-icon.png")
    icon.save(png_out, format="PNG")
    print(f"   PNG: {png_out}")


if __name__ == "__main__":
    main()
