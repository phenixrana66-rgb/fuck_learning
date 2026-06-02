<template>
  <TeacherLayout>
    <div class="page-container">
      <!-- Left Section: Configuration -->
      <div class="config-section">
        <div class="page-card teacher-card">
          <div class="page-title">讲稿生成</div>

          <el-form :model="form" label-width="110px">
            <el-form-item label="当前课程">
              <el-input :model-value="currentCourse.courseName || '-'" readonly />
            </el-form-item>

            <el-form-item label="当前章节">
              <el-input :model-value="chapterInfo.chapterName || '-'" readonly />
            </el-form-item>

            <el-form-item label="解析版本">
              <el-select
                v-model="form.parseId"
                class="full-width"
                placeholder="请选择已完成解析的课件版本"
                :loading="loadingHistory"
                :disabled="loading || taskSnapshot.status === 'running'"
                @change="handleParseChange"
              >
                <el-option
                  v-for="item in parseOptions"
                  :key="item.parseId"
                  :label="item.label"
                  :value="item.parseId"
                  :disabled="item.taskStatus !== 'completed'"
                />
              </el-select>
            </el-form-item>

            <el-form-item v-if="selectedParseMeta" label="当前课件">
              <div class="version-summary">
                <div>文件：{{ selectedParseMeta.fileName }}</div>
                <div>版本：V{{ selectedParseMeta.versionNo }} · {{ selectedParseMeta.fileType.toUpperCase() }}</div>
                <div>状态：{{ parseStatusText(selectedParseMeta.taskStatus) }}</div>
              </div>
            </el-form-item>

            <el-form-item label="讲解风格">
              <el-radio-group v-model="form.teachingStyle" class="card-radio-group" :disabled="loading || taskSnapshot.status === 'running'">
                <el-radio v-for="opt in styleOptions" :key="opt.value" :label="opt.value" class="card-radio">
                  <div class="card-radio-content">
                    <el-icon class="card-icon"><component :is="opt.icon" /></el-icon>
                    <div class="card-info">
                      <div class="card-label">{{ opt.label }}</div>
                      <div class="card-desc">{{ opt.desc }}</div>
                    </div>
                  </div>
                </el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="讲解语速">
              <el-radio-group v-model="form.speechSpeed" class="card-radio-group" :disabled="loading || taskSnapshot.status === 'running'">
                <el-radio v-for="opt in speedOptions" :key="opt.value" :label="opt.value" class="card-radio">
                  <div class="card-radio-content">
                    <el-icon class="card-icon"><component :is="opt.icon" /></el-icon>
                    <div class="card-info">
                      <div class="card-label">{{ opt.label }}</div>
                      <div class="card-desc">{{ opt.desc }}</div>
                    </div>
                  </div>
                </el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="开场白">
              <el-input
                v-model="form.customOpening"
                type="textarea"
                :rows="3"
                placeholder="可选。生成首章时会自然融入这段开场白。"
                :disabled="loading || taskSnapshot.status === 'running'"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loading" @click="handleGenerate">
                基于当前解析生成讲稿
              </el-button>
              <el-button v-if="canOpenLastResult" @click="openLastResult">
                打开上次结果
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </div>

      <!-- Right Section: Status & History -->
      <div class="status-section">
        <!-- Current Task Status -->
        <div v-if="hasLastTask" class="page-card teacher-card status-card">
          <div class="sub-title">任务状态</div>
          
          <div v-if="taskSnapshot.status === 'running'" class="progress-wrapper">
            <el-progress 
              type="dashboard" 
              :percentage="progressPercentage" 
              :status="progressStatus"
              :stroke-width="10"
              :width="120"
            >
              <template #default="{ percentage }">
                <div class="progress-text">
                  <span class="percentage-value">{{ percentage }}%</span>
                  <span class="percentage-label">生成进度</span>
                </div>
              </template>
            </el-progress>
          </div>

          <el-descriptions :column="1" border>
            <el-descriptions-item label="状态">
              <el-tag :type="taskStatusType">{{ taskStatusLabel }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="进度">{{ progressLabel }}</el-descriptions-item>
            <el-descriptions-item label="当前章节">{{ taskSnapshot.currentSectionName || '-' }}</el-descriptions-item>
            <el-descriptions-item label="总耗时">{{ elapsedLabel }}</el-descriptions-item>
          </el-descriptions>

          <div v-if="taskSnapshot.status === 'failed' || taskSnapshot.status === 'interrupted'" class="error-retry">
            <div class="error-msg">{{ taskSnapshot.errorMsg || (taskSnapshot.status === 'failed' ? '生成失败' : '生成中断') }}</div>
            <el-button type="warning" size="small" @click="handleGenerate">重新发起生成</el-button>
          </div>
        </div>

        <!-- Recent Scripts -->
        <div v-if="parseScripts.length" class="page-card teacher-card history-card">
          <div class="sub-title">历史脚本</div>
          <el-table :data="parseScripts" border size="small">
            <el-table-column prop="scriptStatus" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="scriptStatusType(row.scriptStatus)" size="small">
                  {{ scriptStatusText(row.scriptStatus).substring(1, 2) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="updatedAt" label="更新时间" min-width="100">
              <template #default="{ row }">
                {{ row.updatedAt.split(' ')[0].substring(5) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="60">
              <template #default="{ row }">
                <el-button type="primary" link @click="openScript(row.scriptId)">打开</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
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
import { Document, Timer, Collection, Reading } from '@element-plus/icons-vue'
import TeacherLayout from '@/components/teacher/TeacherLayout.vue'
import Loading from '@/components/teacher/Loading.vue'
import ErrorTip from '@/components/teacher/ErrorTip.vue'
import { generateScript, getCoursewareAssets, getParseScripts } from '@/api/teacher'
import {
  getCurrentCourse,
  getParseResult,
  getScriptTask,
  getTeacherWorkspaceContext,
  patchTeacherWorkspaceContext,
  patchScriptTask,
  saveScriptResult
} from '@/utils/platform'

const TASK_PAGE = 'script-generate'
const router = useRouter()
const currentCourse = getCurrentCourse()
const parseResult = getParseResult()
const cachedTask = getScriptTask()
const initialWorkspaceContext = getTeacherWorkspaceContext(currentCourse.courseId)
const readWorkspaceContext = () => getTeacherWorkspaceContext(currentCourse.courseId)

const form = ref({
  parseId: initialWorkspaceContext.parseId || cachedTask.parseId || parseResult.parseId || '',
  teachingStyle: cachedTask.teachingStyle || 'standard',
  speechSpeed: cachedTask.speechSpeed || 'normal',
  customOpening: cachedTask.customOpening || ''
})

const loading = ref(false)
const loadingHistory = ref(false)
const errorCode = ref('')
const errorMsg = ref('')
const taskSnapshot = ref({ ...cachedTask, parseId: form.value.parseId })
const elapsedSeconds = ref(0)
const chapterInfo = ref({
  chapterId: initialWorkspaceContext.chapterId || '',
  chapterName: initialWorkspaceContext.chapterName || ''
})
const assetHistory = ref([])
const parseScripts = ref([])
let timerId = null

const parseOptions = computed(() =>
  assetHistory.value.flatMap((asset) =>
    (asset.parseTasks || []).map((task) => ({
      parseId: task.parseId,
      taskStatus: task.taskStatus,
      assetId: asset.assetId,
      chapterId: asset.chapterId || '',
      chapterName: asset.chapterName || '',
      versionNo: asset.versionNo,
      fileName: asset.fileName,
      fileType: asset.fileType,
      label: `${asset.chapterName || '未命名章节'} · V${asset.versionNo} · ${asset.fileName} · ${parseStatusText(task.taskStatus)} · ${task.parseId}`,
      finishedAt: task.finishedAt || '',
      scriptCount: task.scriptCount || 0,
      audioCount: task.audioCount || 0
    }))
  )
)
const selectedParseMeta = computed(() => parseOptions.value.find((item) => item.parseId === form.value.parseId) || null)
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
const progressPercentage = computed(() => {
  const completed = Number(taskSnapshot.value.completedSections || 0)
  const total = Number(taskSnapshot.value.totalSections || 0)
  return total > 0 ? Math.floor((completed / total) * 100) : 0
})
const progressStatus = computed(() => {
  if (taskSnapshot.value.status === 'failed') return 'exception'
  if (taskSnapshot.value.status === 'completed' || taskSnapshot.value.status === 'success') return 'success'
  return ''
})
const elapsedLabel = computed(() => formatElapsed(elapsedSeconds.value))
const taskStatusType = computed(() => {
  const map = {
    running: 'primary',
    completed: 'success',
    success: 'success',
    failed: 'danger',
    interrupted: 'warning',
    pending: 'info'
  }
  return map[taskSnapshot.value.status] || 'info'
})

watch(
  form,
  () => {
    persistTaskSnapshot()
  },
  { deep: true }
)

onMounted(async () => {
  // Validate stale task
  if (taskSnapshot.value.status === 'running' && taskSnapshot.value.startedAt) {
    const startTime = new Date(taskSnapshot.value.startedAt).getTime()
    const now = Date.now()
    const diffMinutes = (now - startTime) / (1000 * 60)
    if (diffMinutes > 30) {
      taskSnapshot.value = patchScriptTask({
        ...taskSnapshot.value,
        status: 'interrupted',
        errorMsg: '任务执行时间过长，已自动判定为中断'
      })
    }
  }

  persistTaskSnapshot({ lastPage: TASK_PAGE })
  syncElapsed()
  await loadCoursewareHistory()
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

async function loadCoursewareHistory() {
  if (!currentCourse.courseId) {
    return
  }

  loadingHistory.value = true
  try {
    const res = await getCoursewareAssets({
      courseId: currentCourse.courseId
    })
    const data = res.data || {}
    assetHistory.value = data.assets || []

    const preferredParseId = resolvePreferredParseId(
      parseOptions.value,
      readWorkspaceContext().parseId || cachedTask.parseId || parseResult.parseId || ''
    )
    if (preferredParseId) {
      form.value.parseId = preferredParseId
      await syncParseSelection(preferredParseId, { preserveScript: true, silent: true })
    }
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || '读取历史课件版本失败'
  } finally {
    loadingHistory.value = false
  }
}

async function handleParseChange(parseId) {
  await syncParseSelection(parseId, { preserveScript: false })
}

async function syncParseSelection(parseId, options = {}) {
  const { preserveScript = false, silent = false } = options
  form.value.parseId = parseId || ''
  const meta = parseOptions.value.find((item) => item.parseId === form.value.parseId) || null
  chapterInfo.value = {
    chapterId: meta?.chapterId || '',
    chapterName: meta?.chapterName || ''
  }
  const workspaceContext = readWorkspaceContext()
  const previousScriptId = preserveScript ? workspaceContext.scriptId || taskSnapshot.value.scriptId || '' : ''
  patchTeacherWorkspaceContext(currentCourse.courseId, {
    chapterId: meta?.chapterId || '',
    chapterName: meta?.chapterName || '',
    parseId: form.value.parseId,
    assetId: meta?.assetId || '',
    fileName: meta?.fileName || '',
    versionNo: meta?.versionNo || null,
    scriptId: previousScriptId,
    audioId: '',
    audioUrl: '',
    audioStatus: ''
  })
  await loadScriptsForParse(form.value.parseId, previousScriptId)
  if (!silent && meta) {
    ElMessage.success(`已切换到课件 V${meta.versionNo}`)
  }
}

async function loadScriptsForParse(parseId, preferredScriptId = '') {
  parseScripts.value = []
  if (!parseId) {
    return
  }
  try {
    const res = await getParseScripts(parseId)
    const data = res.data || {}
    chapterInfo.value = {
      chapterId: data.chapterId || chapterInfo.value.chapterId || '',
      chapterName: data.chapterName || chapterInfo.value.chapterName || ''
    }
    parseScripts.value = data.scripts || []
    const matchedScript = parseScripts.value.find((item) => item.scriptId === preferredScriptId)
    patchTeacherWorkspaceContext(currentCourse.courseId, {
      chapterId: chapterInfo.value.chapterId,
      chapterName: chapterInfo.value.chapterName,
      scriptId: matchedScript?.scriptId || '',
      audioId: '',
      audioUrl: '',
      audioStatus: ''
    })
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || '读取解析版本脚本失败'
  }
}

async function handleGenerate() {
  if (!form.value.parseId) {
    ElMessage.warning('请先选择已完成解析的课件版本。')
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
  patchTeacherWorkspaceContext(currentCourse.courseId, {
    chapterId: chapterInfo.value.chapterId,
    chapterName: chapterInfo.value.chapterName,
    parseId: form.value.parseId,
    assetId: selectedParseMeta.value?.assetId || '',
    fileName: selectedParseMeta.value?.fileName || '',
    versionNo: selectedParseMeta.value?.versionNo || null,
    scriptId: '',
    audioId: '',
    audioUrl: '',
    audioStatus: ''
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
    patchTeacherWorkspaceContext(currentCourse.courseId, {
      chapterId: chapterInfo.value.chapterId,
      chapterName: chapterInfo.value.chapterName,
      parseId: form.value.parseId,
      assetId: selectedParseMeta.value?.assetId || '',
      fileName: selectedParseMeta.value?.fileName || '',
      versionNo: selectedParseMeta.value?.versionNo || null,
      scriptId: data.scriptId || '',
      audioId: '',
      audioUrl: '',
      audioStatus: ''
    })
    router.push({
      path: '/teacher/script-edit',
      query: data.scriptId ? { scriptId: data.scriptId } : {}
    })
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
  openScript(taskSnapshot.value.scriptId)
}

function openScript(scriptId) {
  if (!scriptId) {
    ElMessage.warning('脚本不存在')
    return
  }
  patchTeacherWorkspaceContext(currentCourse.courseId, {
    chapterId: chapterInfo.value.chapterId,
    chapterName: chapterInfo.value.chapterName,
    parseId: form.value.parseId,
    assetId: selectedParseMeta.value?.assetId || '',
    fileName: selectedParseMeta.value?.fileName || '',
    versionNo: selectedParseMeta.value?.versionNo || null,
    scriptId,
    audioId: '',
    audioUrl: '',
    audioStatus: ''
  })
  router.push({
    path: '/teacher/script-edit',
    query: { scriptId }
  })
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

function resolvePreferredParseId(options, preferredParseId) {
  if (!Array.isArray(options) || !options.length) {
    return ''
  }
  if (preferredParseId && options.some((item) => item.parseId === preferredParseId && item.taskStatus === 'completed')) {
    return preferredParseId
  }
  return options.find((item) => item.taskStatus === 'completed')?.parseId || ''
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

function parseStatusText(status) {
  const map = {
    completed: '已解析',
    processing: '解析中',
    failed: '解析失败'
  }
  return map[status] || '未知'
}

function scriptStatusText(status) {
  const map = {
    generated: '已生成',
    edited: '已编辑',
    published: '已发布'
  }
  return map[status] || status || '-'
}

function scriptStatusType(status) {
  if (status === 'published') return 'success'
  if (status === 'edited') return 'warning'
  if (status === 'generated') return 'info'
  return 'info'
}

function styleText(type) {
  const map = {
    standard: '标准',
    detailed: '详细',
    concise: '简洁'
  }
  return map[type] || '-'
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
.page-container {
  display: grid;
  grid-template-columns: 1fr 350px;
  gap: 20px;
  align-items: start;
}

@media (max-width: 1200px) {
  .page-container {
    grid-template-columns: 1fr;
  }
}

.teacher-card {
  border-radius: 22px;
  box-shadow: 0 8px 24px rgba(149, 157, 165, 0.1);
}

.config-section .teacher-card {
  padding: 24px;
}

.status-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.status-card, .history-card {
  padding: 20px;
}

.progress-wrapper {
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
  background: #f8faff;
  padding: 20px;
  border-radius: 16px;
}

.progress-text {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.percentage-value {
  font-size: 24px;
  font-weight: 700;
  color: #409eff;
}

.percentage-label {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.sub-title {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-radio-group {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  width: 100%;
}

.card-radio {
  margin-right: 0 !important;
  height: auto !important;
  border: 2px solid #f0f2f5;
  border-radius: 12px;
  padding: 12px !important;
  transition: all 0.3s;
  background: #fff;
}

.card-radio.is-checked {
  border-color: #409eff;
  background: #f0f7ff;
}

.card-radio:hover {
  border-color: #c6e2ff;
}

:deep(.card-radio .el-radio__input) {
  display: none;
}

:deep(.card-radio .el-radio__label) {
  padding-left: 0;
  width: 100%;
}

.card-radio-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 8px;
}

.card-icon {
  font-size: 24px;
  color: #909399;
}

.is-checked .card-icon {
  color: #409eff;
}

.card-label {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.card-desc {
  font-size: 11px;
  color: #909399;
  line-height: 1.4;
}

.full-width {
  width: 100%;
}

.version-summary {
  display: grid;
  gap: 4px;
  color: #4b5f82;
  line-height: 1.6;
  font-size: 13px;
  background: #f8faff;
  padding: 12px;
  border-radius: 12px;
}

.error-retry {
  margin-top: 16px;
  padding: 12px;
  background: #fff5f5;
  border-radius: 12px;
  border: 1px solid #ffcfcf;
  text-align: center;
}

.error-msg {
  color: #f56c6c;
  font-size: 13px;
  margin-bottom: 8px;
}

:deep(.el-descriptions__label) {
  width: 100px;
  color: #606266;
}

:deep(.el-descriptions__content) {
  color: #2c3e50;
  font-weight: 500;
}
</style>
