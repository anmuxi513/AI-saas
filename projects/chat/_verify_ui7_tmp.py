"""临时诊断3: 发送按钮点击 + 全量 console（验证后删除）。"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    logs = []
    page.on("console", lambda m: logs.append(f"[{m.type}] {m.text[:300]}"))
    page.on("pageerror", lambda e: logs.append(f"[pageerror] {str(e)[:300]}"))
    page.goto("http://127.0.0.1:7860", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(6000)
    logs.clear()  # 只保留交互后的日志

    try:
        print("=== 输入框发送 ===")
        page.fill("#input-box textarea", "测试消息")
        page.locator("#send-btn").click()
        page.wait_for_timeout(8000)
        print("8s 后: 消息", page.locator("#chat-window .message-item").count(),
              "| 输入框:", repr(page.input_value("#input-box textarea")))
    except Exception as e:
        print("A 异常:", str(e)[:200])

    try:
        print("\n=== 回车发送 ===")
        page.fill("#input-box textarea", "回车测试")
        page.keyboard.press("Enter")
        page.wait_for_timeout(8000)
        print("8s 后: 消息", page.locator("#chat-window .message-item").count())
    except Exception as e:
        print("B 异常:", str(e)[:200])

    print("\n=== console 全部 ===")
    for l in logs:
        print("  ", l)
    browser.close()
