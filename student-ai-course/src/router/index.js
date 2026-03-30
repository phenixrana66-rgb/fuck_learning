import { createRouter, createWebHistory } from 'vue-router'
import { savePlatformToken } from '@/utils/platform'

const routes = [
  {
    path: '/',
    redirect: '/student/home'
  },
  {
    path: '/student/home',
    name: 'StudentHome',
    component: () => import('@/views/student/Home.vue')
  },
  {
    path: '/student/player/:lessonId',
    name: 'StudentPlayer',
    component: () => import('@/views/student/Player.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  if (to.query.token) {
    savePlatformToken(to.query.token)
  }
  next()
})

export default router
