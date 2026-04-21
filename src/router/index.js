import { createRouter, createWebHistory } from 'vue-router'
import { getTeacherPlatformToken, saveTeacherPlatformToken, saveStudentPlatformToken } from '@/utils/platform'

const routes = [
  {
    path: '/',
    name: 'HomePortal',
    component: () => import('@/views/HomePortal.vue')
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
    path: '/student/knowledge-learning/:lessonId/:unitId/:chapterId',
    name: 'StudentKnowledgeLearning',
    component: () => import('@/views/student/KnowledgeLearning.vue')
  },
  {
    path: '/student/slide-learning/:lessonId/:sectionId',
    name: 'StudentSlideLearning',
    component: () => import('@/views/student/SlideLearning.vue')
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
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    }
    if (String(to.name || '').startsWith('Student') || String(from.name || '').startsWith('Student')) {
      return false
    }
    return {
      left: 0,
      top: 0
    }
  }
})

router.beforeEach((to, from, next) => {
  if (typeof to.query.token === 'string' && to.query.token) {
    if (to.path.startsWith('/teacher')) {
      saveTeacherPlatformToken(to.query.token)
    } else if (to.path.startsWith('/student')) {
      saveStudentPlatformToken(to.query.token)
    }
  }

  if (!to.path.startsWith('/teacher')) {
    next()
    return
  }

  if (to.path === '/teacher/login') {
    next()
    return
  }

  if (!getTeacherPlatformToken()) {
    next('/teacher/login')
    return
  }

  next()
})

export default router
