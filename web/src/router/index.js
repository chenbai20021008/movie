import { createRouter, createWebHashHistory } from 'vue-router'
import Recommend from '../views/Recommend.vue'

/**
 * 用 hash 路由：答辩现场无论是 vite dev、vite preview，还是别人用
 * 最简单的静态服务器（python -m http.server / nginx）托管 dist，
 * 刷新页面都不会 404，减少演示时的意外。
 */
const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'recommend', component: Recommend, meta: { title: '推荐展示' } },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('../views/Dashboard.vue'),
      meta: { title: '指标看板' },
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.afterEach((to) => {
  document.title = to.meta?.title ? `${to.meta.title} · 电影推荐系统` : '电影推荐系统 · 服务化演示'
})

export default router
