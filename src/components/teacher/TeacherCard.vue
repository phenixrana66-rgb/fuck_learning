<template>
  <div class="teacher-card" :class="{ 'is-hover': hover }">
    <div v-if="$slots.header || title" class="teacher-card-header">
      <slot name="header">
        <span class="teacher-card-title">{{ title }}</span>
      </slot>
      <div class="teacher-card-extra">
        <slot name="extra"></slot>
      </div>
    </div>
    <div class="teacher-card-body" :style="bodyStyle">
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: String,
  bodyStyle: [Object, String],
  hover: Boolean
})
</script>

<style scoped>
.teacher-card {
  background: var(--app-card-bg, #fff);
  border-radius: var(--app-radius-large, 16px);
  box-shadow: var(--app-shadow-light, 0 6px 20px rgba(31, 35, 41, 0.06));
  overflow: hidden;
  margin-bottom: 16px;
  transition: all 0.3s ease;
}

.teacher-card.is-hover:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(31, 35, 41, 0.1);
}

.teacher-card-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--app-border-color-lighter, #ebeef5);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.teacher-card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--app-text-primary, #303133);
}

.teacher-card-body {
  padding: 20px;
}
</style>
