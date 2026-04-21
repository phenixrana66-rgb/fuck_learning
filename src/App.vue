<template>
  <router-view v-slot="{ Component, route }">
    <transition :name="pageTransitionName" mode="out-in" appear>
      <keep-alive>
        <component :is="Component" :key="resolveRouteCacheKey(route)" />
      </keep-alive>
    </transition>
  </router-view>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const router = useRouter()
const route = useRoute()
const pageTransitionName = ref('app-page-fade')
let removeRouteGuard = null
const STATIC_TOPBAR_ROUTE_NAMES = new Set(['StudentKnowledgeLearning', 'StudentSlideLearning'])

function resolveStudentLearningDepth(routeName) {
  if (routeName === 'StudentPlayer') return 1
  if (routeName === 'StudentKnowledgeLearning') return 2
  if (routeName === 'StudentSlideLearning') return 3
  return 0
}

function resolvePageTransitionName(to, from) {
  const toName = String(to?.name || '')
  const fromName = String(from?.name || '')
  const toDepth = resolveStudentLearningDepth(toName)
  const fromDepth = resolveStudentLearningDepth(fromName)

  if (STATIC_TOPBAR_ROUTE_NAMES.has(toName) && STATIC_TOPBAR_ROUTE_NAMES.has(fromName)) {
    return 'student-shell-static'
  }

  if (toDepth && fromDepth) {
    if (toDepth > fromDepth) return 'student-flow-forward'
    if (toDepth < fromDepth) return 'student-flow-backward'
  }

  if (toDepth || fromDepth) {
    return 'student-flow-fade'
  }

  return 'app-page-fade'
}

function resolveRouteCacheKey(route) {
  if (route.name === 'StudentPlayer') {
    return `StudentPlayer:${route.params.lessonId || ''}`
  }
  if (route.name === 'StudentKnowledgeLearning') {
    return `StudentKnowledgeLearning:${route.params.lessonId || ''}:${route.params.unitId || ''}:${route.params.chapterId || ''}`
  }
  if (route.name === 'StudentSlideLearning') {
    return `StudentSlideLearning:${route.params.lessonId || ''}:${route.params.sectionId || ''}`
  }
  return String(route.name || route.path || '')
}

const scrollbarTimers = new WeakMap()

function clearScrollbarTimer(target) {
  const timer = scrollbarTimers.get(target)
  if (timer) {
    window.clearTimeout(timer)
  }
}

function showScrollbar(target) {
  if (!target) return
  clearScrollbarTimer(target)
  target.classList.add('scrollbar-active')
  const timer = window.setTimeout(() => {
    target.classList.remove('scrollbar-active')
    scrollbarTimers.delete(target)
  }, 3000)
  scrollbarTimers.set(target, timer)
}

function resolveScrollbarTarget(sourceTarget) {
  if (!(sourceTarget instanceof Element)) {
    return null
  }
  return sourceTarget.closest('.app-scrollable')
}

function handleScrollbarInteraction(event) {
  const target = resolveScrollbarTarget(event.target)
  if (target) {
    showScrollbar(target)
  }
}

onMounted(() => {
  pageTransitionName.value = resolvePageTransitionName(route, {})
  removeRouteGuard = router.beforeEach((to, from, next) => {
    pageTransitionName.value = resolvePageTransitionName(to, from)
    next()
  })
  document.addEventListener('scroll', handleScrollbarInteraction, true)
  document.addEventListener('wheel', handleScrollbarInteraction, { capture: true, passive: true })
  document.addEventListener('touchmove', handleScrollbarInteraction, { capture: true, passive: true })
  document.addEventListener('pointerdown', handleScrollbarInteraction, true)
})

onBeforeUnmount(() => {
  removeRouteGuard?.()
  document.removeEventListener('scroll', handleScrollbarInteraction, true)
  document.removeEventListener('wheel', handleScrollbarInteraction, true)
  document.removeEventListener('touchmove', handleScrollbarInteraction, true)
  document.removeEventListener('pointerdown', handleScrollbarInteraction, true)
})
</script>

<style>
.app-page-fade-enter-active,
.app-page-fade-leave-active,
.student-flow-forward-enter-active,
.student-flow-forward-leave-active,
.student-flow-backward-enter-active,
.student-flow-backward-leave-active,
.student-flow-fade-enter-active,
.student-flow-fade-leave-active,
.student-shell-static-enter-active,
.student-shell-static-leave-active {
  will-change: opacity, filter;
}

.app-page-fade-enter-active,
.app-page-fade-leave-active,
.student-flow-fade-enter-active,
.student-flow-fade-leave-active {
  transition:
    opacity 0.28s ease,
    filter 0.34s ease;
}

.student-flow-forward-enter-active,
.student-flow-forward-leave-active,
.student-flow-backward-enter-active,
.student-flow-backward-leave-active {
  transition:
    opacity 0.32s ease,
    filter 0.42s ease;
}

.student-shell-static-enter-active,
.student-shell-static-leave-active {
  transition: none;
}

.app-page-fade-enter-from,
.app-page-fade-leave-to,
.student-flow-fade-enter-from,
.student-flow-fade-leave-to {
  opacity: 0;
  filter: blur(6px);
}

.student-flow-forward-enter-from,
.student-flow-backward-leave-to {
  opacity: 0;
  filter: blur(8px);
}

.student-flow-forward-leave-to,
.student-flow-backward-enter-from {
  opacity: 0;
  filter: blur(7px);
}
</style>
