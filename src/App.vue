<template>
  <router-view v-slot="{ Component, route }">
    <keep-alive>
      <component :is="Component" :key="resolveRouteCacheKey(route)" />
    </keep-alive>
  </router-view>
</template>

<script setup>
import { onBeforeUnmount, onMounted } from 'vue'

function resolveRouteCacheKey(route) {
  if (route.name === 'StudentPlayer') {
    return `StudentPlayer:${route.params.lessonId || ''}`
  }
  if (route.name === 'StudentKnowledgeLearning') {
    return `StudentKnowledgeLearning:${route.params.lessonId || ''}:${route.params.sectionId || ''}`
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
  document.addEventListener('scroll', handleScrollbarInteraction, true)
  document.addEventListener('wheel', handleScrollbarInteraction, { capture: true, passive: true })
  document.addEventListener('touchmove', handleScrollbarInteraction, { capture: true, passive: true })
  document.addEventListener('pointerdown', handleScrollbarInteraction, true)
})

onBeforeUnmount(() => {
  document.removeEventListener('scroll', handleScrollbarInteraction, true)
  document.removeEventListener('wheel', handleScrollbarInteraction, true)
  document.removeEventListener('touchmove', handleScrollbarInteraction, true)
  document.removeEventListener('pointerdown', handleScrollbarInteraction, true)
})
</script>
