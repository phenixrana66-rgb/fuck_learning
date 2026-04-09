<template>
  <el-result
    :icon="icon"
    :title="title"
    :sub-title="subTitle"
  >
    <template #extra>
      <el-button type="primary" @click="$emit('retry')">重试</el-button>
    </template>
  </el-result>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  code: {
    type: [String, Number],
    default: ''
  },
  message: {
    type: String,
    default: ''
  }
})

defineEmits(['retry'])

const title = computed(() => {
  const map = {
    400: '400 参数错误',
    401: '401 鉴权失败',
    403: '403 无权限访问',
    404: '404 接口不存在',
    500: '500 服务异常'
  }
  return map[props.code] || '请求异常'
})

const subTitle = computed(() => props.message || '请检查接口参数或稍后重试')

const icon = computed(() => {
  if ([400, 401, 403, 404, 500].includes(Number(props.code))) return 'error'
  return 'warning'
})
</script>