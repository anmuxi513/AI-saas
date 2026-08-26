"""临时诊断: 侧栏结构 + 点击事件错误抓取（验证后删除）。"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    page.on("console", lambda m: errors.append(f"[console.{m.type}] {m.text[:300]}") if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: errors.append(f"[pageerror] {str(e)[:300]}"))
    page.goto("http://127.0.0.1:7860", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(6000)

    # 1. slot-btn 祖先链（找侧栏容器）
    chain = page.evaluate("""() => {
        const el = document.querySelector('.slot-btn');
        const out = [];
        let n = el;
        for (let i = 0; n && i < 8; i++) {
            out.push(n.tagName.toLowerCase() + '#' + (n.id||'') + '.' + (n.className||'').toString().split(' ').filter(Boolean).slice(0,4).join('.'));
            n = n.parentElement;
        }
        return out;
    }""")
    print("slot-btn 祖先链:")
    for c in chain:
        print("   ", c)

    # 2. 点击示例卡片，抓错误
    print("\n点击示例卡片 nth(1) ...")
    page.locator("#example-card").nth(1).click()
    page.wait_for_timeout(40000)
    msgs = page.locator("#chat-window .message-item").count()
    print("消息条数:", msgs)
    print("槽位:", page.locator(".slot-btn").all_inner_texts())
    print("\n捕获的错误/警告:")
    for e in errors[:15]:
        print("  ", e)
    if not errors:
        print("   （无）")
    page.screenshot(path=r"C:\Users\cc\Desktop\CC\AI模型训练_PyTorch\projects\chat\_shot4.png")
    print("\n截图 _shot4.png 已保存")
    browser.close()
