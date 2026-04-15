<template>
  <TeacherLayout>
    <div class="page-card">
      <div class="page-title">脚本生成</div>

      <el-form :model="form" label-width="110px">
        <el-form-item label="parseId">
          <el-input v-model="form.parseId" readonly />
        </el-form-item>

        <el-form-item label="Style">
          <el-radio-group v-model="form.teachingStyle">
            <el-radio label="standard">标准</el-radio>
            <el-radio label="detailed">详细</el-radio>
            <el-radio label="concise">简洁</el-radio>
          </el-radio-group>
          <div class="light-tip" style="margin-top: 8px;">
            标准版适合常规教学，详细版适合深入讲解，简洁版适合短时课程指导.
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleGenerate">
            开始生成脚本
          </el-button>
          <el-button v-if="canOpenLastResult" @click="openLastResult">
            打开上次结果
          </el-button>
        </el-form-item>
      </el-form>

      <div v-if="isRunning" class="status-panel">
        <el-alert type="info" :closable="false" show-icon>
          <template #title>
            脚本生成中，已用时间： {{ elapsedLabel }}.
          </template>
        </el-alert>
      </div>

      <div v-else-if="hasLastTask" class="status-panel">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="结果">{{ taskStatusLabel }}</el-descriptions-item>
          <el-descriptions-item label="处理用时">{{ elapsedLabel }}</el-descriptions-item>
          <el-descriptions-item label="解析任务编号">{{ taskSnapshot.parseId || '-' }}</el-descriptions-item>
          <el-descriptions-item label="脚本编号">{{ taskSnapshot.scriptId || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div class="toolbar compact">
          <el-button v-if="canOpenLastResult" type="success" @click="openLastResult">加载上次结果</el-button>
          <el-button @click="useLastTask">使用上次的参数</el-button>
        </div>
      </div>

      <Loading :visible="loading" :text="`Generating script... ${elapsedLabel}`" />

      <ErrorTip
        v-if="errorCode"
        :code="errorCode"
        :message="errorMsg"
        @retry="handleGenerate"
      />
    </div>
  </TeacherLayout>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import TeacherLayout from '@/components/teacher/TeacherLayout.vue'
import Loading from '@/components/teacher/Loading.vue'
import ErrorTip from '@/components/teacher/ErrorTip.vue'
import { generateScript } from '@/api/teacher'
import { getParseResult, getScriptTask, patchScriptTask, saveScriptResult } from '@/utils/platform'

const TASK_PAGE = 'script-generate'
const router = useRouter()
const parseResult = getParseResult()
const cachedTask = getScriptTask()

const form = ref({
  parseId: cachedTask.parseId || parseResult.parseId || '',
  teachingStyle: cachedTask.teachingStyle || 'standard',
  speechSpeed: cachedTask.speechSpeed || 'normal',
  customOpening: cachedTask.customOpening || ''
})

const loading = ref(false)
const errorCode = ref('')
const errorMsg = ref('')
const taskSnapshot = ref({ ...cachedTask })
const elapsedSeconds = ref(0)
let timerId = null

const hasLastTask = computed(() => Boolean(taskSnapshot.value.parseId || taskSnapshot.value.scriptId))
const canOpenLastResult = computed(() => Boolean(taskSnapshot.value.scriptId))
const isRunning = computed(() => taskSnapshot.value.status === 'running')
const taskStatusLabel = computed(() => {
  const statusMap = {
    running: 'Running',
    interrupted: 'Interrupted',
    success: 'Success',
    failed: 'Failed'
  }
  return statusMap[taskSnapshot.value.status] || 'Idle'
})
const elapsedLabel = computed(() => formatElapsed(elapsedSeconds.value))

watch(
  form,
  () => {
    persistTaskSnapshot()
  },
  { deep: true }
)

onMounted(() => {
  const restoredTask = getScriptTask()
  if (restoredTask.status === 'running') {
    taskSnapshot.value = patchScriptTask({
      status: 'interrupted',
      lastPage: TASK_PAGE
    })
    errorMsg.value = 'The previous script generation was interrupted. Parameters have been restored.'
  } else {
    persistTaskSnapshot({ lastPage: TASK_PAGE })
  }

  syncElapsed()
  window.addEventListener('beforeunload', persistBeforeUnload)
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onBeforeUnmount(() => {
  stopTimer()
  window.removeEventListener('beforeunload', persistBeforeUnload)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  persistTaskSnapshot({ status: loading.value ? 'running' : taskSnapshot.value.status })
})

async function handleGenerate() {
  if (!form.value.parseId) {
    ElMessage.warning('Complete courseware parsing first')
    return
  }

  const startedAt = new Date().toISOString()
  loading.value = true
  errorCode.value = ''
  errorMsg.value = ''
  taskSnapshot.value = patchScriptTask({
    parseId: form.value.parseId,
    teachingStyle: form.value.teachingStyle,
    speechSpeed: form.value.speechSpeed,
    customOpening: form.value.customOpening,
    status: 'running',
    startedAt,
    finishedAt: '',
    scriptId: '',
    scriptStructure: [],
    version: 1,
    savedAt: '',
    errorCode: '',
    errorMsg: '',
    lastPage: TASK_PAGE
  })
  startTimer()

  try {
    const res = await generateScript({
      parseId: form.value.parseId,
      teachingStyle: form.value.teachingStyle,
      speechSpeed: form.value.speechSpeed,
      customOpening: form.value.customOpening
    })

    const finishedAt = new Date().toISOString()
    const data = res.data || {}
    const result = {
      ...data,
      parseId: form.value.parseId,
      teachingStyle: form.value.teachingStyle,
      speechSpeed: form.value.speechSpeed,
      customOpening: form.value.customOpening,
      status: 'success',
      startedAt,
      finishedAt
    }

    saveScriptResult(result)
    taskSnapshot.value = patchScriptTask({
      ...result,
      status: 'success',
      lastPage: 'script-edit'
    })
    router.push('/teacher/script-edit')
  } catch (error) {
    const finishedAt = new Date().toISOString()
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || 'Failed to generate script'
    taskSnapshot.value = patchScriptTask({
      parseId: form.value.parseId,
      teachingStyle: form.value.teachingStyle,
      speechSpeed: form.value.speechSpeed,
      customOpening: form.value.customOpening,
      status: 'failed',
      startedAt,
      finishedAt,
      errorCode: errorCode.value,
      errorMsg: errorMsg.value,
      lastPage: TASK_PAGE
    })
  } finally {
    loading.value = false
    stopTimer()
    syncElapsed()
  }
}

function openLastResult() {
  if (!canOpenLastResult.value) {
    ElMessage.warning('No previous script result is available')
    return
  }
  router.push('/teacher/script-edit')
}

function useLastTask() {
  const lastTask = getScriptTask()
  form.value = {
    parseId: lastTask.parseId || parseResult.parseId || '',
    teachingStyle: lastTask.teachingStyle || 'standard',
    speechSpeed: lastTask.speechSpeed || 'normal',
    customOpening: lastTask.customOpening || ''
  }
  taskSnapshot.value = lastTask
  syncElapsed()
}

function persistTaskSnapshot(extra = {}) {
  taskSnapshot.value = patchScriptTask({
    parseId: form.value.parseId,
    teachingStyle: form.value.teachingStyle,
    speechSpeed: form.value.speechSpeed,
    customOpening: form.value.customOpening,
    lastPage: TASK_PAGE,
    ...(extra || {})
  })
  syncElapsed()
}

function persistBeforeUnload() {
  persistTaskSnapshot({ status: loading.value ? 'running' : taskSnapshot.value.status })
}

function handleVisibilityChange() {
  if (document.visibilityState === 'hidden') {
    persistBeforeUnload()
  }
}

function startTimer() {
  stopTimer()
  syncElapsed()
  timerId = window.setInterval(syncElapsed, 1000)
}

function stopTimer() {
  if (timerId) {
    window.clearInterval(timerId)
    timerId = null
  }
}

function syncElapsed() {
  elapsedSeconds.value = getElapsedSeconds(taskSnapshot.value.startedAt, taskSnapshot.value.finishedAt, taskSnapshot.value.status)
}

function getElapsedSeconds(startedAt, finishedAt, status) {
  if (!startedAt) {
    return 0
  }

  const startMs = new Date(startedAt).getTime()
  if (Number.isNaN(startMs)) {
    return 0
  }

  const endCandidate = status === 'running' ? Date.now() : new Date(finishedAt || Date.now()).getTime()
  const endMs = Number.isNaN(endCandidate) ? Date.now() : endCandidate
  return Math.max(0, Math.floor((endMs - startMs) / 1000))
}

function formatElapsed(totalSeconds) {
  const safeSeconds = Math.max(0, Number(totalSeconds) || 0)
  const hours = Math.floor(safeSeconds / 3600)
  const minutes = Math.floor((safeSeconds % 3600) / 60)
  const seconds = safeSeconds % 60

  if (hours > 0) {
    return `${hours}h ${String(minutes).padStart(2, '0')}m ${String(seconds).padStart(2, '0')}s`
  }

  return `${String(minutes).padStart(2, '0')}m ${String(seconds).padStart(2, '0')}s`
}
</script>

<style scoped>
.status-panel {
  margin-top: 16px;
}

.toolbar.compact {
  margin-top: 16px;
}
</style>
