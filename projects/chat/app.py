"""ChatGPT 风格持续对话界面（Gradio）。

    python app.py
    浏览器自动打开 http://127.0.0.1:7860

与 ChatGPT 对齐的界面要素:
- 左侧边栏: 新建对话 / 历史会话列表（点击切换、hover 删除、当前高亮）
- 顶栏: 当前会话标题
- 主区: 欢迎屏（logo + 示例提问）→ 多轮对话流（流式输出、markdown、代码块）
- 底部: 圆角输入框 + 圆形发送按钮（回车发送）
- 深色主题, 消息区限宽居中（ChatGPT 版式）

多会话: 每个会话独立的对话历史（ChatEngine），互不干扰。

注意: 旧界面样式 chatgpt.css 已随旧页面删除（2026-08 统一 Vue 3 前端重构）。
当前使用 Gradio 默认主题；后续界面由 frontend/ 的 Vue 3 页面取代。
"""
import os
import sys
import urllib.parse
import uuid

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import gradio as gr

from chat import ChatEngine
from model import get_model

PORT = 7860
MAX_SLOTS = 10  # 侧栏最多显示的会话槽位数
DEFAULT_SYSTEM = "你是Qwen，一个乐于助人的中文AI助手。请用简洁、准确的中文回答。"

# 旧 chatgpt.css 已删除（统一 Vue 3 前端重构）；暂用 Gradio 默认主题
CSS = ""

# 助手头像（ChatGPT 风格: 圆角方块徽标）
LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30">'
    '<rect width="30" height="30" rx="8" fill="#10a37f"/>'
    '<text x="15" y="20" font-size="13" fill="#fff" text-anchor="middle" '
    'font-family="Arial,sans-serif" font-weight="bold">AI</text></svg>'
)
LOGO = "data:image/svg+xml," + urllib.parse.quote(LOGO_SVG)

print("⏳ 正在启动对话服务，加载模型中...", flush=True)
get_model()  # 先加载模型，避免浏览器打开后干等
print(f"✅ 模型就绪！浏览器打开: http://127.0.0.1:{PORT}", flush=True)

# ---------------- 会话管理 ----------------
# SESSIONS: sid -> {"title": str, "engine": ChatEngine}
SESSIONS: dict = {}
ACTIVE: str | None = None


def new_session() -> str:
    global ACTIVE
    sid = uuid.uuid4().hex[:8]
    SESSIONS[sid] = {"title": "新对话", "engine": ChatEngine(system=DEFAULT_SYSTEM)}
    ACTIVE = sid
    return sid


def ensure_active() -> str:
    global ACTIVE
    if ACTIVE is None or ACTIVE not in SESSIONS:
        new_session()
    return ACTIVE


def engine_of() -> ChatEngine:
    return SESSIONS[ensure_active()]["engine"]


def to_history(engine: ChatEngine):
    """engine.messages → Chatbot 显示格式（去掉 system 消息）。"""
    return [{"role": m["role"], "content": m["content"]}
            for m in engine.messages if m["role"] != "system"]


def title_html() -> str:
    t = SESSIONS[ACTIVE]["title"] if (ACTIVE and ACTIVE in SESSIONS) else "新对话"
    return (f'<div id="topbar-title">{t}</div>'
            '<div id="topbar-actions">↗&nbsp;&nbsp;⋮</div>')


def slots_update(no_change: bool = False) -> list:
    """侧栏 2×MAX_SLOTS 个按钮的更新列表（标题按钮 + 删除按钮）。"""
    outs = []
    ids = list(SESSIONS)
    for i in range(MAX_SLOTS):
        if no_change:
            outs += [gr.update(), gr.update()]
        elif i < len(ids):
            sid = ids[i]
            on = sid == ACTIVE
            outs.append(gr.update(
                value=("● " if on else "") + SESSIONS[sid]["title"],
                visible=True,
                elem_classes=["slot-btn", "active"] if on else ["slot-btn"],
            ))
            outs.append(gr.update(visible=True))
        else:
            outs += [gr.update(visible=False), gr.update(visible=False)]
    return outs


def meta_out():
    """顶栏 + 全部侧栏按钮的更新（用于事件链的 then 阶段）。"""
    return [title_html(), *slots_update()]


def noop_out():
    """与 OUT_META 等长的空更新（槽位为空时的安全返回）。"""
    return [gr.update()] * (3 + 2 * MAX_SLOTS)


# ---------------- 事件处理 ----------------

def new_chat():
    """新建会话: 清空聊天区，回到欢迎屏。"""
    new_session()
    return [gr.update(visible=False), title_html(), gr.update(value=[]), *slots_update()]


def open_chat(sid: str):
    """切换会话: 加载该会话的历史。"""
    global ACTIVE
    ACTIVE = sid
    return [gr.update(visible=False), title_html(),
            gr.update(value=to_history(SESSIONS[sid]["engine"])), *slots_update()]


def delete_chat(sid: str):
    """删除会话; 删的是当前会话则切到最近一个，全删光回到欢迎屏。"""
    global ACTIVE
    SESSIONS.pop(sid, None)
    if ACTIVE == sid:
        ACTIVE = next(reversed(list(SESSIONS))) if SESSIONS else None
    if ACTIVE is None:
        return [gr.update(visible=True), title_html(), gr.update(value=[]), *slots_update()]
    return [gr.update(visible=False), title_html(),
            gr.update(value=to_history(SESSIONS[ACTIVE]["engine"])), *slots_update()]


def respond(message, history):
    """多轮对话核心: 流式生成，返回 [欢迎屏更新, 聊天区更新]。"""
    message = (message or "").strip()
    history = history or []
    if not message:
        yield [gr.update(), history]
        return
    engine = engine_of()
    # 首条消息确定会话标题（ChatGPT 行为）
    if not any(m["role"] == "user" for m in engine.messages):
        SESSIONS[ACTIVE]["title"] = message[:20]
    history.append({"role": "user", "content": message})
    reply = ""
    for chunk in engine.stream_chat(message):
        reply += chunk
        yield [gr.update(visible=False), history + [{"role": "assistant", "content": reply}]]


def post_send():
    """回复结束后刷新槽位对应关系和顶栏/侧栏（标题可能刚确定）。"""
    refresh_slot_sids()
    return meta_out()


# ---------------- 界面 ----------------
# 槽位 -> sid 的对应表（按钮事件按槽位取当前 sid）
slot_sids: list = [[] for _ in range(MAX_SLOTS)]


def refresh_slot_sids():
    ids = list(SESSIONS)
    for i in range(MAX_SLOTS):
        slot_sids[i].clear()
        if i < len(ids):
            slot_sids[i].append(ids[i])


with gr.Blocks(title="AI 对话助手") as demo:
    with gr.Sidebar(width=260):
        gr.HTML('<div id="sidebar-head">会话</div>')
        new_btn = gr.Button("＋  新建对话", elem_id="new-chat-btn")
        slot_rows = []
        for i in range(MAX_SLOTS):
            with gr.Row(elem_classes="slot-row", equal_height=True):
                b = gr.Button("", elem_id=f"slot-{i}", elem_classes="slot-btn", scale=4)
                d = gr.Button("✕", elem_id=f"slot-del-{i}", elem_classes="slot-del", scale=1)
                slot_rows.append((b, d))
        gr.HTML('<div id="sidebar-foot">Qwen2.5-0.5B · 纯本地运行 · 对话不上传</div>')

    with gr.Column(elem_id="main-col-inner"):
        topbar = gr.HTML(title_html(), elem_id="topbar")

        welcome = gr.Column(visible=True, elem_id="welcome-col")
        with welcome:
            gr.HTML(
                '<div id="welcome-logo">'
                '<div class="logo-badge">AI</div>'
                '<h1>今天有什么可以帮你？</h1>'
                '<p>本地对话模型 · 支持多轮上下文 · 流式输出</p>'
                '</div>'
            )
            with gr.Row(elem_id="example-cards"):
                ex1 = gr.Button("帮我写一份本周工作周报模板", elem_id="example-card", scale=1)
                ex2 = gr.Button("用最通俗的话解释什么是机器学习", elem_id="example-card", scale=1)
                ex3 = gr.Button("Python 入门推荐几本经典书籍", elem_id="example-card", scale=1)
            gr.HTML('<div id="welcome-hint">对话内容仅保存在本机内存中</div>')

        chatbot = gr.Chatbot(
            elem_id="chat-window",
            layout="bubble",
            height=520,
            avatar_images=(None, LOGO),
            placeholder="",
        )

        with gr.Row(elem_id="input-row"):
            msg = gr.Textbox(
                placeholder="给 AI 发送消息…（回车发送）",
                container=False,
                scale=8,
                lines=1,
                elem_id="input-box",
            )
            send = gr.Button("↑", elem_id="send-btn", scale=1)

    # ---------------- 事件绑定 ----------------
    OUT_META = [welcome, topbar, chatbot, *[c for row in slot_rows for c in row]]
    TOPBAR_SLOTS = [topbar, *[c for row in slot_rows for c in row]]

    def _new_chat_wrap():
        out = new_chat()
        refresh_slot_sids()
        return out

    def _open_chat_wrap(i):
        if not slot_sids[i]:
            return noop_out()
        out = open_chat(slot_sids[i][0])
        refresh_slot_sids()
        return out

    def _delete_chat_wrap(i):
        if not slot_sids[i]:
            return noop_out()
        out = delete_chat(slot_sids[i][0])
        refresh_slot_sids()
        return out

    new_btn.click(_new_chat_wrap, None, OUT_META, api_name="new_chat")
    for i, (b, d) in enumerate(slot_rows):
        b.click(lambda _i=i: _open_chat_wrap(_i), None, OUT_META, api_name=f"open_chat_{i}")
        d.click(lambda _i=i: _delete_chat_wrap(_i), None, OUT_META, api_name=f"delete_chat_{i}")

    # 发送（回车 / 按钮 / 示例卡片）: 流式回复 → 刷新顶栏+侧栏 → 清空输入框
    def _bind(trigger, api):
        trigger(respond, [msg, chatbot], [welcome, chatbot], api_name=api).then(
            post_send, None, TOPBAR_SLOTS, api_name=None
        ).then(lambda: "", None, msg, api_name=None)

    _bind(msg.submit, "send")
    _bind(send.click, "send_btn")
    for ex, text in [(ex1, "帮我写一份本周工作周报模板"),
                     (ex2, "用最通俗的话解释什么是机器学习"),
                     (ex3, "Python 入门推荐几本经典书籍")]:
        ex.click(respond, [gr.State(text), chatbot], [welcome, chatbot]).then(
            post_send, None, TOPBAR_SLOTS
        )

demo.queue()
demo.launch(
    server_name="0.0.0.0",
    server_port=PORT,
    inbrowser=True,
    theme=gr.themes.Base(),
    css=CSS,
)
