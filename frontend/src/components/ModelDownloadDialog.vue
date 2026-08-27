<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useChatStore } from '../stores/chat'

const chat = useChatStore()
const show = ref(false)
const model = ref({ installed: false, chat_ready: false, downloading: false, state: 'idle', cur: 0, total: 0, pct: 0, error: null })
let timer = null

function fmtMB(b) {
  if (!b) return '0'
  return (b / 1024 / 1024).toFixed(0)
}

async function poll() {
  try {
    const r = await fetch('/api/model/status')
    model.value = await r.json()
  } catch { /* 服务暂不可达 */ }
  // 下载完成 → 后端自动加载模型 → 就绪后关闭弹窗
  if (model.value.state === 'done' || model.value.installed) {
    if (model.value.chat_ready) {
      show.value = false
      stopPoll()
    }
  }
}

function startPoll() {
  stopPoll()
  timer = setInterval(poll, 1500)
}
function stopPoll() {
  if (timer) { clearInterval(timer); timer = null }
}

async function startDownload() {
  try {
    const r = await fetch('/api/model/download', { method: 'POST' })
    await r.json()
    startPoll()
    poll()
  } catch (e) {
    model.value.error = `启动下载失败：${e.message}`
  }
}

// 聊天未安装 → 自动弹出
watch(() => chat.status.chat_error, (err) => {
  if (err && err.includes('下载聊天模型')) {
    show.value = true
    startPoll()
  }
})
watch(() => chat.status.chat_ready, (ready) => {
  if (ready) { show.value = false; stopPoll() }
})

onMounted(async () => {
  await poll()
  if (model.value.installed && model.value.chat_ready) return
  if (chat.status.chat_error?.includes('下载聊天模型')) {
    show.value = true
    startPoll()
  }
})
onBeforeUnmount(stopPoll)

// 供外部（状态栏点击）调用
function open() {
  show.value = true
  poll()
  if (model.value.downloading || model.value.state === 'downloading') startPoll()
}
defineExpose({ open })
</script>

<template>
  <transition name="dl-fade">
    <div v-if="show" class="dl-overlay" @click.self="model.downloading ? null : (show = false)">
      <div class="dl-card" role="dialog" aria-modal="true" aria-label="聊天模型下载">
        <div class="dl-head">
          <div class="dl-title">
            <span class="dl-icon" aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <rect x="3" y="3" width="18" height="18" rx="5" fill="#fff" />
                <path d="M8 8v8M12 8v8M16 8v8" stroke="#1E40AF" stroke-width="1.8" stroke-linecap="round" />
              </svg>
            </span>
            <div>
              <h3 class="dl-h3">聊天模型</h3>
              <p class="dl-sub">Qwen2.5-0.5B · 本地运行 · 数据不出本机</p>
            </div>
          </div>
          <button class="dl-close" aria-label="关闭" :disabled="model.downloading" @click="show = false">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
            </svg>
          </button>
        </div>

        <!-- 未安装 -->
        <div v-if="!model.installed && !model.downloading && model.state !== 'downloading' && model.state !== 'done'" class="dl-body">
          <div class="dl-notice">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M12 8v4m0 4h.01M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
            </svg>
            <p>聊天功能需要下载本地模型（约 1GB）。下载一次即可永久使用，支持断点续传。</p>
          </div>
          <div class="dl-meta">
            <span class="dl-meta-item">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
              </svg>
              国内镜像加速
            </span>
            <span class="dl-meta-item">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <rect x="4" y="4" width="16" height="16" rx="3" stroke="currentColor" stroke-width="1.8" />
                <path d="M9 9v6M12 9v6M15 9v6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
              </svg>
              下载约 10-30 分钟
            </span>
          </div>
          <p v-if="model.error" class="dl-error" role="alert">❌ {{ model.error }}</p>
          <div class="dl-actions">
            <button class="btn btn-secondary" @click="show = false">暂不下载</button>
            <button class="btn btn-primary" @click="startDownload">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M12 4v12m0 0l-5-5m5 5l5-5M4 20h16" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
              开始下载
            </button>
          </div>
        </div>

        <!-- 下载中 -->
        <div v-else-if="model.downloading || model.state === 'downloading'" class="dl-body">
          <div class="dl-progress-head">
            <span class="dl-state">正在下载…</span>
            <span class="dl-pct mono">{{ Math.round(model.pct || 0) }}%</span>
          </div>
          <div class="dl-track" role="progressbar" :aria-valuenow="Math.round(model.pct || 0)" aria-valuemin="0" aria-valuemax="100">
            <div class="dl-fill" :style="{ width: `${model.pct || 0}%` }"></div>
          </div>
          <div class="dl-progress-meta">
            <span class="mono">{{ fmtMB(model.cur) }} MB / {{ fmtMB(model.total) }} MB</span>
            <span class="muted">请勿关闭应用窗口</span>
          </div>
        </div>

        <!-- 完成 -->
        <div v-else-if="model.state === 'done' || model.installed" class="dl-body">
          <div class="dl-done">
            <svg width="44" height="44" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle cx="12" cy="12" r="10" fill="#16a34a" />
              <path d="M7.5 12.5l3 3 6-6.5" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <h3 class="dl-h3">下载完成</h3>
            <p class="muted">正在加载模型，稍后即可开始对话…</p>
            <div class="spinner-mini" aria-hidden="true"></div>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.dl-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(16, 32, 79, 0.45);
  backdrop-filter: blur(3px);
}
.dl-card {
  width: 460px;
  max-width: calc(100vw - 40px);
  background: var(--color-card);
  border-radius: 18px;
  box-shadow: 0 24px 60px rgba(16, 32, 79, 0.35);
  overflow: hidden;
  animation: dl-in 0.22s ease both;
}
@keyframes dl-in {
  from { opacity: 0; transform: translateY(10px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.dl-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  background: linear-gradient(135deg, var(--color-primary), #2563eb);
  color: #fff;
}
.dl-title { display: flex; align-items: center; gap: 12px; }
.dl-icon {
  width: 38px; height: 38px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.16);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.2);
}
.dl-h3 { margin: 0; font-size: 15px; font-weight: 600; color: inherit; }
.dl-sub { margin: 2px 0 0; font-size: 11.5px; color: rgba(255, 255, 255, 0.72); }
.dl-close {
  border: none; background: transparent; color: rgba(255, 255, 255, 0.8);
  cursor: pointer; padding: 5px; border-radius: 7px;
}
.dl-close:hover { background: rgba(255, 255, 255, 0.16); }
.dl-close:disabled { opacity: 0.4; cursor: not-allowed; }
.dl-body { padding: 22px 20px 20px; }
.dl-notice {
  display: flex; gap: 10px; align-items: flex-start;
  background: var(--color-muted); border: 1px solid var(--color-border);
  border-radius: 12px; padding: 12px 14px;
  color: var(--color-foreground); font-size: 13.5px; line-height: 1.6;
}
.dl-notice svg { color: var(--color-primary); flex-shrink: 0; margin-top: 1px; }
.dl-notice p { margin: 0; }
.dl-meta { display: flex; gap: 16px; margin: 14px 4px; }
.dl-meta-item {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 12px; color: var(--color-muted-foreground);
}
.dl-meta-item svg { color: var(--color-secondary); }
.dl-error { color: var(--color-destructive); font-size: 13px; margin: 0 4px 10px; }
.dl-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 6px; }

/* 进度 */
.dl-progress-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; }
.dl-state { font-size: 14px; font-weight: 600; color: var(--color-foreground); }
.dl-pct { font-size: 22px; font-weight: 700; color: var(--color-primary); }
.dl-track {
  height: 10px; background: var(--color-muted);
  border-radius: 999px; overflow: hidden;
}
.dl-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), #2563eb, #16a34a);
  border-radius: 999px;
  transition: width 0.4s ease;
}
.dl-progress-meta {
  display: flex; justify-content: space-between; margin-top: 10px;
  font-size: 12.5px; color: var(--color-muted-foreground);
}
.dl-progress-meta .muted { font-size: 12px; }

/* 完成 */
.dl-done { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 10px 0 4px; text-align: center; }
.dl-done .dl-h3 { color: var(--color-foreground); }
.dl-done p { margin: 0; font-size: 13.5px; }
.spinner-mini {
  width: 18px; height: 18px; margin-top: 6px;
  border: 2.5px solid var(--color-muted);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.dl-fade-enter-active, .dl-fade-leave-active { transition: opacity 0.2s ease; }
.dl-fade-enter-from, .dl-fade-leave-to { opacity: 0; }
</style>
