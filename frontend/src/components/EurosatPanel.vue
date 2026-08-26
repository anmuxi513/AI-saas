<script setup>
import { ref } from 'vue'

// EuroSAT 遥感地物分类面板：上传图片 → Top3 结果
const previewUrl = ref('')
const loading = ref(false)
const error = ref('')
const results = ref(null)   // [{ index, name, prob }]
const dragging = ref(false)

const fileInput = ref(null)

function onFile(file) {
  if (!file) return
  if (!file.type.startsWith('image/')) {
    error.value = '请选择图片文件（JPG/PNG）'
    return
  }
  error.value = ''
  results.value = null
  previewUrl.value = URL.createObjectURL(file)
}

function onPick(e) { onFile(e.target.files?.[0]) }

function onDrop(e) {
  dragging.value = false
  onFile(e.dataTransfer.files?.[0])
}

async function predict() {
  if (!previewUrl.value || loading.value) return
  error.value = ''
  loading.value = true
  try {
    const img = new Image()
    img.src = previewUrl.value
    await new Promise((res, rej) => { img.onload = res; img.onerror = rej })

    const canvas = document.createElement('canvas')
    canvas.width = img.naturalWidth
    canvas.height = img.naturalHeight
    canvas.getContext('2d').drawImage(img, 0, 0)
    const b64 = canvas.toDataURL('image/jpeg', 0.92).split(',')[1]

    const r = await fetch('/api/eurosat/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: b64 }),
    })
    const data = await r.json()
    if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`)
    results.value = data.results
  } catch (e) {
    error.value = `识别失败：${e.message}`
  } finally {
    loading.value = false
  }
}

function reset() {
  previewUrl.value = ''
  results.value = null
  error.value = ''
  if (fileInput.value) fileInput.value.value = ''
}
</script>

<template>
  <div class="panel">
    <!-- 上传区 -->
    <div class="upload-card card">
      <h2 class="panel-title">上传遥感图像</h2>
      <div
        class="drop-zone"
        :class="{ 'drop-active': dragging }"
        role="button"
        tabindex="0"
        @click="fileInput?.click()"
        @keydown.enter="fileInput?.click()"
        @dragover.prevent="dragging = true"
        @dragleave.prevent="dragging = false"
        @drop.prevent="onDrop"
      >
        <template v-if="!previewUrl">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M12 16V4m0 0l-4 4m4-4l4 4" stroke="var(--color-primary)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
            <path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" stroke="var(--color-muted-foreground)" stroke-width="1.8" stroke-linecap="round" />
          </svg>
          <p class="drop-text">点击选择或拖拽图片到此处</p>
          <p class="drop-sub muted">支持 JPG / PNG · 建议使用遥感影像（如 EuroSAT 数据集图片）</p>
        </template>
        <img v-else :src="previewUrl" class="preview" alt="待识别图片预览" />
      </div>
      <input ref="fileInput" type="file" accept="image/*" class="hidden-input" @change="onPick" />
      <div class="upload-actions">
        <button class="btn btn-secondary" :disabled="!previewUrl" @click="reset">重新选择</button>
        <button class="btn btn-primary" :disabled="!previewUrl || loading" @click="predict">
          {{ loading ? '识别中…' : '开始识别' }}
        </button>
      </div>
      <p v-if="error" class="error-text" role="alert">{{ error }}</p>
    </div>

    <!-- 结果 -->
    <div class="result-card card">
      <h2 class="panel-title">分类结果</h2>
      <div v-if="results" class="result-body">
        <div v-for="(r, i) in results" :key="r.index" class="res-row" :class="{ 'res-top': i === 0 }">
          <span class="res-rank mono">{{ i + 1 }}</span>
          <div class="res-info">
            <div class="res-name">
              {{ r.name }}
              <span v-if="i === 0" class="badge badge-success">最可能</span>
            </div>
            <div class="prob-track">
              <div
                class="prob-fill"
                :class="{ 'prob-fill-top': i === 0 }"
                :style="{ width: `${r.prob * 100}%` }"
              ></div>
            </div>
          </div>
          <span class="res-val mono">{{ (r.prob * 100).toFixed(1) }}%</span>
        </div>
      </div>
      <div v-else class="result-empty muted">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <rect x="3" y="3" width="18" height="18" rx="4" stroke="currentColor" stroke-width="1.6" />
          <path d="M12 8v4M12 15.5v.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
        </svg>
        <p>上传一张遥感图像，查看 Top-3 地物分类结果</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.panel {
  display: grid;
  grid-template-columns: minmax(320px, 480px) 1fr;
  gap: var(--space-lg);
  align-items: start;
}
.panel-title { font-size: 15px; margin-bottom: var(--space-md); }

.drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  min-height: 240px;
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
  padding: var(--space-md);
  text-align: center;
}
.drop-zone:hover, .drop-active {
  border-color: var(--color-primary);
  background: var(--color-muted);
}
.drop-text { font-size: 15px; font-weight: 500; margin: 0; }
.drop-sub { font-size: 12px; margin: 0; }
.preview {
  max-width: 100%;
  max-height: 320px;
  border-radius: var(--radius-md);
  object-fit: contain;
}
.hidden-input { display: none; }
.upload-actions {
  display: flex;
  gap: var(--space-sm);
  margin-top: var(--space-md);
}
.error-text { color: var(--color-destructive); font-size: 13px; margin-top: var(--space-sm); }

/* 结果 */
.res-row {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: 12px 0;
  border-bottom: 1px solid var(--color-border);
}
.res-row:last-child { border-bottom: none; }
.res-rank {
  width: 26px;
  height: 26px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: var(--color-muted);
  font-size: 13px;
  font-weight: 600;
}
.res-top .res-rank { background: var(--color-primary); color: var(--color-on-primary); }
.res-info { flex: 1; min-width: 0; }
.res-name {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 6px;
}
.prob-track {
  height: 10px;
  background: var(--color-muted);
  border-radius: 999px;
  overflow: hidden;
}
.prob-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-secondary), #60a5fa);
  border-radius: 999px;
  transition: width 0.4s ease;
}
.prob-fill-top { background: linear-gradient(90deg, var(--color-accent), #4ade80); }
.res-val {
  width: 60px;
  text-align: right;
  font-size: 14px;
  font-weight: 600;
}
.result-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-2xl) 0;
  text-align: center;
  font-size: 14px;
}

@media (max-width: 1024px) {
  .panel { grid-template-columns: 1fr; }
}
</style>
