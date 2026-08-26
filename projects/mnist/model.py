"""模型结构定义 (唯一一份, 训练和推理共用)。

这是"模型长什么样"的唯一权威来源:
  - train.py 训练时从这里 import CNN
  - predict.py 推理时也从这里 import CNN
  - 分享给别人时, 这个文件 + 权重文件 = 完整模型

用法: from model import CNN
"""
import torch.nn as nn
import torch.nn.functional as F


class CNN(nn.Module):
    """两层卷积 + 全连接, MNIST 手写数字识别 (28x28 灰度图 -> 10 类)。"""

    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, padding=1)   # 提取低级特征
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)  # 提取高级特征
        self.fc1 = nn.Linear(64 * 7 * 7, 128)                     # 组合特征
        self.fc2 = nn.Linear(128, 10)                             # 输出 10 个数字得分

    def forward(self, x):
        x = F.relu(F.max_pool2d(self.conv1(x), 2))   # 28x28 -> 14x14
        x = F.relu(F.max_pool2d(self.conv2(x), 2))   # 14x14 -> 7x7
        x = x.view(x.size(0), -1)                    # 展平 (N, 64*7*7)
        x = F.relu(self.fc1(x))
        return self.fc2(x)                            # (N, 10) 各类得分
