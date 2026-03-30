import { createRouter, createWebHistory } from 'vue-router'
import { getPlatformToken, savePlatformToken } from '@/utils/platform'

const routes = [
  {
    path: '/',
    redirect: '/teacher/login'
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
  if (typeof to.query.token === 'string' && to.query.token) {
    savePlatformToken(to.query.token)
  }

  if (!to.path.startsWith('/teacher')) {
    next()
    return
  }

  if (to.path === '/teacher/login') {
    next()
    return
  }

  if (!getPlatformToken()) {
    next('/teacher/login')
    return
  }

  next()
})

export default router
