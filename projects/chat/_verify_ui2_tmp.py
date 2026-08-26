"""临时验证: ChatGPT 风格界面端到端测试（验证后删除）。"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
from gradio_client import Client

c = Client("http://127.0.0.1:7860/")
print("=== 1. 新建会话 ===")
r = c.predict(api_name="/new_chat")
print("输出数:", len(r), "| 欢迎屏可见:", r[0]["visible"] if isinstance(r[0], dict) else r[0])

print("\n=== 2. 第一轮对话（流式接口）===")
r1 = c.predict("帮我写一首关于春天的短诗", api_name="/respond")
chat1 = r1[-1]
print("消息数:", len(chat1))
print("用户消息:", chat1[0]["content"])
print("助手回复前 60 字:", chat1[1]["content"][:60])

print("\n=== 3. 第二轮对话（同一会话，验证上下文）===")
r2 = c.predict("把刚才那首诗改成五言绝句", api_name="/respond")
chat2 = r2[-1]
print("消息数:", len(chat2), "| 第二轮回复前 50 字:", chat2[-1]["content"][:50])

print("\n=== 4. 新建会话（验证多会话隔离）===")
r3 = c.predict(api_name="/new_chat")
print("输出数:", len(r3), "| 新会话聊天区:", r3[2])
print("✅ 界面端到端验证完成")
