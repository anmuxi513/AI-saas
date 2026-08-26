"""临时诊断5: 抓取发送时的网络请求（验证后删除）。"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    reqs = []
    page.on("request", lambda r: reqs.append(f"{r.method} {r.url}"))
    page.on("response", lambda r: reqs.append(f"  -> {r.status} {r.url[:100]}") if r.status >= 400 else None)
    page.goto("http://127.0.0.1:7860", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(6000)
    reqs.clear()

    page.fill("#input-box textarea", "测试一下")
    page.locator("#send-btn").click()
    page.wait_for_timeout(12000)

    print("=== 点击后的网络请求 ===")
    for r in reqs[-20:]:
        print("  ", r)
    print("消息条数:", page.locator("#chat-window .message-item").count())
    browser.close()
