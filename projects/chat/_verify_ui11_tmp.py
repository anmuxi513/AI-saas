"""临时诊断7: 真实键盘输入代替 fill（验证后删除）。"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto("http://127.0.0.1:7860", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(6000)

    ta = page.locator("#input-box textarea")
    ta.click()
    page.keyboard.type("测试一下", delay=50)
    print("textarea 值:", repr(page.input_value("#input-box textarea")))
    page.keyboard.press("Enter")
    page.wait_for_timeout(25000)

    print("消息条数:", page.locator("#chat-window .message-item").count())
    if page.locator("#chat-window .message-item").count():
        print("用户:", page.locator("#chat-window .user-message .message-content").first.inner_text()[:50])
        print("助手:", page.locator("#chat-window .bot-message .message-content").first.inner_text()[:80])
    browser.close()
