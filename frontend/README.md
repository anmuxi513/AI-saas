# AI 训练平台 · 前端

企业级 AI 模型训练平台前端界面（Vue 3），包含**聊天对话**与**模型识别**两大模块。

> 视觉规范由 [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) 设计系统生成（Minimalism & Swiss Style）

## ✨ 功能

| 模块 | 说明 |
|---|---|
| 💬 聊天对话（主界面） | 本地 Qwen2.5-0.5B 对话：SSE 流式输出、多会话管理（新建/搜索/分组/删除）、Markdown 渲染、复制回复、停止生成、快捷键（`Esc` 停止、`/` 聚焦） |
| 🔍 模型识别（切换模块） | MNIST 手写数字识别（Canvas 手写板 + 概率条）、EuroSAT 遥感地物分类（上传图片 + Top-3 结果） |

## 🛠 技术栈

- **Vue 3.5** + **Vite** + **vue-router**（hash 模式）+ **Pinia**
- **marked** + **DOMPurify**（Markdown 渲染与消毒）
- **@fontsource/outfit** + **@fontsource/work-sans**（本地化字体，无需 Google Fonts）
- 样式：CSS 变量设计令牌（Design Tokens）+ 响应式布局

## 🚀 快速开始

```bash
npm install
npm run dev        # 开发服务器 http://localhost:5174
npm run build      # 构建产物 → dist/
```

> 国内网络：`.npmrc` 已配置 npmmirror 镜像。

## 🔌 后端对接

前端通过 `/api/*` 与后端通信（开发时由 Vite 代理到 `localhost:6660`），
配套后端为统一门户服务（Python，单端口 6660）：

| API | 说明 |
|---|---|
| `POST /api/chat/send` | 聊天 SSE 流式（`text/event-stream`） |
| `POST /api/chat/new` `GET /api/chat/list` `POST /api/chat/history` `POST /api/chat/delete` `POST /api/chat/clear` | 会话管理 |
| `GET /api/status` | 聊天模型加载状态 |
| `POST /api/mnist/predict` | MNIST 推理 `{pixels:[784]}` |
| `POST /api/eurosat/predict` | EuroSAT 推理 `{image: base64}` |

构建产物 `dist/` 由后端直接托管（`http://localhost:6660`），无需单独部署。

## 📁 目录结构

```
src/
├── App.vue              # 布局（深色侧边栏 + 顶栏）
├── views/
│   ├── ChatView.vue     # 聊天对话（主界面）
│   └── InferenceView.vue# 模型识别（切换模块）
├── components/
│   ├── ChatMessage.vue  # 消息气泡（Markdown + 复制）
│   ├── MnistPanel.vue   # MNIST 手写板
│   └── EurosatPanel.vue # EuroSAT 上传识别
├── stores/chat.js       # 聊天状态（Pinia + SSE）
├── router/index.js      # 路由（hash 模式）
└── styles/
    ├── tokens.css       # 设计令牌（颜色/字体/间距/阴影）
    └── base.css         # 基础组件样式
```

## 📄 License

MIT
