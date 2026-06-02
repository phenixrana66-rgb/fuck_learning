<template>
  <TeacherLayout>
    <div class="page-container">
      <!-- Left Section: Configuration -->
      <div class="config-section">
        <div class="page-card teacher-card">
          <div class="page-title">语音生成</div>

          <el-form :model="form" label-width="110px">
            <el-form-item label="当前课程">
              <el-input :model-value="currentCourse.courseName || '-'" readonly />
            </el-form-item>

            <el-form-item label="发布章节名">
              <el-input
                v-model="chapterInfo.chapterName"
                placeholder="请输入发布时使用的章节名"
                @input="handleChapterNameInput"
              />
            </el-form-item>

            <el-form-item label="解析版本">
              <el-select
                v-model="form.parseId"
                class="full-width"
                placeholder="请选择解析版本"
                :loading="loadingHistory"
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

            <el-form-item label="讲稿版本">
              <el-select
                v-model="form.scriptId"
                class="full-width"
                placeholder="请选择脚本版本"
                :disabled="!form.parseId"
                @change="handleScriptChange"
              >
                <el-option
                  v-for="item in parseScripts"
                  :key="item.scriptId"
                  :label="`${item.scriptId} · ${scriptStatusText(item.scriptStatus)} · ${styleText(item.teachingStyle)}`"
                  :value="item.scriptId"
                />
              </el-select>
            </el-form-item>

            <el-form-item v-if="selectedScriptMeta" label="当前脚本">
              <div class="version-summary">
                <div>脚本：{{ selectedScriptMeta.scriptId }}</div>
                <div>风格：{{ styleText(selectedScriptMeta.teachingStyle) }} · 音频数：{{ selectedScriptMeta.audioCount || 0 }}</div>
                <div>状态：{{ scriptStatusText(selectedScriptMeta.scriptStatus) }}</div>
              </div>
            </el-form-item>

            <el-form-item label="音色选择">
              <el-radio-group v-model="form.voiceType" class="card-radio-group" :disabled="loading">
                <el-radio v-for="voice in voiceOptions" :key="voice.value" :label="voice.value" class="card-radio">
                  <div class="card-radio-content">
                    <el-icon class="card-icon"><component :is="voice.icon" /></el-icon>
                    <div class="card-info">
                      <div class="card-label">{{ voice.label }}</div>
                      <div class="card-desc">{{ voice.desc }}</div>
                    </div>
                  </div>
                </el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" :loading="loading" @click="handleGenerateAudio">
                生成音频
              </el-button>
              <el-button :disabled="!form.scriptId || loading" @click="openScript">
                脚本编辑
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </div>

      <!-- Right Section: Status & History -->
      <div class="status-section">
        <!-- Audio Preview & Publish -->
        <div v-if="form.audioUrl" class="page-card teacher-card preview-card">
          <div class="sub-title">
            <el-icon><Headset /></el-icon>音频预览
          </div>

          <el-descriptions :column="1" border>
            <el-descriptions-item label="音频ID">{{ form.audioId || '-' }}</el-descriptions-item>
            <el-descriptions-item label="音色">{{ selectedVoiceLabel }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="publishInfo.status === 'published' ? 'success' : 'primary'" size="small">
                {{ publishInfo.status === 'published' ? '已发布' : (form.status || '已生成') }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>

          <audio class="audio-preview" :src="form.audioUrl" controls />

          <div class="toolbar" style="margin-top: 16px;">
            <el-button 
              :type="publishInfo.status === 'published' ? 'info' : 'success'" 
              class="full-width" 
              :loading="publishing" 
              :disabled="publishInfo.status === 'published'"
              @click="publishLesson"
            >
              {{ publishInfo.status === 'published' ? '课程已发布' : '发布课程' }}
            </el-button>
          </div>
        </div>

        <!-- Task Status -->
        <div v-if="loading || errorCode" class="page-card teacher-card status-card">
          <div class="sub-title">任务状态</div>
          
          <div v-if="loading" class="progress-wrapper">
            <el-progress 
              type="dashboard" 
              :percentage="loading ? 50 : 0" 
              :status="loading ? '' : 'success'"
              :stroke-width="10"
              :width="120"
            >
              <template #default>
                <div class="progress-text">
                  <span class="percentage-value">...</span>
                  <span class="percentage-label">生成中</span>
                </div>
              </template>
            </el-progress>
          </div>

          <el-descriptions :column="1" border>
            <el-descriptions-item label="状态">
              <el-tag :type="loading ? 'primary' : (errorCode ? 'danger' : 'success')">
                {{ loading ? '生成中' : (errorCode ? '失败' : '空闲') }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="耗时">{{ elapsedLabel }}</el-descriptions-item>
          </el-descriptions>

          <ErrorTip
            v-if="errorCode"
            :code="errorCode"
            :message="errorMsg"
            @retry="handleGenerateAudio"
          />
        </div>

        <!-- History Audios -->
        <div v-if="audioHistory.length" class="page-card teacher-card history-card">
          <div class="sub-title">已有音频</div>
          <el-table :data="audioHistory" border size="small">
            <el-table-column prop="voiceType" label="音色" width="100">
              <template #default="{ row }">
                {{ voiceText(row.voiceType) }}
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 'published' ? 'success' : 'info'" size="small">
                  {{ audioStatusText(row.status).substring(0, 1) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" min-width="80">
              <template #default="{ row }">
                <el-button type="primary" link @click="useExistingAudio(row)">使用</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-if="publishInfo.status === 'published'" class="page-card teacher-card">
          <el-result
            icon="success"
            title="已发布"
            sub-title="课程已成功发布"
            style="padding: 10px 0;"
          />
        </div>
      </div>
    </div>

    <Loading :visible="loading" :text="`正在生成音频，已耗时 ${elapsedLabel}`" />
  </TeacherLayout>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Female, Male, Headset } from '@element-plus/icons-vue'
import TeacherLayout from '@/components/teacher/TeacherLayout.vue'
import Loading from '@/components/teacher/Loading.vue'
import ErrorTip from '@/components/teacher/ErrorTip.vue'
import { generateAudio, getCoursewareAssets, getLessonStatus, getParseScripts, getParseStatusAPI, getScriptAudios, publishLesson as publishLessonAPI } from '@/api/teacher'
import {
  getAudioResult,
  getCurrentCourse,
  getParseResult,
  getScriptResult,
  getTeacherProfile,
  getTeacherWorkspaceContext,
  patchTeacherWorkspaceContext,
  saveAudioResult,
  saveParseResult
} from '@/utils/platform'

const router = useRouter()
const currentCourse = getCurrentCourse()
const teacherInfo = getTeacherProfile()
const parseResult = getParseResult()
const scriptResult = getScriptResult()
const audioResult = getAudioResult()
const initialWorkspaceContext = getTeacherWorkspaceContext(currentCourse.courseId)
const readWorkspaceContext = () => getTeacherWorkspaceContext(currentCourse.courseId)

const voiceOptions = [
  { label: '女声标准', value: 'female_standard', desc: '清晰中性，适合日常。', icon: Female },
  { label: '男声标准', value: 'male_standard', desc: '声音稳定，适合技术。', icon: Male },
  { label: '女声温暖', value: 'female_warm', desc: '柔和声音，适合引导。', icon: Female },
  { label: '男声深沉', value: 'male_deep', desc: '低沉音调，适合演示。', icon: Male }
]

const voiceList = voiceOptions

const form = ref({
  parseId: initialWorkspaceContext.parseId || scriptResult.parseId || parseResult.parseId || '',
  scriptId: initialWorkspaceContext.scriptId || scriptResult.scriptId || '',
  voiceType: initialWorkspaceContext.voiceType || audioResult.voiceType || 'female_standard',
  audioId: initialWorkspaceContext.audioId || audioResult.audioId || '',
  audioUrl: initialWorkspaceContext.audioUrl || audioResult.audioUrl || '',
  status: initialWorkspaceContext.audioStatus || audioResult.status || ''
})

const chapterInfo = ref({
  chapterId: initialWorkspaceContext.chapterId || '',
  chapterName: initialWorkspaceContext.chapterName || ''
})
const publishInfo = ref({
  published: Boolean(audioResult.lessonId),
  lessonId: audioResult.lessonId || '',
  publishId: audioResult.publishId || '',
  status: audioResult.publishStatus || ''
})
const assetHistory = ref([])
const parseScripts = ref([])
const audioHistory = ref([])
const loading = ref(false)
const loadingHistory = ref(false)
const publishing = ref(false)
const errorCode = ref('')
const errorMsg = ref('')
const elapsedSeconds = ref(0)
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
      label: `${asset.chapterName || '未命名章节'} · V${asset.versionNo} · ${asset.fileName} · ${parseStatusText(task.taskStatus)} · ${task.parseId}`
    }))
  )
)
const selectedParseMeta = computed(() => parseOptions.value.find((item) => item.parseId === form.value.parseId) || null)
const selectedScriptMeta = computed(() => parseScripts.value.find((item) => item.scriptId === form.value.scriptId) || null)
const selectedVoiceLabel = computed(() => voiceList.find((item) => item.value === form.value.voiceType)?.label || '-')
const elapsedLabel = computed(() => formatElapsed(elapsedSeconds.value))

onMounted(async () => {
  await initializePage()
})

onBeforeUnmount(() => {
  stopTimer()
})

async function initializePage() {
  if (!currentCourse.courseId) return
  await refreshStatus()
  await loadCoursewareHistory()
}

async function refreshStatus() {
  if (!currentCourse.courseId) return
  try {
    const res = await getLessonStatus({ courseId: currentCourse.courseId })
    const data = res.data || {}
    publishInfo.value.status = data.publish?.status || publishInfo.value.status
    publishInfo.value.publishedAt = data.publish?.publishedAt || ''
    publishInfo.value.chapterName = data.chapterName || publishInfo.value.chapterName || ''
    publishInfo.value.lessonId = publishInfo.value.lessonId || data.publish?.lessonNo || ''
  } catch (_error) {
    // 保持静默，历史版本接口会继续尝试兜底
  }
}

async function loadCoursewareHistory() {
  loadingHistory.value = true
  try {
    const res = await getCoursewareAssets({
      courseId: currentCourse.courseId
    })
    const data = res.data || {}
    assetHistory.value = data.assets || []

    const preferredParseId = resolvePreferredParseId(
      parseOptions.value,
      readWorkspaceContext().parseId || form.value.parseId || ''
    )
    if (preferredParseId) {
      form.value.parseId = preferredParseId
      await syncParseSelection(preferredParseId, {
        preserveScript: true,
        preserveAudio: true,
        silent: true
      })
    }
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || '读取历史课件版本失败'
  } finally {
    loadingHistory.value = false
  }
}

async function handleParseChange(parseId) {
  await syncParseSelection(parseId, { preserveScript: false, preserveAudio: false })
}

async function syncParseSelection(parseId, options = {}) {
  const { preserveScript = false, preserveAudio = false, silent = false } = options
  form.value.parseId = parseId || ''
  const meta = parseOptions.value.find((item) => item.parseId === form.value.parseId) || null
  chapterInfo.value = {
    chapterId: meta?.chapterId || '',
    chapterName: meta?.chapterName || ''
  }
  const workspaceContext = readWorkspaceContext()
  const preferredScriptId = preserveScript ? workspaceContext.scriptId || form.value.scriptId || '' : ''
  const preferredAudioId = preserveAudio ? workspaceContext.audioId || form.value.audioId || '' : ''
  patchTeacherWorkspaceContext(currentCourse.courseId, {
    chapterId: meta?.chapterId || '',
    chapterName: meta?.chapterName || '',
    parseId: form.value.parseId,
    assetId: meta?.assetId || '',
    fileName: meta?.fileName || '',
    versionNo: meta?.versionNo || null,
    scriptId: preferredScriptId,
    audioId: preferredAudioId
  })
  await loadScriptsForParse(form.value.parseId, preferredScriptId, preferredAudioId)
  if (!silent && selectedParseMeta.value) {
    ElMessage.success(`已切换到课件 V${selectedParseMeta.value.versionNo}`)
  }
}

async function loadScriptsForParse(parseId, preferredScriptId = '', preferredAudioId = '') {
  parseScripts.value = []
  audioHistory.value = []
  form.value.scriptId = ''
  clearSelectedAudio()
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
    const nextScriptId = resolvePreferredScriptId(parseScripts.value, preferredScriptId)
    if (nextScriptId) {
      form.value.scriptId = nextScriptId
      await loadAudiosForScript(nextScriptId, preferredAudioId)
    }
    patchTeacherWorkspaceContext(currentCourse.courseId, {
      chapterId: chapterInfo.value.chapterId,
      chapterName: chapterInfo.value.chapterName,
      parseId,
      scriptId: nextScriptId,
      audioId: ''
    })
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || '读取脚本列表失败'
  }
}

async function handleScriptChange(scriptId) {
  patchTeacherWorkspaceContext(currentCourse.courseId, {
    parseId: form.value.parseId,
    scriptId,
    audioId: '',
    audioUrl: '',
    audioStatus: ''
  })
  await loadAudiosForScript(scriptId, '')
}

async function loadAudiosForScript(scriptId, preferredAudioId = '') {
  audioHistory.value = []
  clearSelectedAudio()
  if (!scriptId) {
    return
  }
  try {
    const res = await getScriptAudios(scriptId)
    const data = res.data || {}
    audioHistory.value = data.audios || []
    const preferred = audioHistory.value.find((item) => item.audioId === preferredAudioId)
    if (preferred) {
      useExistingAudio(preferred, { silent: true })
    } else if (audioHistory.value.length) {
      useExistingAudio(audioHistory.value[0], { silent: true })
    }
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || '读取音频列表失败'
  }
}

async function handleGenerateAudio() {
  if (!form.value.scriptId) {
    ElMessage.warning('请先选择一份脚本。')
    return
  }

  resetElapsed()
  loading.value = true
  errorCode.value = ''
  errorMsg.value = ''
  startTimer()

  try {
    const res = await generateAudio({
      scriptId: form.value.scriptId,
      voiceType: form.value.voiceType,
      audioFormat: 'mp3',
      sectionIds: []
    })

    const data = res.data || {}
    form.value.audioId = data.audioId || ''
    form.value.audioUrl = data.audioUrl || ''
    form.value.status = data.taskStatus || data.status || 'success'

    saveAudioResult({
      ...data,
      parseId: form.value.parseId,
      scriptId: form.value.scriptId,
      voiceType: form.value.voiceType,
      status: form.value.status,
      elapsedSeconds: elapsedSeconds.value,
      lessonId: '',
      publishId: '',
      publishStatus: ''
    })
    patchTeacherWorkspaceContext(currentCourse.courseId, {
      chapterId: chapterInfo.value.chapterId,
      chapterName: chapterInfo.value.chapterName,
      parseId: form.value.parseId,
      assetId: selectedParseMeta.value?.assetId || '',
      fileName: selectedParseMeta.value?.fileName || '',
      versionNo: selectedParseMeta.value?.versionNo || null,
      scriptId: form.value.scriptId,
      audioId: form.value.audioId,
      audioUrl: form.value.audioUrl,
      audioStatus: form.value.status,
      voiceType: form.value.voiceType
    })
    await loadAudiosForScript(form.value.scriptId, form.value.audioId)

    ElMessage.success('音频生成完成。')
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || 'Failed to generate audio'
  } finally {
    stopTimer()
    loading.value = false
  }
}

function useExistingAudio(row, options = {}) {
  const { silent = false } = options
  form.value.audioId = row.audioId || ''
  form.value.audioUrl = row.audioUrl || ''
  form.value.status = row.status || 'generated'
  patchTeacherWorkspaceContext(currentCourse.courseId, {
    parseId: form.value.parseId,
    scriptId: form.value.scriptId,
    audioId: form.value.audioId,
    audioUrl: form.value.audioUrl,
    audioStatus: form.value.status,
    voiceType: form.value.voiceType
  })
  if (!silent) {
    ElMessage.success('已切换为历史音频版本')
  }
}

function clearSelectedAudio() {
  form.value.audioId = ''
  form.value.audioUrl = ''
  form.value.status = ''
}

function openScript() {
  if (!form.value.scriptId) {
    ElMessage.warning('请先选择脚本')
    return
  }
  patchTeacherWorkspaceContext(currentCourse.courseId, {
    parseId: form.value.parseId,
    scriptId: form.value.scriptId,
    audioId: form.value.audioId,
    audioUrl: form.value.audioUrl,
    audioStatus: form.value.status
  })
  router.push({
    path: '/teacher/script-edit',
    query: { scriptId: form.value.scriptId }
  })
}

async function publishLesson() {
  if (!form.value.audioId) {
    ElMessage.warning('请先生成音频或选择已有音频。')
    return
  }

  if (!String(chapterInfo.value.chapterName || '').trim()) {
    ElMessage.warning('请输入发布章节名。')
    return
  }

  const coursewareId = await resolveCoursewareId()
  if (!coursewareId) {
    ElMessage.warning('缺少 coursewareId，请先确认解析版本是否可用。')
    return
  }

  publishing.value = true

  try {
    const res = await publishLessonAPI({
      coursewareId,
      scriptId: form.value.scriptId,
      audioId: form.value.audioId,
      publisherId: teacherInfo.teacherId || teacherInfo.userId || '',
      chapterName: chapterInfo.value.chapterName
    })

    const data = res.data || {}
    publishInfo.value = {
      published: data.publishStatus === 'published',
      lessonId: data.lessonId || '',
      publishId: data.publishId || '',
      status: data.publishStatus || ''
    }

    saveAudioResult({
      ...audioResult,
      audioId: form.value.audioId,
      audioUrl: form.value.audioUrl,
      parseId: form.value.parseId,
      scriptId: form.value.scriptId,
      voiceType: form.value.voiceType,
      status: form.value.status,
      lessonId: data.lessonId || '',
      publishId: data.publishId || '',
      publishStatus: data.publishStatus || ''
    })

    ElMessage.success(`Lesson published successfully: ${data.lessonId || '-'}`)
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || 'Failed to publish lesson'
  } finally {
    publishing.value = false
  }
}

function handleChapterNameInput() {
  patchTeacherWorkspaceContext(currentCourse.courseId, {
    chapterId: chapterInfo.value.chapterId,
    chapterName: chapterInfo.value.chapterName
  })
}

async function resolveCoursewareId() {
  const parseId = form.value.parseId || scriptResult.parseId || parseResult.parseId
  if (!parseId) {
    return ''
  }

  try {
    const res = await getParseStatusAPI(parseId)
    const data = res.data || {}
    if (data.coursewareId) {
      saveParseResult({
        ...parseResult,
        ...data,
        parseId
      })
      patchTeacherWorkspaceContext(currentCourse.courseId, {
        parseId,
        coursewareId: data.coursewareId
      })
      return data.coursewareId
    }
  } catch (_error) {
    return ''
  }

  return readWorkspaceContext().coursewareId || ''
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

function audioStatusText(status) {
  const map = {
    generated: '已生成',
    published: '已发布'
  }
  return map[status] || status || '-'
}

function styleText(type) {
  const map = {
    standard: '标准',
    detailed: '详细',
    concise: '简洁'
  }
  return map[type] || '-'
}

function voiceText(type) {
  return voiceList.find((item) => item.value === type)?.label || type || '-'
}

function startTimer() {
  stopTimer()
  timerId = window.setInterval(() => {
    elapsedSeconds.value += 1
  }, 1000)
}

function stopTimer() {
  if (timerId) {
    window.clearInterval(timerId)
    timerId = null
  }
}

function resetElapsed() {
  elapsedSeconds.value = 0
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

.status-card, .history-card, .preview-card {
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
  grid-template-columns: repeat(2, 1fr);
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

.audio-preview {
  width: 100%;
  margin-top: 16px;
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
