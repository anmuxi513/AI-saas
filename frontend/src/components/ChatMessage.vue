<script setup>
import { ref, computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps({
  message: { type: Object, required: true },
  streaming: { type: Boolean, default: false },
})

const isUser = computed(() => props.message.role === 'user')
const copied = ref(false)

const rendered = computed(() => {
  const text = props.message.content || ''
  return DOMPurify.sanitize(marked.parse(text))
})

async function copy() {
  const text = props.message.content || ''
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    // 兼容非安全上下文：降级复制
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    ta.remove()
  }
  copied.value = true
  setTimeout(() => (copied.value = false), 1600)
}
</script>

<template>
  <div class="msg-row" :class="isUser ? 'row-user' : 'row-assistant'">
    <div v-if="!isUser" class="avatar" aria-hidden="true">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="3" width="18" height="18" rx="5" fill="var(--color-primary)" />
        <path d="M8 8v8M12 8v8M16 8v8" stroke="#fff" stroke-width="1.8" stroke-linecap="round" />
      </svg>
    </div>
    <div class="msg-body">
      <div class="bubble" :class="isUser ? 'bubble-user' : 'bubble-assistant'">
        <div v-if="!isUser && !message.content && streaming" class="typing" aria-label="正在输入">
          <span></span><span></span><span></span>
        </div>
        <div v-else class="md-body" v-html="rendered"></div>
        <span v-if="!isUser && message.content && streaming" class="cursor" aria-hidden="true"></span>
      </div>
      <button
        v-if="!isUser && message.content"
        class="copy-btn"
        :class="{ 'copied': copied }"
        :aria-label="copied ? '已复制' : '复制回复'"
        @click="copy"
      >
        <svg v-if="!copied" width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <rect x="9" y="9" width="11" height="11" rx="2" stroke="currentColor" stroke-width="1.8" />
          <path d="M5 15V5a2 2 0 0 1 2-2h10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
        </svg>
        <span v-else class="copied-text">已复制</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.msg-row {
  display: flex;
  gap: 12px;
  margin-bottom: 22px;
  align-items: flex-start;
  animation: msg-in 0.2s ease both;
}
@keyframes msg-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
.row-user { justify-content: flex-end; }
.msg-body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 5px;
  max-width: min(720px, 82%);
}
.row-user .msg-body { align-items: flex-end; }

.avatar {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--color-muted), #dbeafe);
  box-shadow: inset 0 0 0 1px rgba(30, 64, 175, 0.08);
  margin-top: 2px;
}

.bubble {
  max-width: 100%;
  padding: 13px 18px;
  border-radius: 16px;
  font-size: 15px;
  line-height: 1.7;
  word-break: break-word;
}
.bubble-user {
  background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%);
  color: #fff;
  border-bottom-right-radius: 6px;
  box-shadow: 0 4px 14px rgba(30, 64, 175, 0.28);
}
.bubble-assistant {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-bottom-left-radius: 6px;
  box-shadow: var(--shadow-sm);
}
.cursor {
  display: inline-block;
  width: 8px;
  height: 16px;
  margin-left: 2px;
  vertical-align: text-bottom;
  background: var(--color-primary);
  border-radius: 1px;
  animation: blink 1s steps(2) infinite;
}
@keyframes blink { 50% { opacity: 0; } }

.typing { display: inline-flex; gap: 5px; padding: 6px 2px; }
.typing span {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--color-secondary);
  animation: bounce 1.2s infinite;
}
.typing span:nth-child(2) { animation-delay: 0.15s; }
.typing span:nth-child(3) { animation-delay: 0.3s; }
@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.35; }
  30% { transform: translateY(-4px); opacity: 1; }
}

/* markdown 内容样式 */
.md-body :deep(p) { margin: 0 0 8px; }
.md-body :deep(p:last-child) { margin-bottom: 0; }
.md-body :deep(pre) {
  background: #0f172a;
  color: #e2e8f0;
  padding: 14px 16px;
  border-radius: 10px;
  overflow-x: auto;
  font-size: 13px;
  margin: 10px 0;
  border: 1px solid rgba(148, 163, 184, 0.2);
}
.md-body :deep(code) {
  font-family: var(--font-mono);
  font-size: 13px;
  background: var(--color-muted);
  padding: 2px 6px;
  border-radius: 5px;
}
.md-body :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}
.md-body :deep(ul), .md-body :deep(ol) { padding-left: 22px; margin: 8px 0; }
.md-body :deep(li) { margin: 4px 0; }
.md-body :deep(h1), .md-body :deep(h2), .md-body :deep(h3) { margin: 14px 0 8px; font-size: 1.08em; font-family: var(--font-heading); }
.md-body :deep(blockquote) {
  border-left: 3px solid var(--color-secondary);
  margin: 10px 0;
  padding: 2px 14px;
  color: var(--color-muted-foreground);
  background: var(--color-muted);
  border-radius: 0 8px 8px 0;
}
.md-body :deep(hr) { border: none; border-top: 1px solid var(--color-border); margin: 14px 0; }
.md-body :deep(a) { color: #2563eb; text-decoration: underline; }

/* 复制按钮：纯淡入，无位移（避免鼠标扫过消息时的抖动感） */
.copy-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--color-border);
  background: var(--color-card);
  color: var(--color-muted-foreground);
  padding: 4px 8px;
  border-radius: 7px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s ease, color 0.15s ease, border-color 0.15s ease;
  font-size: 12px;
}
.msg-row:hover .copy-btn { opacity: 1; }
.copy-btn:hover {
  color: var(--color-primary);
  border-color: var(--color-secondary);
}
.copy-btn.copied {
  opacity: 1;
  color: #166534;
  border-color: #86efac;
  background: #f0fdf4;
}
.copied-text { font-size: 12px; font-weight: 500; }
</style>
