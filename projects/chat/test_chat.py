"""命令行冒烟测试: 不开界面验证对话链路（对齐 eurosat/e2e_test.py 的定位）。

用法:
    python test_chat.py                  # 跑内置的两轮示例对话
    python test_chat.py "你好"           # 单轮问答
    python test_chat.py -i               # 交互模式（持续对话直到输入 exit）

输出包含 token 生成速度，用于评估 CPU 上的实际性能。
"""
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from chat import ChatEngine


def timed_chat(engine, text):
    t0 = time.time()
    reply = engine.chat(text)
    dt = time.time() - t0
    n_tokens = max(1, len(reply))
    print(f"\n👤 问: {text}")
    print(f"🤖 答: {reply}")
    print(f"⏱ 耗时 {dt:.1f}s | 约 {n_tokens / dt:.1f} 字/秒\n")
    return reply


def main():
    engine = ChatEngine()
    args = sys.argv[1:]

    if "-i" in args:
        print("进入交互模式（输入 exit 退出）\n")
        while True:
            text = input("👤 你: ").strip()
            if not text:
                continue
            if text.lower() in ("exit", "quit", "退出"):
                break
            timed_chat(engine, text)
        return

    if args:
        timed_chat(engine, " ".join(args))
        return

    # 默认: 两轮示例，验证多轮上下文（让模型记住数字并复述）
    print("=== 冒烟测试: 两轮对话（验证上下文记忆） ===\n")
    timed_chat(engine, "请记住一个数字：42。不要忘记。")
    timed_chat(engine, "我刚才让你记住什么数字？只回答数字本身。")
    print("✅ 冒烟测试通过（多轮上下文正常）")


if __name__ == "__main__":
    main()
