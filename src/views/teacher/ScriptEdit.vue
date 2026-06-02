<template>
  <TeacherLayout>
    <div class="script-edit-layout">
      <!-- 左侧目录导航 -->
      <aside class="script-aside" :class="{ 'mobile-collapsed': !sidebarVisible }">
        <TeacherCard class="aside-card" :body-style="{ padding: '0' }">
          <template #header>
            <div class="aside-header">
              <span class="aside-title">章节目录</span>
              <el-tag size="small" type="info">{{ form.scriptStructure.length }} 章节</el-tag>
            </div>
          </template>

          <div class="aside-content app-scrollable">
            <!-- 版本选择器 (移动到侧边栏顶部或主面板顶部，侧边栏更节省主区空间) -->
            <div class="version-compact-box">
              <el-select
                v-model="form.parseId"
                size="small"
                placeholder="解析版本"
                class="compact-select"
                :loading="loadingHistory"
                @change="handleParseChange"
              >
                <el-option
                  v-for="item in parseOptions"
                  :key="item.parseId"
                  :label="`V${item.versionNo} · ${item.chapterName}`"
                  :value="item.parseId"
                />
              </el-select>
              <el-select
                v-model="form.scriptId"
                size="small"
                placeholder="脚本版本"
                class="compact-select"
                :disabled="!form.parseId || !parseScripts.length"
                @change="handleScriptChange"
              >
                <el-option
                  v-for="item in parseScripts"
                  :key="item.scriptId"
                  :label="`脚本 ${item.scriptId.slice(-4)} · ${scriptStatusText(item.scriptStatus)}`"
                  :value="item.scriptId"
                />
              </el-select>
            </div>

            <div v-if="hasScript" class="section-list">
              <div
                v-for="(section, index) in form.scriptStructure"
                :key="section.sectionId"
                class="section-nav-item"
                :class="{ active: activeSectionIndex === index }"
                @click="selectSection(index)"
              >
                <div class="nav-item-main">
                  <div class="nav-item-title">{{ section.sectionName }}</div>
                  <div class="nav-item-meta">
                    <el-icon v-if="section.content?.trim()" color="var(--app-success-color)"><CircleCheck /></el-icon>
                    <el-icon v-else-if="isRunning && section.sectionId === form.currentSectionId" class="is-loading"><Loading /></el-icon>
                    <span v-else class="status-dot"></span>
                    <span>{{ section.duration || 0 }}s</span>
                  </div>
                </div>
              </div>
            </div>
            <el-empty v-else :image-size="60" description="暂无内容" />
          </div>
        </TeacherCard>
      </aside>

      <!-- 右侧主编辑区 -->
      <main class="script-main">
        <div class="mobile-toggle" @click="sidebarVisible = !sidebarVisible">
          <el-icon><Menu /></el-icon>
          <span>{{ sidebarVisible ? '隐藏目录' : '显示目录' }}</span>
        </div>

        <TeacherCard class="editor-container-card">
          <template #header>
            <div class="editor-header">
              <div class="editor-header-left">
                <span class="editor-title">章节编辑</span>
                <span v-if="lastSavedTime" class="save-status">
                  <el-icon><CircleCheck /></el-icon> 已保存于 {{ lastSavedTime }}
                </span>
              </div>
              <div class="editor-header-actions">
                <el-button :loading="restoring" size="small" @click="loadLastResult({ forceRemote: true })">刷新</el-button>
                <el-button v-if="form.scriptId" type="primary" size="small" :disabled="!canSave" :loading="saving" @click="handleSave">
                  手动保存
                </el-button>
                <el-button type="success" size="small" :disabled="!canGoAudio" @click="goAudioPage">进入音频生成</el-button>
              </div>
            </div>
          </template>

          <template v-if="activeSection">
            <div class="section-focus-info">
              <div class="info-banner">
                <div class="banner-item">
                  <span class="label">当前章节:</span>
                  <span class="value">{{ activeSection.sectionName }}</span>
                </div>
                <div class="banner-item">
                  <span class="label">页码:</span>
                  <el-tag size="small" type="info">{{ activeSection.relatedPage || '-' }}</el-tag>
                </div>
                <div class="banner-item">
                  <span class="label">状态:</span>
                  <el-tag size="small" :type="sectionTagType(activeSection)">{{ sectionStatusLabel(activeSection) }}</el-tag>
                </div>
              </div>

              <div v-if="activeSection.keyPoints?.length" class="key-points-box">
                <span class="label">知识点：</span>
                <span v-for="point in activeSection.keyPoints" :key="point" class="key-point-tag">{{ point }}</span>
              </div>
            </div>

            <div class="editor-wrapper">
              <el-input
                v-model="activeSection.content"
                type="textarea"
                :autosize="{ minRows: 15, maxRows: 100 }"
                resize="none"
                :disabled="isRunning"
                :placeholder="sectionPlaceholder(activeSection)"
                class="modern-textarea"
              />
            </div>

          </template>

          <template v-else>
            <el-empty v-if="hasScript" description="请从左侧选择一个章节进行编辑" />
            <el-empty v-else description="请先加载或生成脚本">
              <el-button type="primary" @click="goGeneratePage">去生成</el-button>
            </el-empty>
          </template>
        </TeacherCard>

        <!-- 脚本统计卡片 -->
        <TeacherCard v-if="hasScript" title="脚本概览" class="stat-card">
          <el-descriptions :column="3" border>
            <el-descriptions-item label="脚本编号">{{ form.scriptId }}</el-descriptions-item>
            <el-descriptions-item label="讲解风格">{{ styleLabel }}</el-descriptions-item>
            <el-descriptions-item label="生成状态">{{ generationStatusLabel }}</el-descriptions-item>
            <el-descriptions-item label="总进度">{{ progressLabel }}</el-descriptions-item>
            <el-descriptions-item label="已耗时">{{ elapsedLabel }}</el-descriptions-item>
            <el-descriptions-item label="章节数">{{ form.scriptStructure.length }}</el-descriptions-item>
          </el-descriptions>
        </TeacherCard>
      </main>
    </div>
  </TeacherLayout>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheck, Loading, Menu } from '@element-plus/icons-vue'
import TeacherLayout from '@/components/teacher/TeacherLayout.vue'
import TeacherCard from '@/components/teacher/TeacherCard.vue'
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

// UI State
const sidebarVisible = ref(true)
const activeSectionIndex = ref(0)
const lastSavedTime = ref('')

let pollTimerId = null
let elapsedTimerId = null

const hasScript = computed(() => Boolean(form.scriptId) && form.scriptStructure.length > 0)
const isRunning = computed(() => form.generationStatus === 'running')
const canSave = computed(() => hasScript.value && !isRunning.value)
const activeSection = computed(() => form.scriptStructure[activeSectionIndex.value] || null)

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
      label: `${asset.chapterName || '未命名章节'} · V${asset.versionNo}`,
      finishedAt: task.finishedAt || '',
      scriptCount: task.scriptCount || 0
    }))
  )
)

watch(
  () => form.scriptId,
  () => {
    activeSectionIndex.value = 0
    lastSavedTime.value = ''
  }
)

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

  // Handle responsive
  if (window.innerWidth < 1100) {
    sidebarVisible.value = false
  }
})

onBeforeUnmount(() => {
  persistDraft()
  stopPolling()
  stopElapsedTimer()
  window.removeEventListener('beforeunload', persistDraft)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})

async function selectSection(index) {
  if (activeSectionIndex.value === index) return
  
  // Silent auto-save on switch
  await autoSave()
  
  activeSectionIndex.value = index
  
  // Mobile auto-collapse
  if (window.innerWidth < 1100) {
    sidebarVisible.value = false
  }
}

async function autoSave() {
  if (!canSave.value || isRunning.value) return

  try {
    const activeScriptId = form.scriptId
    await updateScript(activeScriptId, {
      scriptStructure: cloneSections(form.scriptStructure),
      versionRemark: 'teacher-autosave'
    })
    lastSavedTime.value = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch (error) {
    console.warn('Auto save failed:', error)
  }
}

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
    lastSavedTime.value = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    ElMessage.success('脚本已手动保存')
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
    return `${hours}h ${String(minutes).padStart(2, '0')}m ${String(seconds).padStart(2, '0')}s`
  }

  return `${String(minutes).padStart(2, '0')}m ${String(seconds).padStart(2, '0')}s`
}
</script>

<style scoped>
.script-edit-layout {
  display: flex;
  gap: 20px;
  align-items: flex-start;
  min-height: 600px;
}

.script-aside {
  width: 300px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 20px;
  transition: all 0.3s ease;
}

.aside-card {
  display: flex;
  flex-direction: column;
  margin-bottom: 0;
}

.aside-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.aside-title {
  font-weight: 600;
  color: var(--app-text-primary);
}

.aside-content {
  padding: 12px 0;
}

.version-compact-box {
  padding: 0 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-bottom: 1px solid var(--app-border-color-lighter);
  margin-bottom: 8px;
}

.compact-select {
  width: 100%;
}

.section-list {
  display: flex;
  flex-direction: column;
}

.section-nav-item {
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  border-left: 3px solid transparent;
}

.section-nav-item:hover {
  background-color: var(--app-border-color-extra-light);
}

.section-nav-item.active {
  background-color: #ecf5ff;
  border-left-color: var(--app-primary-color);
}

.nav-item-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--app-text-primary);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--app-text-secondary);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--app-border-color);
}

.script-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mobile-toggle {
  display: none;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #fff;
  border-radius: 8px;
  cursor: pointer;
  color: var(--app-primary-color);
  font-weight: 600;
  box-shadow: var(--app-shadow-light);
}

.editor-container-card {
  margin-bottom: 0;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.editor-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.editor-title {
  font-size: 18px;
  font-weight: 600;
}

.save-status {
  font-size: 12px;
  color: var(--app-success-color);
  display: flex;
  align-items: center;
  gap: 4px;
}

.editor-header-actions {
  display: flex;
  gap: 8px;
}

.section-focus-info {
  margin-bottom: 16px;
  padding: 12px;
  background: var(--app-border-color-extra-light);
  border-radius: var(--app-radius-base);
}

.info-banner {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 8px;
}

.banner-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.banner-item .label {
  color: var(--app-text-secondary);
}

.banner-item .value {
  font-weight: 600;
  color: var(--app-text-primary);
}

.key-points-box {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.key-points-box .label {
  font-size: 13px;
  color: var(--app-text-secondary);
}

.key-point-tag {
  padding: 2px 10px;
  background: #fff;
  border: 1px solid var(--app-border-color-light);
  border-radius: 999px;
  font-size: 12px;
  color: var(--app-text-regular);
}

.editor-wrapper {
  margin-top: 8px;
}

.modern-textarea :deep(.el-textarea__inner) {
  border: 1px solid var(--app-border-color-light);
  border-radius: var(--app-radius-base);
  padding: 16px;
  font-size: 15px;
  line-height: 1.6;
  color: var(--app-text-primary);
  background-color: #fafafa;
  transition: all 0.3s;
}

.modern-textarea :deep(.el-textarea__inner:focus) {
  background-color: #fff;
  border-color: var(--app-primary-color);
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.1);
}

.stat-card {
  flex-shrink: 0;
}

@media (max-width: 1100px) {
  .script-edit-layout {
    position: relative;
  }

  .script-aside {
    position: absolute;
    left: 0;
    top: 0;
    bottom: auto;
    z-index: 100;
    box-shadow: 4px 0 16px rgba(0, 0, 0, 0.1);
  }

  .script-aside.mobile-collapsed {
    transform: translateX(-105%);
  }

  .mobile-toggle {
    display: flex;
  }
}
</style>
