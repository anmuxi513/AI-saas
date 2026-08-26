<script setup>
import { ref } from 'vue'
import MnistPanel from '../components/MnistPanel.vue'
import EurosatPanel from '../components/EurosatPanel.vue'

const active = ref('mnist')
const tabs = [
  { id: 'mnist', label: 'MNIST 手写数字', desc: '手写数字识别（CNN + ONNX）' },
  { id: 'eurosat', label: 'EuroSAT 遥感地物', desc: '卫星图像地物分类（ResNet18 + ONNX）' },
]
</script>

<template>
  <div class="inference-page">
    <!-- 页头 -->
    <div class="page-head">
      <div class="page-head-left">
        <h1 class="page-title">模型识别</h1>
        <span class="page-badge mono">
          <span class="page-badge-dot" aria-hidden="true"></span>
          ONNX Runtime
        </span>
      </div>
      <p class="muted page-desc">选择模型，在线体验 ONNX 推理服务</p>
    </div>

    <!-- 切换模块 -->
    <div class="tabs" role="tablist" aria-label="模型选择">
      <button
        v-for="t in tabs"
        :key="t.id"
        role="tab"
        :aria-selected="active === t.id"
        class="tab"
        :class="{ 'tab-active': active === t.id }"
        @click="active = t.id"
      >
        <span class="tab-label">{{ t.label }}</span>
        <span class="tab-desc">{{ t.desc }}</span>
      </button>
    </div>

    <!-- 面板 -->
    <div class="panel-wrap">
      <transition name="panel-fade" mode="out-in">
        <MnistPanel v-if="active === 'mnist'" key="mnist" />
        <EurosatPanel v-else key="eurosat" />
      </transition>
    </div>
  </div>
</template>

<style scoped>
.inference-page {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: var(--space-xl);
  overflow-y: auto;
}
.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: var(--space-lg);
}
.page-head-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.page-title { font-size: 22px; margin: 0; }
.page-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--color-primary);
  background: var(--color-muted);
  border: 1px solid var(--color-border);
  padding: 3px 10px;
  border-radius: 999px;
}
.page-badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #16a34a;
}
.page-desc { font-size: 14px; margin: 0; }

/* 切换模块（segmented tabs） */
.tabs {
  display: inline-flex;
  gap: 6px;
  padding: 5px;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  margin-bottom: var(--space-lg);
  align-self: flex-start;
}
.tab {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 10px 18px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.tab-label { font-size: 14px; font-weight: 600; color: var(--color-muted-foreground); }
.tab-desc { font-size: 11px; color: var(--color-muted-foreground); opacity: 0.8; }
.tab:hover { background: var(--color-muted); }
.tab-active { background: var(--color-primary); }
.tab-active .tab-label, .tab-active .tab-desc { color: var(--color-on-primary); }

.panel-wrap {
  flex: 1;
  min-height: 0;
}
/* 面板切换过渡 */
.panel-fade-enter-active,
.panel-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.panel-fade-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.panel-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
@media (prefers-reduced-motion: reduce) {
  .panel-fade-enter-active,
  .panel-fade-leave-active { transition: none; }
  .panel-fade-enter-from,
  .panel-fade-leave-to { transform: none; }
}
</style>
