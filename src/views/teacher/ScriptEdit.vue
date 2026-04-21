<template>
  <TeacherLayout>
    <div class="page-card">
      <div class="page-title">脚本编辑</div>

      <div class="toolbar version-toolbar">
        <el-form inline class="version-form">
          <el-form-item label="解析版本" class="version-form-item">
            <el-select
              v-model="form.parseId"
              class="version-select"
              placeholder="请选择解析版本"
              clearable
              filterable
              :loading="loadingHistory"
              @change="handleParseChange"
            >
              <el-option
                v-for="item in parseOptions"
                :key="item.parseId"
                :label="item.label"
                :value="item.parseId"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="脚本版本" class="version-form-item">
            <el-select
              v-model="form.scriptId"
              class="version-select"
              placeholder="请选择已有脚本"
              clearable
              filterable
              :disabled="!form.parseId || !parseScripts.length"
              @change="handleScriptChange"
            >
              <el-option
                v-for="item in parseScripts"
                :key="item.scriptId"
                :label="`${item.scriptId} · ${scriptStatusText(item.scriptStatus)}${item.updatedAt ? ` · ${item.updatedAt}` : ''}`"
                :value="item.scriptId"
              />
            </el-select>
          </el-form-item>
        </el-form>

        <div v-if="selectedParseMeta || selectedScriptMeta" class="version-summary">
          <span v-if="selectedParseMeta">
            课件：{{ selectedParseMeta.chapterName || '未命名章节' }} · V{{ selectedParseMeta.versionNo }}
          </span>
          <span v-if="selectedScriptMeta">
            当前脚本状态：{{ scriptStatusText(selectedScriptMeta.scriptStatus) }}
          </span>
        </div>
      </div>

      <div class="toolbar top-actions">
        <el-button :loading="restoring" @click="loadLastResult({ forceRemote: true })">刷新</el-button>
        <el-button v-if="form.scriptId" type="primary" :disabled="!canSave" :loading="saving" @click="handleSave">
          保存脚本
        </el-button>
        <el-button type="success" :disabled="!canGoAudio" @click="goAudioPage">进入音频生成</el-button>
      </div>

      <template v-if="hasScript">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="脚本编号">{{ form.scriptId }}</el-descriptions-item>
          <el-descriptions-item label="解析任务编号">{{ form.parseId }}</el-descriptions-item>
          <el-descriptions-item label="讲解风格">{{ styleLabel }}</el-descriptions-item>
          <el-descriptions-item label="进度">{{ progressLabel }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ generationStatusLabel }}</el-descriptions-item>
          <el-descriptions-item label="总耗时">{{ elapsedLabel }}</el-descriptions-item>
          <el-descriptions-item label="当前章节">{{ form.currentSectionName || '-' }}</el-descriptions-item>
          <el-descriptions-item label="章节数">{{ form.scriptStructure.length }}</el-descriptions-item>
        </el-descriptions>

        <el-alert
          v-if="isRunning"
          class="status-alert"
          type="info"
          :closable="false"
          show-icon
          title="脚本正在按章节逐步生成，已经完成的章节会立即显示。"
        />
        <el-alert
          v-else-if="form.generationStatus === 'failed'"
          class="status-alert"
          type="error"
          :closable="false"
          show-icon
          :title="form.errorMsg || '脚本尚未全部生成完成，生成过程已失败。'"
        />
      </template>

      <el-empty
        v-else
        description="当前还没有可编辑的脚本，请先加载上次结果或重新生成。"
      >
        <el-button type="primary" :loading="restoring" @click="loadLastResult({ forceRemote: true })">加载上次结果</el-button>
        <el-button @click="goGeneratePage">开始生成</el-button>
      </el-empty>
    </div>

    <div v-if="hasScript" class="page-card">
      <div class="sub-title">脚本内容</div>

      <div
        v-for="(section, index) in form.scriptStructure"
        :key="section.sectionId"
        class="section-card"
      >
        <div class="section-meta">
          <div>
            <div class="section-index">章节 {{ index + 1 }}</div>
            <div class="section-name">{{ section.sectionName }}</div>
          </div>
          <div class="section-tags">
            <el-tag size="small">{{ section.sectionId }}</el-tag>
            <el-tag v-if="section.relatedPage" size="small" type="success">页码 {{ section.relatedPage }}</el-tag>
            <el-tag size="small" :type="sectionTagType(section)">{{ sectionStatusLabel(section) }}</el-tag>
            <el-tag size="small" type="warning">{{ section.duration || 0 }} 秒</el-tag>
          </div>
        </div>

        <div v-if="section.keyPoints?.length" class="key-points">
          <span
            v-for="point in section.keyPoints"
            :key="point"
            class="key-point"
          >
            {{ point }}
          </span>
        </div>

        <el-input
          v-model="section.content"
          type="textarea"
          :rows="8"
          resize="vertical"
          :disabled="isRunning"
          :placeholder="sectionPlaceholder(section)"
        />
      </div>
    </div>
  </TeacherLayout>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import TeacherLayout from '@/components/teacher/TeacherLayout.vue'
import { getCoursewareAssets, getParseScripts, getScript, updateScript } from '@/api/teacher'
import { getCurrentCourse, getScriptResult, getScriptTask, getTeacherWorkspaceContext, patchTeacherWorkspaceContext, patchScriptTask, saveScriptResult } from '@/utils/platform'

const TASK_PAGE = 'script-edit'
const POLL_INTERVAL_MS = 2000
const route = useRoute()
const router = useRouter()
const currentCourse = getCurrentCourse()
const cachedResult = getScriptResult()
const cachedTask = getScriptTask()
const initialWorkspaceContext = getTeacherWorkspaceContext(currentCourse.courseId)
const readWorkspaceContext = () => getTeacherWorkspaceContext(currentCourse.courseId)

const form = reactive(createFormState(cachedResult.scriptId ? cachedResult : { ...cachedTask, parseId: initialWorkspaceContext.parseId || cachedTask.parseId || '' }))
const saving = ref(false)
const restoring = ref(false)
const loadingHistory = ref(false)
const bootstrapped = ref(false)
const elapsedSeconds = ref(0)
const assetHistory = ref([])
const parseScripts = ref([])
const chapterInfo = ref({
  chapterId: initialWorkspaceContext.chapterId || '',
  chapterName: initialWorkspaceContext.chapterName || ''
})
let pollTimerId = null
let elapsedTimerId = null

const hasScript = computed(() => Boolean(form.scriptId) && form.scriptStructure.length > 0)
const isRunning = computed(() => form.generationStatus === 'running')
const canSave = computed(() => hasScript.value && !isRunning.value)
const completedSections = computed(() => Number(form.completedSections || countCompletedSections(form.scriptStructure)))
const totalSections = computed(() => Number(form.totalSections || form.scriptStructure.length || 0))
const canGoAudio = computed(() => hasScript.value && !isRunning.value && completedSections.value > 0)
const progressLabel = computed(() => (totalSections.value > 0 ? `${completedSections.value}/${totalSections.value}` : '-'))
const styleLabelMap = {
  standard: '标准',
  detailed: '详细',
  concise: '简洁'
}
const styleLabel = computed(() => styleLabelMap[form.teachingStyle] || form.teachingStyle || '-')
const generationStatusLabel = computed(() => {
  const statusMap = {
    pending: '待开始',
    running: '生成中',
    completed: '已完成',
    failed: '失败',
    interrupted: '已中断'
  }
  return statusMap[form.generationStatus] || '待开始'
})
const elapsedLabel = computed(() => formatElapsed(elapsedSeconds.value))
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
      scriptCount: task.scriptCount || 0
    }))
  )
)
const selectedParseMeta = computed(() => parseOptions.value.find((item) => item.parseId === form.parseId) || null)
const selectedScriptMeta = computed(() => parseScripts.value.find((item) => item.scriptId === form.scriptId) || null)

watch(
  form,
  () => {
    if (!bootstrapped.value) {
      return
    }
    persistDraft()
  },
  { deep: true }
)

watch(
  isRunning,
  (running) => {
    if (running) {
      startPolling()
      startElapsedTimer()
    } else {
      stopPolling()
      stopElapsedTimer()
      syncElapsed()
    }
  },
  { immediate: false }
)

onMounted(async () => {
  patchScriptTask({ lastPage: TASK_PAGE })
  const routeScriptId = typeof route.query.scriptId === 'string' ? route.query.scriptId : ''
  const routeParseId = typeof route.query.parseId === 'string' ? route.query.parseId : ''
  await loadCoursewareHistory({
    preferredParseId: routeParseId || initialWorkspaceContext.parseId || cachedResult.parseId || cachedTask.parseId || '',
    preferredScriptId: routeScriptId || initialWorkspaceContext.scriptId || cachedResult.scriptId || cachedTask.scriptId || ''
  })
  if (!form.scriptId && (hasRemoteScriptSource() || Boolean(routeScriptId))) {
    await loadLastResult({ silent: true, forceRemote: true, scriptId: routeScriptId || initialWorkspaceContext.scriptId || '' })
  }
  bootstrapped.value = true
  window.addEventListener('beforeunload', persistDraft)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  syncElapsed()
  if (isRunning.value) {
    startPolling()
    startElapsedTimer()
  }
})

onBeforeUnmount(() => {
  persistDraft()
  stopPolling()
  stopElapsedTimer()
  window.removeEventListener('beforeunload', persistDraft)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})

async function handleSave() {
  if (!canSave.value) {
    ElMessage.warning('请等待脚本生成完成后再保存编辑')
    return
  }

  saving.value = true
  try {
    const activeScriptId = form.scriptId
    const res = await updateScript(activeScriptId, {
      scriptStructure: cloneSections(form.scriptStructure),
      versionRemark: 'teacher-edit'
    })
    await loadLastResult({ silent: true, forceRemote: true, scriptId: activeScriptId })

    const data = res.data || {}
    const nextResult = {
      ...getScriptResult(),
      ...serializeForm(),
      version: data.version || 2,
      status: 'completed',
      generationStatus: 'completed',
      savedAt: data.savedAt || ''
    }
    saveScriptResult(nextResult)
    patchScriptTask({
      ...nextResult,
      status: 'completed',
      lastPage: TASK_PAGE
    })
    patchTeacherWorkspaceContext(currentCourse.courseId, {
      parseId: form.parseId,
      scriptId: activeScriptId,
      chapterId: chapterInfo.value.chapterId,
      chapterName: chapterInfo.value.chapterName
    })
    ElMessage.success('脚本已保存')
  } catch (error) {
    ElMessage.error(error.msg || '保存脚本失败')
  } finally {
    saving.value = false
  }
}

async function loadCoursewareHistory(options = {}) {
  if (!currentCourse.courseId) {
    return
  }

  const { preferredParseId = '', preferredScriptId = '' } = options
  loadingHistory.value = true
  try {
    const res = await getCoursewareAssets({
      courseId: currentCourse.courseId
    })
    const data = res.data || {}
    assetHistory.value = data.assets || []

    const nextParseId = resolvePreferredParseId(
      parseOptions.value,
      preferredParseId || readWorkspaceContext().parseId || form.parseId || ''
    )
    if (nextParseId) {
      await syncParseSelection(nextParseId, {
        preserveScript: true,
        preferredScriptId,
        silent: true
      })
    }
  } catch (error) {
    ElMessage.error(error.msg || '读取历史课件版本失败')
  } finally {
    loadingHistory.value = false
  }
}

async function handleParseChange(parseId) {
  await syncParseSelection(parseId, { preserveScript: false })
}

async function syncParseSelection(parseId, options = {}) {
  const { preserveScript = false, preferredScriptId = '', silent = false } = options
  form.parseId = parseId || ''
  const meta = parseOptions.value.find((item) => item.parseId === form.parseId) || null
  chapterInfo.value = {
    chapterId: meta?.chapterId || '',
    chapterName: meta?.chapterName || ''
  }
  const workspaceContext = readWorkspaceContext()
  const nextPreferredScriptId = preferredScriptId || (preserveScript ? workspaceContext.scriptId || form.scriptId || '' : '')
  patchTeacherWorkspaceContext(currentCourse.courseId, {
    chapterId: meta?.chapterId || '',
    chapterName: meta?.chapterName || '',
    parseId: form.parseId,
    assetId: meta?.assetId || '',
    fileName: meta?.fileName || '',
    versionNo: meta?.versionNo || null,
    scriptId: nextPreferredScriptId
  })
  await loadScriptsForParse(form.parseId, nextPreferredScriptId)
  if (!silent && meta) {
    ElMessage.success(`已切换到课件 V${meta.versionNo}`)
  }
}

async function loadScriptsForParse(parseId, preferredScriptId = '') {
  parseScripts.value = []
  form.scriptId = ''
  if (!parseId) {
    applyForm(createFormState({ parseId: '', scriptId: '', scriptStructure: [] }))
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
    const nextScriptId = resolvePreferredScriptId(parseScripts.value, preferredScriptId)
    patchTeacherWorkspaceContext(currentCourse.courseId, {
      chapterId: chapterInfo.value.chapterId,
      chapterName: chapterInfo.value.chapterName,
      parseId,
      scriptId: nextScriptId
    })
    if (nextScriptId) {
      form.scriptId = nextScriptId
      await loadLastResult({ silent: true, forceRemote: true, scriptId: nextScriptId })
      return
    }
    applyForm(createFormState({ parseId, scriptId: '', scriptStructure: [] }))
  } catch (error) {
    ElMessage.error(error.msg || '读取脚本列表失败')
  }
}

async function handleScriptChange(scriptId) {
  patchTeacherWorkspaceContext(currentCourse.courseId, {
    parseId: form.parseId,
    scriptId,
    chapterId: chapterInfo.value.chapterId,
    chapterName: chapterInfo.value.chapterName
  })
  if (!scriptId) {
    applyForm(createFormState({ parseId: form.parseId, scriptId: '', scriptStructure: [] }))
    return
  }
  await loadLastResult({ silent: true, forceRemote: true, scriptId })
  ElMessage.success('已切换为历史脚本版本')
}

async function loadLastResult(options = {}) {
  const { silent = false, forceRemote = false, scriptId: targetScriptId = '' } = options
  const latestResult = getScriptResult()
  const latestTask = getScriptTask()
  const scriptId = targetScriptId || latestResult.scriptId || latestTask.scriptId || form.scriptId
  const matchesTargetScript = !targetScriptId || latestResult.scriptId === targetScriptId

  if (!forceRemote && matchesTargetScript && hasScriptStructure(latestResult) && latestResult.generationStatus !== 'running') {
    applyForm(latestResult)
    patchScriptTask({
      ...latestResult,
      status: latestTask.status || mapGenerationStatus(latestResult.generationStatus),
      lastPage: TASK_PAGE
    })
    syncElapsed()
    if (!silent) {
      ElMessage.success('已加载缓存结果')
    }
    return
  }

  if (!scriptId) {
    if (!silent) {
      ElMessage.warning('暂无可用的脚本结果')
    }
    return
  }

  restoring.value = true
  try {
    const res = await getScript(scriptId)
    const data = res.data || {}
    const mergedResult = {
      ...latestTask,
      ...latestResult,
      ...data,
      status: mapGenerationStatus(data.generationStatus),
      startedAt: data.startedAt || latestTask.startedAt || latestResult.startedAt || '',
      finishedAt: data.finishedAt || latestTask.finishedAt || latestResult.finishedAt || ''
    }
    applyForm(mergedResult)
    saveScriptResult(mergedResult)
    patchScriptTask({
      ...mergedResult,
      lastPage: TASK_PAGE
    })
    patchTeacherWorkspaceContext(currentCourse.courseId, {
      parseId: mergedResult.parseId || '',
      scriptId: mergedResult.scriptId || ''
    })
    syncElapsed()
    if (!silent) {
      ElMessage.success('已加载最新脚本状态')
    }
  } catch (error) {
    if (!silent) {
      ElMessage.error(error.msg || '加载脚本状态失败')
    }
  } finally {
    restoring.value = false
  }
}

function persistDraft() {
  if (!form.parseId && !form.scriptId) {
    return
  }

  const currentTask = getScriptTask()
  const currentResult = getScriptResult()
  const nextResult = {
    ...currentResult,
    ...serializeForm(),
    version: currentResult.version || currentTask.version || 1,
    status: currentTask.status || mapGenerationStatus(form.generationStatus),
    savedAt: currentResult.savedAt || currentTask.savedAt || ''
  }
  saveScriptResult(nextResult)
  patchScriptTask({
    ...nextResult,
    lastPage: TASK_PAGE
  })
  patchTeacherWorkspaceContext(currentCourse.courseId, {
    parseId: form.parseId,
    scriptId: form.scriptId
  })
}

function handleVisibilityChange() {
  if (document.visibilityState === 'hidden') {
    persistDraft()
  }
}

function goGeneratePage() {
  router.push('/teacher/script-generate')
}

function goAudioPage() {
  if (!canGoAudio.value) {
    ElMessage.warning('请先等待脚本生成完成')
    return
  }
  router.push('/teacher/audio-generate')
}

function applyForm(source) {
  const next = createFormState(source)
  form.scriptId = next.scriptId
  form.parseId = next.parseId
  form.teachingStyle = next.teachingStyle
  form.speechSpeed = next.speechSpeed
  form.customOpening = next.customOpening
  form.scriptStructure = next.scriptStructure
  form.version = next.version
  form.generationStatus = next.generationStatus
  form.completedSections = next.completedSections
  form.totalSections = next.totalSections
  form.currentSectionId = next.currentSectionId
  form.currentSectionName = next.currentSectionName
  form.startedAt = next.startedAt
  form.finishedAt = next.finishedAt
  form.errorMsg = next.errorMsg
}

function createFormState(source = {}) {
  return {
    scriptId: source.scriptId || '',
    parseId: source.parseId || '',
    teachingStyle: source.teachingStyle || 'standard',
    speechSpeed: source.speechSpeed || 'normal',
    customOpening: source.customOpening || '',
    scriptStructure: cloneSections(source.scriptStructure),
    version: source.version || 1,
    generationStatus: source.generationStatus || 'pending',
    completedSections: Number(source.completedSections || 0),
    totalSections: Number(source.totalSections || (Array.isArray(source.scriptStructure) ? source.scriptStructure.length : 0)),
    currentSectionId: source.currentSectionId || '',
    currentSectionName: source.currentSectionName || '',
    startedAt: source.startedAt || '',
    finishedAt: source.finishedAt || '',
    errorMsg: source.errorMsg || ''
  }
}

function serializeForm() {
  return {
    scriptId: form.scriptId,
    parseId: form.parseId,
    teachingStyle: form.teachingStyle,
    speechSpeed: form.speechSpeed,
    customOpening: form.customOpening,
    scriptStructure: cloneSections(form.scriptStructure),
    version: form.version,
    generationStatus: form.generationStatus,
    completedSections: completedSections.value,
    totalSections: totalSections.value,
    currentSectionId: form.currentSectionId,
    currentSectionName: form.currentSectionName,
    startedAt: form.startedAt,
    finishedAt: form.finishedAt,
    errorMsg: form.errorMsg
  }
}

function cloneSections(sections = []) {
  return Array.isArray(sections)
    ? sections.map((section) => ({
        ...section,
        keyPoints: Array.isArray(section.keyPoints) ? [...section.keyPoints] : []
      }))
    : []
}

function hasScriptStructure(value) {
  return Array.isArray(value?.scriptStructure) && value.scriptStructure.length > 0
}

function hasRemoteScriptSource() {
  return Boolean(getScriptTask().scriptId || getScriptResult().scriptId || getScriptTask().parseId || getScriptResult().parseId)
}

function countCompletedSections(sections = []) {
  return Array.isArray(sections)
    ? sections.filter((section) => typeof section.content === 'string' && section.content.trim()).length
    : 0
}

function mapGenerationStatus(status) {
  if (status === 'completed') {
    return 'completed'
  }
  if (status === 'failed') {
    return 'failed'
  }
  if (status === 'interrupted') {
    return 'interrupted'
  }
  if (status === 'running') {
    return 'running'
  }
  return 'pending'
}

function sectionStatusLabel(section) {
  if (section.content && section.content.trim()) {
    return '已生成'
  }
  if (isRunning.value && section.sectionId === form.currentSectionId) {
    return '生成中'
  }
  return '待开始'
}

function sectionTagType(section) {
  if (section.content && section.content.trim()) {
    return 'success'
  }
  if (isRunning.value && section.sectionId === form.currentSectionId) {
    return 'warning'
  }
  return 'info'
}

function sectionPlaceholder(section) {
  if (isRunning.value && section.content && section.content.trim()) {
    return ''
  }
  if (isRunning.value && section.sectionId === form.currentSectionId) {
    return '当前章节正在生成中...'
  }
  return isRunning.value ? '等待生成进入当前章节。' : '请输入或修改当前章节讲稿内容。'
}

function resolvePreferredParseId(options, preferredParseId) {
  if (!Array.isArray(options) || !options.length) {
    return ''
  }
  if (preferredParseId && options.some((item) => item.parseId === preferredParseId && item.taskStatus === 'completed')) {
    return preferredParseId
  }
  return options.find((item) => item.taskStatus === 'completed' && item.scriptCount > 0)?.parseId
    || options.find((item) => item.taskStatus === 'completed')?.parseId
    || ''
}

function resolvePreferredScriptId(options, preferredScriptId) {
  if (!Array.isArray(options) || !options.length) {
    return ''
  }
  if (preferredScriptId && options.some((item) => item.scriptId === preferredScriptId)) {
    return preferredScriptId
  }
  return options[0]?.scriptId || ''
}

function parseStatusText(status) {
  const map = {
    pending: '待开始',
    running: '解析中',
    completed: '已完成',
    failed: '失败',
    interrupted: '已中断'
  }
  return map[status] || '未知状态'
}

function scriptStatusText(status) {
  const map = {
    generated: '已生成',
    edited: '已编辑',
    published: '已发布'
  }
  return map[status] || status || '未知状态'
}

function startPolling() {
  if (pollTimerId || !form.scriptId) {
    return
  }
  pollTimerId = window.setInterval(() => {
    if (!restoring.value && form.scriptId) {
      loadLastResult({ silent: true, forceRemote: true })
    }
  }, POLL_INTERVAL_MS)
}

function stopPolling() {
  if (pollTimerId) {
    window.clearInterval(pollTimerId)
    pollTimerId = null
  }
}

function startElapsedTimer() {
  if (elapsedTimerId) {
    return
  }
  syncElapsed()
  elapsedTimerId = window.setInterval(syncElapsed, 1000)
}

function stopElapsedTimer() {
  if (elapsedTimerId) {
    window.clearInterval(elapsedTimerId)
    elapsedTimerId = null
  }
}

function syncElapsed() {
  elapsedSeconds.value = getElapsedSeconds(form.startedAt, form.finishedAt, form.generationStatus)
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
.toolbar {
  margin-top: 16px;
}

.top-actions {
  margin-top: 0;
  margin-bottom: 16px;
}

.version-toolbar {
  margin-top: 0;
  margin-bottom: 16px;
}

.version-form {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 16px;
  width: 100%;
}

.version-form :deep(.el-form-item) {
  margin-right: 0;
  margin-bottom: 0;
}

.version-form-item {
  flex: 1 1 420px;
  min-width: 320px;
}

.version-form-item :deep(.el-form-item__content) {
  width: min(100%, 620px);
}

.version-select {
  width: 100%;
}

.version-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 8px;
  color: #606266;
  font-size: 13px;
}

.status-alert {
  margin-top: 16px;
}

.section-card {
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 16px;
  margin-top: 16px;
  background: #fff;
}

.section-meta {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.section-index {
  font-size: 12px;
  color: #909399;
}

.section-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-top: 4px;
}

.section-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.key-points {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.key-point {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  color: #3a5b7a;
  background: #eef5fb;
}
</style>
