<template>
  <div class="loading-box" v-if="visible">
    <el-icon class="is-loading" :size="24"><Loading /></el-icon>
    <div class="loading-text">{{ text || '处理中，请稍候...' }}</div>
    <el-progress
      v-if="showProgress"
      :percentage="percentage"
      :stroke-width="10"
      striped
      striped-flow
      style="width: 280px; margin-top: 12px"
    />
  </div>
</template>

<script setup>
import { Loading } from '@element-plus/icons-vue'

defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  text: {
    type: String,
    default: ''
  },
  percentage: {
    type: Number,
    default: 0
  },
  showProgress: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.loading-box {
  width: 100%;
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
}
.loading-text {
  margin-top: 10px;
  color: #606266;
}
</style>