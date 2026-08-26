"""临时诊断2: 发送按钮 + 槽位切换 + 全量 console（验证后删除）。"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    logs = []
    page.on("console", lambda m: logs.append(f"[{m.type}] {m.text[:200]}"))
    page.on("pageerror", lambda e: logs.append(f"[pageerror] {str(e)[:200]}"))
    page.goto("http://127.0.0.1:7860", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(6000)

    print("=== A. 输入框发送 ===")
    page.fill("#input-box textarea", "你好，介绍一下你自己")
    page.locator("#send-btn").click()
    page.wait_for_timeout(5000)
    msgs = page.locator("#chat-window .message-item").count()
    print("5s 后消息条数:", msgs, "| 输入框已清空:", page.input_value("#input-box textarea") == "")
    page.wait_for_timeout(30000)
    msgs = page.locator("#chat-window .message-item").count()
    print("35s 后消息条数:", msgs)
    if msgs:
        print("  用户:", page.locator("#chat-window .user-message .message-content").first.inner_text()[:40])
        print("  助手:", page.locator("#chat-window .bot-message .message-content").first.inner_text()[:60])
    print("  槽位:", page.locator(".slot-btn").all_inner_texts())

    print("\n=== B. 新建对话按钮 ===")
    page.locator("#new-chat-btn").click()
    page.wait_for_timeout(3000)
    print("  欢迎区可见:", page.locator("#welcome-col").is_visible())
    print("  聊天区消息:", page.locator("#chat-window .message-item").count())
    print("  槽位:", page.locator(".slot-btn").all_inner_texts())

    print("\n=== C. 点击第一个会话槽位（切回历史会话）===")
    page.locator("#slot-0").click()
    page.wait_for_timeout(3000)
    msgs = page.locator("#chat-window .message-item").count()
    print("  聊天区消息:", msgs, "| 欢迎区可见:", page.locator("#welcome-col").is_visible())
    if msgs:
        print("  首条用户消息:", page.locator("#chat-window .user-message .message-content").first.inner_text()[:40])

    print("\n=== D. 点击示例卡片（再次尝试）===")
    before = len(logs)
    page.locator("#example-card").nth(1).click()
    page.wait_for_timeout(30000)
    msgs = page.locator("#chat-window .message-item").count()
    print("  30s 后消息条数:", msgs)
    print("  槽位:", page.locator(".slot-btn").all_inner_texts())

    print("\n=== console 日志（后 12 条）===")
    for l in logs[-12:]:
        print("  ", l)

    page.screenshot(path=r"C:\Users\cc\Desktop\CC\AI模型训练_PyTorch\projects\chat\_shot5.png")
    print("\n截图 _shot5.png 已保存")
    browser.close()
