import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
// 本地化字体（Outfit 标题 / Work Sans 正文，设计系统推荐，无需 Google Fonts）
import '@fontsource/outfit/400.css'
import '@fontsource/outfit/500.css'
import '@fontsource/outfit/600.css'
import '@fontsource/outfit/700.css'
import '@fontsource/work-sans/400.css'
import '@fontsource/work-sans/500.css'
import '@fontsource/work-sans/600.css'
import './styles/tokens.css'
import './styles/base.css'

createApp(App).use(createPinia()).use(router).mount('#app')
