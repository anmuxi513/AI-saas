import { createRouter, createWebHashHistory } from 'vue-router'

// 使用 hash 模式：构建产物可直接被门户服务（6666）静态托管
const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/chat' },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('../views/ChatView.vue'),
    },
    {
      path: '/inference',
      name: 'inference',
      component: () => import('../views/InferenceView.vue'),
    },
    { path: '/:pathMatch(.*)*', redirect: '/chat' },
  ],
})

export default router
