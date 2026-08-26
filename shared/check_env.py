"""环境检查：PyTorch 版本、CUDA / GPU 可用性。"""
import sys

import torch

print(f"Python      : {sys.version.split()[0]}")
print(f"PyTorch     : {torch.__version__}")
print(f"CUDA 可用   : {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA 版本   : {torch.version.cuda}")
    print(f"GPU 数量    : {torch.cuda.device_count()}")
    for i in range(torch.cuda.device_count()):
        print(f"  GPU[{i}] : {torch.cuda.get_device_name(i)}")
        print(f"          显存 {torch.cuda.get_device_properties(i).total_memory / 1024**3:.1f} GB")
else:
    print("提示: 未检测到 GPU，将使用 CPU 训练（较慢）。")
    print("      如需 GPU 加速，请到 https://pytorch.org/get-started/locally/ 安装对应版本。")

# 张量与自动求导冒烟测试
x = torch.randn(2, 3, requires_grad=True)
y = (x * x).sum()
y.backward()
print(f"\n冒烟测试通过: x.grad 形状 = {tuple(x.grad.shape)}")
