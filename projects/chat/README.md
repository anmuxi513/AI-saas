# 💬 语言对话模块（Qwen2.5-0.5B）

本地运行的**持续对话**模型模块，与 mnist / fashion / eurosat 并列，
遵循工作区「一个模型一个项目模块」的约定。

## 文件

| 文件 | 说明 |
|---|---|
| `model.py` | 模型/分词器加载唯一入口（懒加载单例，权重缓存到 `models/`） |
| `chat.py` | 对话引擎：多轮历史、流式生成、系统提示词、生成参数 |
| `app.py` | **Gradio 持续对话界面**（流式输出），浏览器打开 http://127.0.0.1:7860 |
| `test_chat.py` | 命令行冒烟测试（不开界面，验证对话链路与速度） |
| `models/` | 模型权重缓存（HuggingFace 下载，约 1GB，已 gitignore） |

## 快速开始

```bash
pip install transformers gradio

# 方式一：命令行冒烟测试（先验证环境）
python projects/chat/test_chat.py "你好，介绍一下你自己"

# 方式二：图形界面（持续对话）
python projects/chat/app.py
#   浏览器自动打开 http://127.0.0.1:7860
```

> 国内网络下载慢/失败时，先设置镜像再运行（首次下载约 1GB）：
> - PowerShell: `$env:HF_ENDPOINT = "https://hf-mirror.com"`
> - 之后可正常运行，缓存已在本机 `models/`

## 设计说明

- **多轮上下文**：每轮提问都携带完整对话历史（`chat.py` 内部维护 messages），
  模型记得之前聊过什么；界面「清空对话」按钮会重置历史。
- **流式输出**：生成放在子线程 + `TextIteratorStreamer`，一个字一个字返回，
  不需要等整段生成完。
- **系统提示词**：界面「⚙️ 系统提示词」可自定义角色设定，修改后点「应用并重置」。
- **性能**：0.5B 模型在普通 CPU 上约 10~20 字/秒，适合日常对话；
  想要更强效果可换 `Qwen/Qwen2.5-1.5B-Instruct`（速度约慢 3 倍）。

## 为什么语言模型不做 ONNX 导出？

mnist / eurosat 都导出了 ONNX（结构+权重一体、免 PyTorch 推理），
但**语言模型不适合**这条路：

1. 输入输出是**不定长 token 序列**，ONNX 需要动态轴 + 固定最大长度，导出繁琐；
2. 生成过程依赖 **KV Cache**（每步增长），标准 ONNX 格式难以高效表达；
3. 0.5B 模型本身只有 ~1GB，直接分发 transformers 方案（pip 安装 + 缓存目录复制）
   与分发 ONNX 的复杂度相当，但质量与生态（量化、长上下文）更好。

结论：语言模型以「HuggingFace 权重 + transformers 推理」为交付形态，
模型目录 `models/` 可直接整目录复制给同架构机器使用。

## 进阶（可选项，本次未实现）

- **CPU 微调**：0.5B 用 QLoRA 可在 CPU 上微调（数小时级），
  脚本可参考 `projects/fashion/resnet_transfer_template.py` 的「模板」思路。
- **换更强模型**：改 `model.py` 顶部的 `MODEL_NAME` 一行即可切换
  （如 `Qwen/Qwen2.5-1.5B-Instruct`、`Qwen/Qwen3-1.7B-Instruct`）。
