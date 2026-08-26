<script setup>
import { ref, onMounted } from 'vue'

// MNIST 手写数字识别面板
// 预处理与模型训练一致：黑底白字 → 28x28 → (R/255 - 0.1307) / 0.3081
const CANVAS_SIZE = 280
const MEAN = 0.1307
const STD = 0.3081

const canvasRef = ref(null)
const drawing = ref(false)
const loading = ref(false)
const error = ref('')
const result = ref(null)          // { pred, probs: [10] }
const maxProb = ref(1)

let ctx = null

function initCanvas() {
  const canvas = canvasRef.value
  ctx = canvas.getContext('2d')
  ctx.fillStyle = '#000'
  ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE)
  ctx.strokeStyle = '#fff'
  ctx.lineWidth = 18
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
}

function pos(e) {
  const rect = canvasRef.value.getBoundingClientRect()
  return {
    x: ((e.clientX - rect.left) * CANVAS_SIZE) / rect.width,
    y: ((e.clientY - rect.top) * CANVAS_SIZE) / rect.height,
  }
}

function start(e) {
  drawing.value = true
  const p = pos(e)
  ctx.beginPath()
  ctx.moveTo(p.x, p.y)
  ctx.lineTo(p.x + 0.1, p.y + 0.1)
  ctx.stroke()
}

function move(e) {
  if (!drawing.value) return
  const p = pos(e)
  ctx.lineTo(p.x, p.y)
  ctx.stroke()
}

function stop() { drawing.value = false }

function clear() {
  ctx.fillStyle = '#000'
  ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE)
  result.value = null
  error.value = ''
}

function extract() {
  const off = document.createElement('canvas')
  off.width = off.height = 28
  const octx = off.getContext('2d')
  octx.drawImage(canvasRef.value, 0, 0, 28, 28)
  const px = octx.getImageData(0, 0, 28, 28).data
  const out = new Array(784)
  for (let i = 0; i < 784; i++) out[i] = (px[i * 4] / 255 - MEAN) / STD
  return out
}

async function predict() {
  error.value = ''
  loading.value = true
  try {
    const r = await fetch('/api/mnist/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pixels: extract() }),
    })
    const data = await r.json()
    if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`)
    result.value = data
    maxProb.value = Math.max(...data.probs, 0.01)
  } catch (e) {
    error.value = `识别失败：${e.message}`
  } finally {
    loading.value = false
  }
}

onMounted(initCanvas)
</script>

<template>
  <div class="panel">
    <!-- 手写板 -->
    <div class="pad-card card">
      <h2 class="panel-title">手写数字板</h2>
      <div class="canvas-wrap">
        <canvas
          ref="canvasRef"
          :width="CANVAS_SIZE"
          :height="CANVAS_SIZE"
          class="pad-canvas"
          aria-label="手写数字输入板"
          @pointerdown="start"
          @pointermove="move"
          @pointerup="stop"
          @pointerleave="stop"
        ></canvas>
      </div>
      <div class="pad-actions">
        <button class="btn btn-secondary" @click="clear">清空</button>
        <button class="btn btn-primary" :disabled="loading" @click="predict">
          {{ loading ? '识别中…' : '识别' }}
        </button>
      </div>
      <p class="hint muted">用鼠标或手指在上面写一个数字（0-9）</p>
      <p v-if="error" class="error-text" role="alert">{{ error }}</p>
    </div>

    <!-- 结果 -->
    <div class="result-card card">
      <h2 class="panel-title">识别结果</h2>
      <div v-if="result" class="result-body">
        <div class="prediction">
          <span class="pred-label muted">预测数字</span>
          <span class="pred-value mono">{{ result.pred }}</span>
        </div>
        <div class="prob-list" aria-label="各数字概率">
          <div v-for="(p, i) in result.probs" :key="i" class="prob-row">
            <span class="prob-digit mono">{{ i }}</span>
            <div class="prob-track">
              <div
                class="prob-fill"
                :class="{ 'prob-fill-top': i === result.pred }"
                :style="{ width: `${(p / maxProb) * 100}%` }"
              ></div>
            </div>
            <span class="prob-val mono">{{ (p * 100).toFixed(1) }}%</span>
          </div>
        </div>
      </div>
      <div v-else class="result-empty muted">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <rect x="3" y="3" width="18" height="18" rx="4" stroke="currentColor" stroke-width="1.6" />
          <path d="M12 8v4M12 15.5v.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
        </svg>
        <p>在左侧手写板写一个数字，点击「识别」查看结果</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.panel {
  display: grid;
  grid-template-columns: minmax(320px, 420px) 1fr;
  gap: var(--space-lg);
  align-items: start;
}
.panel-title { font-size: 15px; margin-bottom: var(--space-md); }
.canvas-wrap {
  display: flex;
  justify-content: center;
  background: #000;
  border-radius: var(--radius-lg);
  padding: 10px;
}
.pad-canvas {
  width: 100%;
  max-width: 320px;
  aspect-ratio: 1;
  touch-action: none;
  cursor: crosshair;
  border-radius: var(--radius-sm);
}
.pad-actions {
  display: flex;
  gap: var(--space-sm);
  margin-top: var(--space-md);
}
.hint { font-size: 12px; margin: var(--space-sm) 0 0; }
.error-text { color: var(--color-destructive); font-size: 13px; margin-top: var(--space-sm); }

/* 结果 */
.prediction {
  display: flex;
  align-items: center;
  gap: var(--space-lg);
  margin-bottom: var(--space-lg);
  padding: 14px 18px;
  background: linear-gradient(135deg, rgba(30, 64, 175, 0.06), rgba(37, 99, 235, 0.1));
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}
.pred-label { font-size: 14px; font-weight: 500; }
.pred-value {
  font-size: 54px;
  font-weight: 700;
  line-height: 1;
  background: linear-gradient(135deg, var(--color-primary), #2563eb);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.prob-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: 8px;
}
.prob-digit { width: 16px; font-size: 13px; font-weight: 600; }
.prob-track {
  flex: 1;
  height: 12px;
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
.prob-val { width: 52px; font-size: 12px; text-align: right; }
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
