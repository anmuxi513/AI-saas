import { defineStore } from 'pinia'

// 带超时的 fetch（防止服务端异常时 UI 永久挂起）
async function fetchTimeout(url, options = {}, timeout = 8000) {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeout)
  try {
    return await fetch(url, { ...options, signal: ctrl.signal })
  } finally {
    clearTimeout(timer)
  }
}

// 聊天会话 Store：会话列表 + 消息流 + SSE 流式接收
export const useChatStore = defineStore('chat', {
  state: () => ({
    sessions: [],            // [{ sid, title, created, updated }]
    activeSid: null,
    messages: [],            // [{ role: 'user'|'assistant', content }]
    streaming: false,
    abortCtrl: null,         // 停止生成用
    status: { chat_ready: false, loading: false, chat_error: null },
  }),

  getters: {
    activeTitle: (s) => s.sessions.find((x) => x.sid === s.activeSid)?.title || '新对话',
  },

  actions: {
    async fetchStatus() {
      try {
        const r = await fetchTimeout('/api/status')
        this.status = await r.json()
      } catch { /* 服务未启动 */ }
    },

    async loadSessions() {
      try {
        const r = await fetchTimeout('/api/chat/list')
        const data = await r.json()
        this.sessions = data.sessions || []
      } catch {
        this.sessions = []
      }
    },

    async newSession() {
      const r = await fetchTimeout('/api/chat/new', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
      })
      const data = await r.json()
      this.activeSid = data.session_id
      this.messages = []
      this.loadSessions()   // 不阻塞主流程
      return data.session_id
    },

    async openSession(sid) {
      this.activeSid = sid
      try {
        const r = await fetchTimeout('/api/chat/history', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sid }),
        })
        const data = await r.json()
        this.messages = data.messages || []
      } catch {
        this.messages = []
      }
    },

    async deleteSession(sid) {
      try {
        await fetchTimeout('/api/chat/delete', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sid }),
        })
        await this.loadSessions()
      } catch { /* 忽略 */ }
      if (this.activeSid === sid) {
        this.activeSid = null
        this.messages = []
      }
    },

    async clearConversation() {
      if (!this.activeSid) return
      try {
        await fetchTimeout('/api/chat/clear', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: this.activeSid }),
        })
        this.messages = []
        await this.loadSessions()
      } catch { /* 忽略 */ }
    },

    // 停止当前生成
    stop() {
      if (this.abortCtrl) this.abortCtrl.abort()
    },

    // SSE 流式发送消息：逐块追加到当前助手消息
    async sendMessage(text) {
      if (this.streaming) return
      if (!this.activeSid) await this.newSession()
      const sid = this.activeSid
      if (!sid) return
      this.messages.push({ role: 'user', content: text })
      this.messages.push({ role: 'assistant', content: '' })
      this.streaming = true

      const ctrl = new AbortController()
      this.abortCtrl = ctrl
      try {
        const r = await fetch('/api/chat/send', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sid, message: text }),
          signal: ctrl.signal,
        })
        if (r.status === 503) {
          const err = await r.json()
          this.messages.pop()
          this.messages.push({ role: 'assistant', content: `⚠️ ${err.message || '模型尚未就绪，请稍候重试'}` })
          return
        }
        if (!r.ok) {
          const err = await r.json().catch(() => ({}))
          this.messages.pop()
          this.messages.push({ role: 'assistant', content: `❌ ${err.error || '请求失败'}` })
          return
        }

        const reader = r.body.getReader()
        const decoder = new TextDecoder('utf-8')
        let buf = ''
        const last = this.messages[this.messages.length - 1]

        for (;;) {
          const { done, value } = await reader.read()
          if (done) break
          buf += decoder.decode(value, { stream: true })
          let idx
          while ((idx = buf.indexOf('\n\n')) >= 0) {
            const raw = buf.slice(0, idx)
            buf = buf.slice(idx + 2)
            if (!raw.startsWith('data: ')) continue
            let evt
            try { evt = JSON.parse(raw.slice(6)) } catch { continue }
            if (evt.delta) last.content += evt.delta
            else if (evt.done) { this.loadSessions() }
            else if (evt.error) { last.content += `\n\n❌ ${evt.error}` }
          }
        }
      } catch (e) {
        if (e.name === 'AbortError') {
          // 用户手动停止：保留已生成内容，清空空消息
          const last = this.messages[this.messages.length - 1]
          if (!last.content) this.messages.pop()
          return
        }
        this.messages.pop()
        this.messages.push({ role: 'assistant', content: `❌ 连接失败：${e.message}` })
      } finally {
        this.streaming = false
        this.abortCtrl = null
      }
    },
  },
})
