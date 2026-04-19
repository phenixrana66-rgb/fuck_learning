<template>
  <router-view v-slot="{ Component, route }">
    <keep-alive>
      <component :is="Component" :key="resolveRouteCacheKey(route)" />
    </keep-alive>
  </router-view>
</template>

<script setup>
function resolveRouteCacheKey(route) {
  if (route.name === 'StudentPlayer') {
    return `StudentPlayer:${route.params.lessonId || ''}`
  }
  if (route.name === 'StudentKnowledgeLearning') {
    return `StudentKnowledgeLearning:${route.params.lessonId || ''}:${route.params.sectionId || ''}`
  }
  return String(route.name || route.path || '')
}
</script>
