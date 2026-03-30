import { createRouter, createWebHistory } from 'vue-router'
import { getPlatformToken } from '@/utils/platform'

const routes = [
  {
    path: '/',
    redirect: '/teacher/login'
  },
  {
    path: '/teacher/login',
    name: 'TeacherLogin',
    component: () => import('@/views/teacher/Login.vue')
  },
  {
    path: '/teacher/lesson-manage',
    name: 'LessonManage',
    component: () => import('@/views/teacher/LessonManage.vue')
  },
  {
    path: '/teacher/course-parse',
    name: 'CourseParse',
    component: () => import('@/views/teacher/CourseParse.vue')
  },
  {
    path: '/teacher/script-generate',
    name: 'ScriptGenerate',
    component: () => import('@/views/teacher/ScriptGenerate.vue')
  },
  {
    path: '/teacher/script-edit',
    name: 'ScriptEdit',
    component: () => import('@/views/teacher/ScriptEdit.vue')
  },
  {
    path: '/teacher/audio-generate',
    name: 'AudioGenerate',
    component: () => import('@/views/teacher/AudioGenerate.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  if (to.path === '/teacher/login') {
    next()
    return
  }

  const token = getPlatformToken()
  if (!token) {
    next('/teacher/login')
    return
  }

  next()
})

export default router
