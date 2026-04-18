<template>
  <TeacherLayout>
    <div class="page-card teacher-card">
      <div class="page-title">讲稿生成</div>

      <el-form :model="form" label-width="110px">
        <el-form-item label="解析任务编号">
          <el-input v-model="form.parseId" readonly />
        </el-form-item>

        <el-form-item label="讲解风格">
          <el-radio-group v-model="form.teachingStyle">
            <el-radio label="standard">标准</el-radio>
            <el-radio label="detailed">详细</el-radio>
            <el-radio label="concise">简洁</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="讲解语速">
          <el-radio-group v-model="form.speechSpeed">
            <el-radio label="slow">慢</el-radio>
            <el-radio label="normal">正常</el-radio>
            <el-radio label="fast">快</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="开场白">
          <el-input
            v-model="form.customOpening"
            type="textarea"
            :rows="3"
            placeholder="可选。生成首章时会自然融入这段开场白。"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleGenerate">
            开始生成
          </el-button>
          <el-button v-if="canOpenLastResult" @click="openLastResult">
            打开上次结果
          </el-button>
        </el-form-item>
      </el-form>

      <div v-if="hasLastTask" class="status-panel">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="状态">{{ taskStatusLabel }}</el-descriptions-item>
          <el-descriptions-item label="总耗时">{{ elapsedLabel }}</el-descriptions-item>
          <el-descriptions-item label="脚本编号">{{ taskSnapshot.scriptId || '-' }}</el-descriptions-item>
          <el-descriptions-item label="进度">{{ progressLabel }}</el-descriptions-item>
          <el-descriptions-item label="当前章节">{{ taskSnapshot.currentSectionName || '-' }}</el-descriptions-item>
          <el-descriptions-item label="解析任务编号">{{ taskSnapshot.parseId || '-' }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <Loading :visible="loading" :text="`正在启动脚本生成，已处理 ${elapsedLabel}`" />

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
const taskStatusLabel = computed(() => {
  const statusMap = {
    pending: '待开始',
    running: '生成中',
    completed: '已完成',
    failed: '失败',
    interrupted: '已中断',
    success: '已完成'
  }
  return statusMap[taskSnapshot.value.status] || '空闲'
})
const progressLabel = computed(() => {
  const completed = Number(taskSnapshot.value.completedSections || 0)
  const total = Number(taskSnapshot.value.totalSections || 0)
  return total > 0 ? `${completed}/${total}` : '-'
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
  persistTaskSnapshot({ lastPage: TASK_PAGE })
  syncElapsed()
  window.addEventListener('beforeunload', persistBeforeUnload)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  if (taskSnapshot.value.status === 'running') {
    startTimer()
  }
})

onBeforeUnmount(() => {
  stopTimer()
  window.removeEventListener('beforeunload', persistBeforeUnload)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  persistTaskSnapshot({ status: taskSnapshot.value.status })
})

async function handleGenerate() {
  if (!form.value.parseId) {
    ElMessage.warning('请先完成课件解析。')
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
    generationStatus: 'running',
    startedAt,
    finishedAt: '',
    scriptId: '',
    scriptStructure: [],
    version: 1,
    completedSections: 0,
    totalSections: 0,
    currentSectionId: '',
    currentSectionName: '',
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

    const data = res.data || {}
    const runtimeStatus = normalizeGenerationStatus(data.generationStatus)
    const result = {
      ...data,
      parseId: form.value.parseId,
      teachingStyle: form.value.teachingStyle,
      speechSpeed: form.value.speechSpeed,
      customOpening: form.value.customOpening,
      status: runtimeStatus,
      generationStatus: data.generationStatus || runtimeStatus,
      startedAt: data.startedAt || startedAt,
      finishedAt: data.finishedAt || ''
    }

    saveScriptResult(result)
    taskSnapshot.value = patchScriptTask({
      ...result,
      status: runtimeStatus,
      lastPage: 'script-edit'
    })
    router.push('/teacher/script-edit')
  } catch (error) {
    const finishedAt = new Date().toISOString()
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || '脚本生成任务启动失败'
    taskSnapshot.value = patchScriptTask({
      parseId: form.value.parseId,
      teachingStyle: form.value.teachingStyle,
      speechSpeed: form.value.speechSpeed,
      customOpening: form.value.customOpening,
      status: 'failed',
      generationStatus: 'failed',
      startedAt,
      finishedAt,
      errorCode: errorCode.value,
      errorMsg: errorMsg.value,
      lastPage: TASK_PAGE
    })
    stopTimer()
  } finally {
    loading.value = false
    syncElapsed()
  }
}

function openLastResult() {
  if (!canOpenLastResult.value) {
    ElMessage.warning('暂无可打开的脚本结果')
    return
  }
  router.push('/teacher/script-edit')
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
  persistTaskSnapshot({ status: taskSnapshot.value.status })
}

function handleVisibilityChange() {
  if (document.visibilityState === 'hidden') {
    persistBeforeUnload()
  }
}

function normalizeGenerationStatus(status) {
  if (status === 'completed') {
    return 'completed'
  }
  if (status === 'failed') {
    return 'failed'
  }
  if (status === 'interrupted') {
    return 'interrupted'
  }
  return 'running'
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
    return `${hours}小时 ${String(minutes).padStart(2, '0')}分 ${String(seconds).padStart(2, '0')}秒`
  }

  return `${String(minutes).padStart(2, '0')}分 ${String(seconds).padStart(2, '0')}秒`
}
</script>

<style scoped>
.status-panel {
  margin-top: 16px;
}
</style>
