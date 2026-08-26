"""临时验证: ChatGPT 风格界面端到端测试（验证后删除）。"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
from gradio_client import Client

c = Client("http://127.0.0.1:7860/")


def text_of(msg):
    """gradio 6 消息 content 可能是 list[dict] 或 str。"""
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list) and content:
        return "".join(x.get("text", "") for x in content if isinstance(x, dict))
    return str(content)


print("=== 1. 新建会话 ===")
r = c.predict(api_name="/new_chat")
print("输出数:", len(r))
welcome_vis = r[0]
print("欢迎屏可见:", welcome_vis["visible"] if isinstance(welcome_vis, dict) else welcome_vis)
print("顶栏 HTML 前 40 字:", str(r[1])[:40])

print("\n=== 2. 第一轮对话 ===")
r1 = c.predict("帮我写一首关于春天的短诗", api_name="/send")
chat1 = r1[-1]
print("消息数:", len(chat1))
print("用户:", text_of(chat1[0]))
print("助手:", text_of(chat1[1])[:60], "...")

print("\n=== 3. 第二轮（同会话上下文）===")
r2 = c.predict("把诗改成五言绝句", api_name="/send")
chat2 = r2[-1]
print("消息数:", len(chat2), "| 助手:", text_of(chat2[-1])[:50], "...")

print("\n=== 4. 新建第二个会话（隔离验证）===")
c.predict(api_name="/new_chat")
r3 = c.predict("1+1等于几", api_name="/send")
chat3 = r3[-1]
print("会话2消息数:", len(chat3), "| 助手:", text_of(chat3[-1])[:40], "...")

print("\n=== 5. 切换回第一个会话（历史恢复）===")
r4 = c.predict(api_name="/open_chat_0")
print("输出数:", len(r4), "| 聊天区消息数:", len(r4[2]))
print("恢复的用户消息:", text_of(r4[2][0]))

print("\n=== 6. 删除当前会话 ===")
r5 = c.predict(api_name="/delete_chat_0")
print("输出数:", len(r5), "| 聊天区消息数:", len(r5[2]), "(剩余会话应为会话2: 1条)")
print("✅ 界面端到端验证完成")
