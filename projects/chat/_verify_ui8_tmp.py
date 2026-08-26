"""临时诊断4: 发送一次消息后立即结束（验证后删除）。"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto("http://127.0.0.1:7860", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(6000)
    page.fill("#input-box textarea", "测试一下")
    page.locator("#send-btn").click()
    page.wait_for_timeout(15000)
    print("消息条数:", page.locator("#chat-window .message-item").count())
    browser.close()
