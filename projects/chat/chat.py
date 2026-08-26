"""对话引擎: 多轮历史 + 流式生成。

核心类 ChatEngine:
    engine = ChatEngine(system="你是...")     # 可选系统提示词
    for chunk in engine.stream_chat("你好"):   # 流式吐出回复片段
        print(chunk, end="")
    engine.reset()                             # 清空对话历史

实现要点:
- 对话历史保存在 messages 列表里，持续对话 = 每轮都带上完整上下文
- 用 apply_chat_template 构造 Qwen 官方聊天格式（不用手写格式）
- 流式: 生成放在子线程 + TextIteratorStreamer，主线程边收边吐
"""
import threading

from transformers import TextIteratorStreamer

from model import get_model


class ChatEngine:
    def __init__(self, system: str = "你是Qwen，一个乐于助人的中文AI助手。", **gen_kwargs):
        self.system = system
        self.gen_kwargs = {
            "max_new_tokens": 512,      # 单次回复最长 token 数
            "temperature": 0.7,         # 随机性（0 偏保守，越大越发散）
            "top_p": 0.9,
            "repetition_penalty": 1.05,  # 抑制重复
            **gen_kwargs,
        }
        self.messages = []
        self.reset()

    def reset(self):
        """清空历史，回到初始系统提示词状态。"""
        self.messages = [{"role": "system", "content": self.system}]

    def _build_inputs(self, tokenizer, text: str):
        """当前历史 + 新提问 → 模型输入。"""
        self.messages.append({"role": "user", "content": text})
        prompt = tokenizer.apply_chat_template(
            self.messages, tokenize=False, add_generation_prompt=True
        )
        return tokenizer(prompt, return_tensors="pt")

    def stream_chat(self, text: str):
        """向模型提问并流式返回回复片段（生成器）。

        完整回复结束后会自动存入历史（作为 assistant 消息），
        因此下一轮提问时模型能看到之前的所有对话。
        """
        model, tokenizer = get_model()
        inputs = self._build_inputs(tokenizer, text)

        streamer = TextIteratorStreamer(
            tokenizer, skip_prompt=True, skip_special_tokens=True, timeout=600.0
        )
        gen_kwargs = dict(self.gen_kwargs)
        gen_kwargs.update(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            streamer=streamer,
        )
        thread = threading.Thread(target=model.generate, kwargs=gen_kwargs)
        thread.start()

        parts = []
        for chunk in streamer:
            parts.append(chunk)
            yield chunk
        thread.join()

        # 把完整回复记入历史，维持多轮上下文
        self.messages.append({"role": "assistant", "content": "".join(parts)})

    def chat(self, text: str) -> str:
        """非流式版本: 直接返回完整回复（测试脚本用）。"""
        return "".join(self.stream_chat(text))
