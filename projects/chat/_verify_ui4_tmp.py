"""临时验证: playwright 驱动系统 Edge 检查 ChatGPT 风格界面（验证后删除）。"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto("http://127.0.0.1:7860", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(6000)

    # 1. 关键元素存在性
    checks = {
        "侧栏容器 [data-testid=sidebar]": page.locator('[data-testid="sidebar"]').count(),
        "新建对话按钮": page.locator("#new-chat-btn").count(),
        "顶栏": page.locator("#topbar").count(),
        "顶栏标题": page.locator("#topbar-title").count(),
        "欢迎区": page.locator("#welcome-col").count(),
        "欢迎 logo": page.locator("#welcome-logo").count(),
        "示例卡片": page.locator("#example-card").count(),
        "聊天区": page.locator("#chat-window").count(),
        "输入框": page.locator("#input-box textarea").count(),
        "发送按钮": page.locator("#send-btn").count(),
        "侧栏会话槽位(10个)": page.locator(".slot-btn").count(),
    }
    for k, v in checks.items():
        print(f"  {k}: {v}")

    # 2. 侧栏背景色（CSS 是否生效）
    sb = page.locator('[data-testid="sidebar"]').first
    if sb.count():
        bg = sb.evaluate("el => getComputedStyle(el).backgroundColor")
        print("  侧栏背景色:", bg)
    body_bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
    print("  body 背景色:", body_bg)
    ibg = page.evaluate(
        "getComputedStyle(document.querySelector('#input-box textarea')).backgroundColor"
    )
    print("  输入框背景色:", ibg)

    # 3. 截图
    page.screenshot(path=r"C:\Users\cc\Desktop\CC\AI模型训练_PyTorch\projects\chat\_shot2.png")
    print("  截图已保存 _shot2.png")

    # 4. 交互: 点击示例卡片 → 等待回复 → 检查消息渲染
    print("\n  点击示例卡片（解释机器学习）...")
    page.locator("#example-card").nth(1).click()
    page.wait_for_timeout(25000)  # 等模型生成（约 10-20s）
    msgs = page.locator("#chat-window .message-item").count()
    print("  生成后消息条数:", msgs)
    if msgs:
        user_txt = page.locator("#chat-window .user-message .message-content").first.inner_text()[:40]
        bot_txt = page.locator("#chat-window .bot-message .message-content").first.inner_text()[:60]
        print("  用户消息:", user_txt)
        print("  助手消息:", bot_txt)
    page.screenshot(path=r"C:\Users\cc\Desktop\CC\AI模型训练_PyTorch\projects\chat\_shot3.png")
    print("  对话截图已保存 _shot3.png")

    # 5. 侧栏会话是否出现（标题 = 首条消息前 20 字）
    slots = page.locator(".slot-btn").all_inner_texts()
    print("  侧栏槽位文字:", slots)

    browser.close()
print("✅ playwright 验证完成")
