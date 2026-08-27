<script setup>
import { onMounted, computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useChatStore } from './stores/chat'
import ModelDownloadDialog from './components/ModelDownloadDialog.vue'

const route = useRoute()
const chat = useChatStore()
const modelDialog = ref(null)

const navItems = [
  { name: '聊天对话', to: '/chat', icon: 'chat', desc: '与本地 AI 对话' },
  { name: '模型识别', to: '/inference', icon: 'scan', desc: 'MNIST · EuroSAT' },
]

const pageTitle = computed(() => {
  const hit = navItems.find((n) => route.path.startsWith(n.to))
  return hit ? hit.name : 'AI 模型训练平台'
})

// 聊天页显示当前会话标题
const topbarSub = computed(() => {
  if (route.path.startsWith('/chat')) {
    return chat.activeSid ? chat.activeTitle : '开始新的对话'
  }
  const hit = navItems.find((n) => route.path.startsWith(n.to))
  return hit ? hit.desc : ''
})

const statusText = computed(() => {
  const s = chat.status
  if (s.loading) return { text: '模型加载中', cls: 'warn' }
  if (s.chat_ready) return { text: '服务就绪', cls: 'ok' }
  if (s.chat_error) {
    const brief = s.chat_error.length > 26 ? `${s.chat_error.slice(0, 26)}…` : s.chat_error
    return { text: brief, cls: 'err', detail: s.chat_error }
  }
  return { text: '连接中', cls: 'warn' }
})

onMounted(() => {
  chat.fetchStatus()
  setInterval(() => chat.fetchStatus(), 15000)
})
</script>

<template>
  <div class="app-shell">
    <!-- 深色侧边栏 -->
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-logo">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <rect x="3" y="3" width="18" height="18" rx="5" fill="#fff" />
            <path d="M8 8v8M12 8v8M16 8v8" stroke="#1E40AF" stroke-width="1.8" stroke-linecap="round" />
          </svg>
        </div>
        <div class="brand-text">
          <div class="brand-name">AI 训练平台</div>
          <div class="brand-sub">Enterprise</div>
        </div>
      </div>

      <nav class="nav" aria-label="主导航">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          active-class="nav-link-active"
        >
          <span class="nav-icon">
            <svg v-if="item.icon === 'chat'" width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M21 12a8 8 0 0 1-8 8H4l2.3-2.9A8 8 0 1 1 21 12z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
            </svg>
            <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <rect x="4" y="4" width="16" height="16" rx="3" stroke="currentColor" stroke-width="1.8" />
              <path d="M9 4v16M4 9h16" stroke="currentColor" stroke-width="1.8" />
            </svg>
          </span>
          <span class="nav-text">
            <span class="nav-name">{{ item.name }}</span>
            <span class="nav-desc">{{ item.desc }}</span>
          </span>
        </router-link>
      </nav>

      <div
        class="sidebar-foot"
        :title="statusText.detail"
        :class="{ 'foot-clickable': statusText.cls === 'err' }"
        role="button"
        :tabindex="statusText.cls === 'err' ? 0 : undefined"
        @click="statusText.cls === 'err' && modelDialog?.open()"
        @keydown.enter="statusText.cls === 'err' && modelDialog?.open()"
      >
        <span class="status-dot" :class="statusText.cls" aria-hidden="true"></span>
        <span class="foot-text">{{ statusText.text }}</span>
        <span v-if="statusText.cls === 'err'" class="foot-dl" aria-hidden="true">点击安装</span>
        <span class="foot-ver mono">v0.1</span>
      </div>
    </aside>

    <!-- 主区域 -->
    <div class="main-area">
      <header class="topbar">
        <div class="topbar-left">
          <h1 class="topbar-title">{{ pageTitle }}</h1>
          <span v-if="topbarSub" class="topbar-sub">{{ topbarSub }}</span>
        </div>
        <div class="topbar-right">
          <span class="badge badge-tech mono">
            <span class="badge-dot" aria-hidden="true"></span>
            Qwen2.5 · 本地推理
          </span>
        </div>
      </header>

      <main class="content">
        <router-view />
      </main>
    </div>

    <!-- 聊天模型下载弹窗 -->
    <ModelDownloadDialog ref="modelDialog" />
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--color-background);
}

/* ---- 深色侧边栏 ---- */
.sidebar {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #10204f 0%, #14295f 60%, #1a3478 100%);
  color: #fff;
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 22px 20px 18px;
}
.brand-logo {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(4px);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.14);
}
.brand-name {
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 16px;
  letter-spacing: 0.01em;
  line-height: 1.25;
}
.brand-sub {
  font-size: 10.5px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.55);
  margin-top: 1px;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  margin-top: 4px;
}
.nav-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.68);
  transition: all var(--transition-fast);
  cursor: pointer;
}
.nav-link:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
  text-decoration: none;
}
.nav-link-active {
  color: #fff;
  background: rgba(255, 255, 255, 0.14);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);
}
.nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
}
.nav-text { display: flex; flex-direction: column; gap: 1px; }
.nav-name { font-size: 14px; font-weight: 600; line-height: 1.3; }
.nav-desc { font-size: 11px; color: rgba(255, 255, 255, 0.45); }

.sidebar-foot {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}
.foot-clickable {
  cursor: pointer;
  transition: background var(--transition-fast);
}
.foot-clickable:hover { background: rgba(255, 255, 255, 0.07); }
.foot-dl {
  font-size: 11px;
  font-weight: 600;
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.14);
  padding: 2px 8px;
  border-radius: 999px;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-dot.ok { background: #4ade80; box-shadow: 0 0 0 3px rgba(74, 222, 128, 0.2); }
.status-dot.warn { background: #fbbf24; box-shadow: 0 0 0 3px rgba(251, 191, 36, 0.2); }
.status-dot.err { background: #f87171; box-shadow: 0 0 0 3px rgba(248, 113, 113, 0.2); }
.foot-text { flex: 1; }
.foot-ver { font-size: 11px; color: rgba(255, 255, 255, 0.4); }

/* ---- 主区域 ---- */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  flex-shrink: 0;
  padding: 0 var(--space-xl);
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--color-border);
}
.topbar-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
  min-width: 0;
}
.topbar-title {
  font-family: var(--font-heading);
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  white-space: nowrap;
}
.topbar-sub {
  font-size: 13px;
  color: var(--color-muted-foreground);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 320px;
}
.badge-tech {
  background: var(--color-muted);
  color: var(--color-primary);
  gap: 6px;
  border: 1px solid var(--color-border);
}
.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #16a34a;
}
.content {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
}

@media (max-width: 768px) {
  .sidebar { width: 68px; }
  .brand-text, .nav-text, .foot-text, .foot-ver { display: none; }
  .brand { justify-content: center; padding: 18px 0; }
  .nav-link { justify-content: center; padding: 10px; }
  .topbar { padding: 0 var(--space-md); }
  .topbar-sub { display: none; }
}
</style>
