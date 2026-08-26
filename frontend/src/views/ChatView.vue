<script setup>
import { ref, computed, nextTick, watch, onMounted, onBeforeUnmount } from 'vue'
import { useChatStore } from '../stores/chat'
import ChatMessage from '../components/ChatMessage.vue'

const chat = useChatStore()
const input = ref('')
const searchText = ref('')
const scrollArea = ref(null)
const inputBox = ref(null)
const showScrollBtn = ref(false)

const suggestions = [
  '帮我写一份本周工作周报模板',
  '用最通俗的话解释什么是机器学习',
  'Python 入门推荐几本经典书籍',
]

/* ---------------- 输入框高度自适应 ---------------- */
function autoResize() {
  const el = inputBox.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 160)}px`
}
watch(input, () => autoResize())

/* ---------------- 会话分组 + 搜索 ---------------- */
const GROUP_ORDER = ['今天', '昨天', '最近 7 天', '更早']

function groupOf(ts) {
  if (!ts) return '更早'
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const that = new Date(ts * 1000)
  that.setHours(0, 0, 0, 0)
  const days = Math.floor((today - that) / 86400000)
  if (days <= 0) return '今天'
  if (days === 1) return '昨天'
  if (days <= 7) return '最近 7 天'
  return '更早'
}

const groups = computed(() => {
  const kw = searchText.value.trim().toLowerCase()
  const map = {}
  for (const s of chat.sessions) {
    if (kw && !s.title.toLowerCase().includes(kw)) continue
    const g = groupOf(s.updated)
    ;(map[g] ||= []).push(s)
  }
  return map
})

function relTime(ts) {
  if (!ts) return ''
  const diff = Date.now() / 1000 - ts
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 172800) return '昨天'
  const d = new Date(ts * 1000)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

/* ---------------- 滚动 ---------------- */
function scrollToBottom() {
  const el = scrollArea.value
  if (!el) return
  el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  showScrollBtn.value = false
}

let userScrolledUp = false
let scrollRaf = null
watch(() => chat.messages, () => {
  // 流式更新时高频触发：用 rAF 合并，仅当用户贴近底部时跟随
  if (userScrolledUp) return
  if (scrollRaf) return
  scrollRaf = requestAnimationFrame(() => {
    scrollRaf = null
    scrollToBottom()
  })
}, { deep: true })

function onScroll() {
  const el = scrollArea.value
  if (!el) return
  const dist = el.scrollHeight - el.scrollTop - el.clientHeight
  userScrolledUp = dist > 120
  showScrollBtn.value = dist > 300 && chat.messages.length > 3
}

function focusInput() {
  nextTick(() => inputBox.value?.focus())
}

/* ---------------- 发送 ---------------- */
async function send(text) {
  const msg = (text ?? input.value).trim()
  if (!msg || chat.streaming) return
  input.value = ''
  await chat.sendMessage(msg)
  scrollToBottom()
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

// 切换会话：若正在生成先停止，避免流式状态串到新会话
async function openSession(sid) {
  if (chat.streaming && sid !== chat.activeSid) chat.stop()
  await chat.openSession(sid)
}

// 全局快捷键：Esc 停止生成；"/" 聚焦输入框
function onGlobalKeydown(e) {
  const tag = document.activeElement?.tagName
  const typing = tag === 'INPUT' || tag === 'TEXTAREA'
  if (e.key === 'Escape' && chat.streaming) {
    chat.stop()
    e.preventDefault()
  } else if (e.key === '/' && !typing) {
    e.preventDefault()
    focusInput()
  }
}

onMounted(async () => {
  autoResize()
  window.addEventListener('keydown', onGlobalKeydown)
  await chat.fetchStatus()
  await chat.loadSessions()
  if (chat.sessions.length) {
    await chat.openSession(chat.sessions[0].sid)
  } else {
    await chat.newSession()
  }
  scrollToBottom()
  focusInput()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onGlobalKeydown)
})
</script>

<template>
  <div class="chat-layout">
    <!-- 会话面板 -->
    <aside class="session-panel" aria-label="会话列表">
      <button class="btn new-btn" :disabled="chat.streaming" @click="chat.newSession()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" />
        </svg>
        新建对话
      </button>

      <div class="search-box">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true" class="search-icon">
          <circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="1.8" />
          <path d="M20 20l-3.5-3.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
        </svg>
        <input
          v-model="searchText"
          class="search-input"
          type="text"
          placeholder="搜索会话…"
          aria-label="搜索会话"
        />
        <button
          v-if="searchText"
          class="search-clear"
          aria-label="清除搜索"
          @click="searchText = ''"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
          </svg>
        </button>
      </div>

      <div class="session-list">
        <template v-for="g in GROUP_ORDER" :key="g">
          <div v-if="groups[g]?.length" class="session-group">
            <div class="group-head">
              <span class="group-label">{{ g }}</span>
              <span class="group-count mono">{{ groups[g].length }}</span>
            </div>
            <div
              v-for="s in groups[g]"
              :key="s.sid"
              class="session-item"
              :class="{ active: s.sid === chat.activeSid }"
              role="button"
              tabindex="0"
              @click="openSession(s.sid)"
              @keydown.enter="openSession(s.sid)"
            >
              <span class="item-indicator" aria-hidden="true"></span>
              <span class="sess-icon" aria-hidden="true">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                  <path d="M21 12a8 8 0 0 1-8 8H4l2.3-2.9A8 8 0 1 1 21 12z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
                </svg>
              </span>
              <span class="sess-title">{{ s.title }}</span>
              <span class="sess-time mono">{{ relTime(s.updated) }}</span>
              <button
                class="sess-del"
                :aria-label="`删除会话 ${s.title}`"
                @click.stop="chat.deleteSession(s.sid)"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
                </svg>
              </button>
            </div>
          </div>
        </template>

        <!-- 空状态 -->
        <div v-if="!chat.sessions.length" class="session-empty">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M21 12a8 8 0 0 1-8 8H4l2.3-2.9A8 8 0 1 1 21 12z" stroke="var(--color-muted-foreground)" stroke-width="1.5" stroke-linejoin="round" />
          </svg>
          <p>暂无会话，点击上方「新建对话」开始</p>
        </div>
        <div v-else-if="!Object.keys(groups).length" class="session-empty">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle cx="11" cy="11" r="7" stroke="var(--color-muted-foreground)" stroke-width="1.5" />
            <path d="M20 20l-3.5-3.5" stroke="var(--color-muted-foreground)" stroke-width="1.5" stroke-linecap="round" />
          </svg>
          <p>没有匹配「{{ searchText }}」的会话</p>
        </div>
      </div>
    </aside>

    <!-- 消息区 -->
    <div class="chat-main">
      <!-- 会话信息条 -->
      <div v-if="chat.messages.length" class="chat-head">
        <div class="chat-head-left">
          <span class="chat-head-title">{{ chat.activeTitle }}</span>
          <span class="badge badge-running mono">Qwen2.5-0.5B</span>
        </div>
        <button class="chat-head-clear" :disabled="chat.streaming" @click="chat.clearConversation()">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M4 6h16M9 6V4h6v2m-8 0l1 14h8l1-14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          清空对话
        </button>
      </div>

      <div ref="scrollArea" class="message-area" @scroll="onScroll">
        <transition name="view-fade" mode="out-in">
          <!-- 欢迎屏 -->
          <div v-if="!chat.messages.length" key="welcome" class="welcome">
          <div class="welcome-logo">
            <svg width="38" height="38" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <rect x="3" y="3" width="18" height="18" rx="5" fill="#fff" />
              <path d="M8 8v8M12 8v8M16 8v8" stroke="#1E40AF" stroke-width="1.8" stroke-linecap="round" />
            </svg>
          </div>
          <h2 class="welcome-title">今天有什么可以帮你？</h2>
          <p class="welcome-sub">本地对话模型 · 多轮上下文 · 流式输出 · 数据不出本机</p>
          <div class="capabilities" aria-label="能力标签">
            <span class="cap">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M12 3v3m0 12v3M3 12h3m12 0h3M5.6 5.6l2.1 2.1m8.6 8.6l2.1 2.1m0-12.8l-2.1 2.1M7.7 16.3l-2.1 2.1" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
              </svg>
              多轮对话
            </span>
            <span class="cap">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z" stroke="currentColor" stroke-width="2" stroke-linejoin="round" />
              </svg>
              流式输出
            </span>
            <span class="cap">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
              </svg>
              Markdown
            </span>
            <span class="cap">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <rect x="4" y="4" width="16" height="16" rx="3" stroke="currentColor" stroke-width="2" />
                <path d="M9 9v6M12 9v6M15 9v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
              </svg>
              本地运行
            </span>
          </div>
          <div class="suggestion-grid">
            <button
              v-for="s in suggestions"
              :key="s"
              class="suggestion"
              @click="send(s)"
            >
              <span class="suggestion-text">{{ s }}</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true" class="arrow">
                <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </button>
          </div>
        </div>

        <!-- 消息流 -->
        <div v-else key="messages" class="messages">
          <ChatMessage
            v-for="(m, i) in chat.messages"
            :key="i"
            :message="m"
            :streaming="chat.streaming && i === chat.messages.length - 1"
          />
        </div>
        </transition>

        <!-- 回到底部按钮 -->
        <transition name="fade-pop">
          <button
            v-if="showScrollBtn"
            class="scroll-btn"
            aria-label="回到底部"
            @click="scrollToBottom"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M12 4v14m0 0l-6-6m6 6l6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </button>
        </transition>
      </div>

      <!-- 输入区 -->
      <div class="input-area">
        <div class="input-box">
          <span class="model-chip mono" title="本地推理模型">
            <span class="model-chip-dot" aria-hidden="true"></span>
            Qwen
          </span>
          <textarea
            ref="inputBox"
            v-model="input"
            class="input chat-input"
            rows="1"
            :placeholder="chat.streaming ? 'AI 正在回复…（可继续输入，Enter 将在生成结束后发送）' : '给 AI 发送消息…（Enter 发送，Shift+Enter 换行）'"
            @keydown="onKeydown"
          ></textarea>
          <button
            class="send-btn"
            :class="{ 'stop-btn': chat.streaming }"
            :disabled="chat.streaming ? false : !input.trim()"
            :aria-label="chat.streaming ? '停止生成' : '发送'"
            @click="chat.streaming ? chat.stop() : send()"
          >
            <svg v-if="!chat.streaming" width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M4 12l16-7-7 16-2-7-7-2z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" fill="currentColor" />
            </svg>
            <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" />
            </svg>
          </button>
        </div>
        <p class="input-hint muted">Qwen2.5-0.5B 本地推理 · 对话仅保存在本机内存中</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-layout {
  display: flex;
  flex: 1;
  min-height: 0;
  background: var(--color-background);
}

/* ================= 会话面板 ================= */
.session-panel {
  width: 272px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 16px 12px;
  border-right: 1px solid var(--color-border);
  background: var(--color-card);
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--color-border) transparent;
}
.session-panel::-webkit-scrollbar { width: 5px; }
.session-panel::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 999px;
}
.session-panel::-webkit-scrollbar-track { background: transparent; }

/* 新建对话按钮：hover 高光扫过（sheen），无位移无旋转 */
.new-btn {
  position: relative;
  overflow: hidden;
  width: 100%;
  padding: 12px 14px;
  font-size: 14px;
  font-weight: 600;
  border-radius: 11px;
  background: linear-gradient(135deg, var(--color-primary) 0%, #2b5fe0 55%, #2563eb 100%);
  color: #fff;
  box-shadow:
    0 3px 12px rgba(30, 64, 175, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.18);
  transition: box-shadow var(--transition-base);
}
/* 高光带：hover 时从左向右扫过 */
.new-btn::after {
  content: '';
  position: absolute;
  top: 0;
  left: -70%;
  width: 45%;
  height: 100%;
  background: linear-gradient(105deg, transparent, rgba(255, 255, 255, 0.32), transparent);
  transform: skewX(-20deg);
  pointer-events: none;
}
.new-btn:hover:not(:disabled)::after {
  animation: btn-sheen 0.7s ease;
}
@keyframes btn-sheen {
  from { left: -70%; }
  to { left: 130%; }
}
.new-btn:hover:not(:disabled) {
  box-shadow:
    0 6px 18px rgba(30, 64, 175, 0.42),
    inset 0 1px 0 rgba(255, 255, 255, 0.26);
}
.new-btn:active:not(:disabled) {
  box-shadow:
    0 2px 6px rgba(30, 64, 175, 0.3),
    inset 0 2px 8px rgba(0, 0, 0, 0.16);
}
.new-btn:disabled { opacity: 0.55; cursor: not-allowed; }
.new-btn:disabled::after { display: none; }

/* 搜索框 */
.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 14px 2px 6px;
  padding: 8px 11px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: var(--color-muted);
  transition: all var(--transition-base);
}
.search-box:focus-within {
  border-color: var(--color-secondary);
  background: var(--color-card);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}
.search-icon { color: var(--color-muted-foreground); flex-shrink: 0; }
.search-input {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  font-family: var(--font-body);
  font-size: 13px;
  color: var(--color-foreground);
  outline: none;
}
.search-input::placeholder { color: var(--color-muted-foreground); opacity: 0.7; }
.search-clear {
  display: inline-flex;
  border: none;
  background: transparent;
  color: var(--color-muted-foreground);
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
}
.search-clear:hover { color: var(--color-foreground); }

/* 会话分组 */
.session-list {
  display: flex;
  flex-direction: column;
  gap: 6px;              /* 会话项之间的间距 */
  margin-top: 6px;
}
.session-group { margin-top: 12px; }
.session-group:first-child { margin-top: 0; }
.group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 10px 6px;
}
.group-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--color-muted-foreground);
}
.group-count {
  font-size: 10.5px;
  color: var(--color-muted-foreground);
  background: var(--color-muted);
  padding: 0 6px;
  border-radius: 999px;
  line-height: 16px;
}

/* 会话项：hover 只变背景/指示条，时间与删除按钮绝对定位重叠（布局恒定，杜绝抖动） */
.session-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 34px 9px 12px;   /* 右侧预留时间/删除按钮空间 */
  border-radius: 9px;
  font-size: 13px;
  color: var(--color-muted-foreground);
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}
.item-indicator {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%) scaleY(0);
  width: 3px;
  height: 60%;
  border-radius: 0 3px 3px 0;
  background: var(--color-secondary);
  opacity: 0;
  transition: transform var(--transition-fast), opacity var(--transition-fast);
}
.session-item:hover { background: var(--color-muted); }
.session-item:hover .item-indicator { opacity: 1; transform: translateY(-50%) scaleY(1); }
.session-item.active {
  background: linear-gradient(135deg, var(--color-primary), #2563eb);
  color: var(--color-on-primary);
  box-shadow: 0 3px 10px rgba(30, 64, 175, 0.22);
}
.session-item.active .item-indicator {
  background: #fff;
  opacity: 1;
  transform: translateY(-50%) scaleY(1);
}
.sess-icon {
  display: inline-flex;
  flex-shrink: 0;
  opacity: 0.7;
  transition: opacity var(--transition-fast);
}
.session-item:hover .sess-icon { opacity: 1; }
.session-item.active .sess-icon { opacity: 1; }
.sess-title {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
}
/* 时间与删除按钮：同一位置重叠，透明度交叉过渡，不参与布局变化 */
.sess-time,
.sess-del {
  position: absolute;
  right: 9px;
  top: 50%;
  transform: translateY(-50%);
  transition: opacity var(--transition-fast);
}
.sess-time {
  font-size: 10.5px;
  color: var(--color-muted-foreground);
  opacity: 0.75;
  pointer-events: none;
}
.session-item:hover .sess-time { opacity: 0; }
.session-item.active .sess-time { color: rgba(255, 255, 255, 0.72); }
.sess-del {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  opacity: 0;
}
.session-item:hover .sess-del { opacity: 1; }
.session-item:not(.active) .sess-del:hover { background: rgba(220, 38, 38, 0.14); color: var(--color-destructive); }
.session-item.active .sess-del:hover { background: rgba(255, 255, 255, 0.22); }

/* 空状态 */
.session-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 36px 12px;
  text-align: center;
  color: var(--color-muted-foreground);
  font-size: 13px;
}
.session-empty p { margin: 0; line-height: 1.6; }

/* ================= 消息区 ================= */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}
.chat-head {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  padding: 12px 32px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--color-border);
}
.chat-head-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.chat-head-title {
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 420px;
}
.chat-head-clear {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 1px solid var(--color-border);
  background: var(--color-card);
  color: var(--color-muted-foreground);
  font-size: 12px;
  padding: 5px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.chat-head-clear:hover:not(:disabled) {
  color: var(--color-destructive);
  border-color: #fca5a5;
}
.chat-head-clear:disabled { opacity: 0.5; cursor: not-allowed; }

.message-area {
  flex: 1;
  overflow-y: auto;
  padding: 28px 32px;
  scroll-behavior: smooth;
  background: linear-gradient(180deg, #fafcff 0%, var(--color-background) 60%);
  position: relative;
}
.messages {
  max-width: 860px;
  margin: 0 auto;
}

/* 欢迎屏 / 消息流 切换过渡 */
.view-fade-enter-active { transition: opacity 0.22s ease, transform 0.22s ease; }
.view-fade-leave-active { transition: opacity 0.15s ease; }
.view-fade-enter-from { opacity: 0; transform: translateY(8px); }
.view-fade-leave-to { opacity: 0; }

/* 回到底部按钮 */
.scroll-btn {
  position: sticky;
  float: right;
  bottom: 18px;
  margin-right: 8px;
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-border);
  border-radius: 50%;
  background: var(--color-card);
  color: var(--color-primary);
  cursor: pointer;
  box-shadow: var(--shadow-md);
  transition: all var(--transition-fast);
}
.scroll-btn:hover {
  border-color: var(--color-secondary);
  box-shadow: var(--shadow-lg);
  background: var(--color-muted);
}
.fade-pop-enter-active, .fade-pop-leave-active { transition: opacity 0.18s ease, transform 0.18s ease; }
.fade-pop-enter-from, .fade-pop-leave-to { opacity: 0; transform: translateY(6px); }

/* ---- 欢迎屏 ---- */
.welcome {
  max-width: 680px;
  margin: 10vh auto 0;
  text-align: center;
}
.welcome-logo {
  display: inline-flex;
  padding: 18px;
  border-radius: 22px;
  background: linear-gradient(135deg, var(--color-primary), #2563eb);
  box-shadow: 0 10px 26px rgba(30, 64, 175, 0.32);
  margin-bottom: 22px;
}
.welcome-title {
  font-family: var(--font-heading);
  font-size: 26px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--color-foreground);
}
.welcome-sub {
  font-size: 14px;
  color: var(--color-muted-foreground);
  margin-bottom: 20px;
}
.capabilities {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  margin-bottom: 30px;
}
.cap {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 500;
  color: var(--color-muted-foreground);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  padding: 4px 11px;
  border-radius: 999px;
  transition: all var(--transition-fast);
}
.cap svg { color: var(--color-secondary); transition: transform var(--transition-fast); }
.cap:hover {
  border-color: var(--color-secondary);
  color: var(--color-primary);
  background: var(--color-muted);
}
.cap:hover svg { transform: scale(1.2); }   /* 图标轻微放大 */
.suggestion-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  text-align: left;
}
.suggestion {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 15px 16px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-card);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-foreground);
  cursor: pointer;
  transition: all var(--transition-base);
  text-align: left;
  box-shadow: var(--shadow-sm);
}
.suggestion:hover {
  border-color: var(--color-secondary);
  box-shadow: var(--shadow-md);
  background: var(--color-muted);
}
.suggestion-text { line-height: 1.45; }
.arrow {
  color: var(--color-muted-foreground);
  flex-shrink: 0;
  transition: transform var(--transition-fast), color var(--transition-fast);
}
.suggestion:hover .arrow {
  color: var(--color-primary);
  transform: translateX(2px);    /* 箭头右移，指向感 */
}

/* ---- 输入区 ---- */
.input-area {
  flex-shrink: 0;
  padding: 14px 32px 20px;
  background: linear-gradient(transparent, var(--color-background) 35%);
}
.input-box {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  max-width: 860px;
  margin: 0 auto;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  padding: 10px 12px;
  box-shadow: 0 4px 18px rgba(30, 64, 175, 0.09);
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
}
.input-box:focus-within {
  border-color: var(--color-secondary);
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.12), 0 4px 18px rgba(30, 64, 175, 0.1);
}
.model-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.03em;
  color: var(--color-primary);
  background: var(--color-muted);
  border: 1px solid var(--color-border);
  padding: 5px 10px;
  border-radius: 999px;
  margin-bottom: 6px;
}
.model-chip-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #16a34a;
}
.chat-input {
  flex: 1;
  border: none;
  background: transparent;
  resize: none;
  padding: 8px 8px;
  font-size: 15px;
  line-height: 1.5;
  box-shadow: none;
  overflow-y: auto;
  min-height: 24px;
  max-height: 160px;
  transition: height 0.18s ease;   /* 高度自适应带过渡 */
}
.chat-input:focus { box-shadow: none; }
.send-btn {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--color-primary), #2563eb);
  color: var(--color-on-primary);
  cursor: pointer;
  transition: box-shadow var(--transition-fast), background var(--transition-fast);
  box-shadow: 0 3px 10px rgba(30, 64, 175, 0.28);
}
.send-btn svg {
  transition: transform var(--transition-fast);
}
.send-btn:hover:not(:disabled) svg { transform: translateY(-1px); }   /* 图标微上浮 */
.send-btn:hover:not(:disabled) {
  box-shadow: 0 5px 14px rgba(30, 64, 175, 0.36);
}
.send-btn:active:not(:disabled) { box-shadow: 0 2px 6px rgba(30, 64, 175, 0.3); }
.send-btn:disabled { opacity: 0.4; cursor: not-allowed; box-shadow: none; }
.stop-btn {
  background: var(--color-destructive);
  box-shadow: 0 3px 10px rgba(220, 38, 38, 0.28);
}
.stop-btn:hover:not(:disabled) {
  background: #b91c1c;
  transform: none;
}
.input-hint {
  max-width: 860px;
  margin: 10px auto 0;
  font-size: 12px;
  text-align: center;
}

@media (max-width: 900px) {
  .session-panel { display: none; }
  .message-area { padding: 20px 16px; }
  .input-area { padding: 12px 16px 18px; }
}
</style>
