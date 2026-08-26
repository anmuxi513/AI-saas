"""临时诊断6: dump 聊天区 DOM + 修复头像后重测（验证后删除）。"""
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
    page.wait_for_timeout(20000)

    html = page.locator("#chat-window").inner_html()
    print("聊天区 innerHTML 长度:", len(html))
    print(html[:1500])
    print("...")
    print("消息条数:", page.locator("#chat-window .message-item").count())
    browser.close()
