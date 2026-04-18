<template>
  <TeacherLayout>
    <div class="page-card">
      <div class="page-title">Audio Generate</div>

      <el-form :model="form" label-width="110px" class="teacher-form">
        <el-form-item label="当前课程">
          <el-input :model-value="currentCourse.courseName || '-'" readonly />
        </el-form-item>
        <el-form-item label="讲稿 ID">
          <el-input v-model="form.scriptId" readonly />
        </el-form-item>

        <el-form-item label="Voice">
          <div class="voice-grid">
            <div
              v-for="voice in voiceList"
              :key="voice.value"
              type="button"
              class="voice-card"
              :class="{ active: form.voiceType === voice.value }"
              @click="form.voiceType = voice.value"
            >
              <div class="voice-title">{{ voice.label }}</div>
              <div class="voice-desc">{{ voice.desc }}</div>
            </div>
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleGenerateAudio">
            Generate Audio
          </el-button>
        </el-form-item>
      </el-form>

      <div v-if="loading" class="status-panel">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          :title="`Audio generation in progress, processed ${elapsedLabel}`"
        />
      </div>

      <Loading :visible="loading" :text="`Generating audio, elapsed ${elapsedLabel}`" />

      <ErrorTip
        v-if="errorCode"
        :code="errorCode"
        :message="errorMsg"
        @retry="handleGenerateAudio"
      />
    </div>

    <div class="page-card" v-if="form.audioUrl">
      <div class="sub-title">Audio Preview</div>

      <el-descriptions :column="1" border>
        <el-descriptions-item label="audioId">{{ form.audioId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="Voice">{{ selectedVoiceLabel }}</el-descriptions-item>
        <el-descriptions-item label="Status">
          <el-tag type="success">{{ form.status || 'success' }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <audio class="audio-preview" :src="form.audioUrl" controls />

      <div class="toolbar" style="margin-top: 16px;">
        <el-button type="success" :loading="publishing" @click="publishLesson">
          Publish Lesson
        </el-button>
      </div>
    </div>

    <div v-if="publishInfo.status === 'published'" class="page-card teacher-card">
      <el-result
        icon="success"
        title="Lesson Published"
        :sub-title="`Course: ${currentCourse.courseName || '-'}, lesson: ${publishInfo.lessonId || '-'}, audio: ${form.audioId || '-'}`"
      />
    </div>
  </TeacherLayout>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import TeacherLayout from '@/components/teacher/TeacherLayout.vue'
import Loading from '@/components/teacher/Loading.vue'
import ErrorTip from '@/components/teacher/ErrorTip.vue'
import { generateAudio, getParseStatusAPI, publishLesson as publishLessonAPI } from '@/api/teacher'
import { getAudioResult, getCurrentCourse, getParseResult, getScriptResult, getTeacherProfile, saveAudioResult, saveParseResult } from '@/utils/platform'

const currentCourse = getCurrentCourse()
const teacherInfo = getTeacherProfile()
const parseResult = getParseResult()
const scriptResult = getScriptResult()
const audioResult = getAudioResult()
const cachedAudioResult = audioResult.scriptId === scriptResult.scriptId ? audioResult : {}

const voiceList = [
  { label: 'Female Standard', value: 'female_standard', desc: 'Clear and neutral for everyday teaching.' },
  { label: 'Male Standard', value: 'male_standard', desc: 'Stable voice for technical topics.' },
  { label: 'Female Warm', value: 'female_warm', desc: 'Softer voice for guided lessons.' },
  { label: 'Male Deep', value: 'male_deep', desc: 'Lower tone for presentation style delivery.' }
]

const form = ref({
  scriptId: scriptResult.scriptId || '',
  voiceType: cachedAudioResult.voiceType || 'female_standard',
  audioId: cachedAudioResult.audioId || '',
  audioUrl: cachedAudioResult.audioUrl || '',
  status: cachedAudioResult.status || ''
})

const chapterInfo = ref({
  chapterId: '',
  chapterName: ''
})
const publishInfo = ref({
  published: Boolean(cachedAudioResult.lessonId),
  lessonId: cachedAudioResult.lessonId || '',
  publishId: cachedAudioResult.publishId || ''
})

const loading = ref(false)
const publishing = ref(false)
const errorCode = ref('')
const errorMsg = ref('')
const elapsedSeconds = ref(0)
let timerId = null

const selectedVoiceLabel = computed(() => voiceList.find((item) => item.value === form.value.voiceType)?.label || '-')

onMounted(() => {
  refreshStatus()
})
const elapsedLabel = computed(() => formatElapsed(elapsedSeconds.value))

onBeforeUnmount(() => {
  stopTimer()
})

async function refreshStatus() {
  if (!currentCourse.courseId) return
  try {
    const res = await getLessonStatus({ courseId: currentCourse.courseId })
    const data = res.data || {}
    chapterInfo.value.chapterId = data.chapterId || ''
    chapterInfo.value.chapterName = data.chapterName || ''
    form.value.scriptId = form.value.scriptId || data.script?.scriptId || ''
    form.value.audioId = data.audio?.audioId || form.value.audioId
    form.value.audioUrl = data.audio?.audioUrl || form.value.audioUrl
    form.value.status = data.audio?.status || form.value.status
    publishInfo.value.status = data.publish?.status || ''
    publishInfo.value.publishedAt = data.publish?.publishedAt || ''
    publishInfo.value.chapterName = data.chapterName || ''
  } catch (_error) {
    // 刷新失败不阻断页面使用
  }
}

async function handleGenerateAudio() {
  if (!form.value.scriptId) {
    ElMessage.warning('Generate a script first')
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
      scriptId: form.value.scriptId,
      voiceType: form.value.voiceType,
      status: form.value.status,
      elapsedSeconds: elapsedSeconds.value,
      lessonId: '',
      publishId: '',
      publishStatus: ''
    })

    ElMessage.success('音频生成完成。')
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || 'Failed to generate audio'
  } finally {
    stopTimer()
    loading.value = false
  }
}

async function publishLesson() {
  if (!form.value.audioId) {
    ElMessage.warning('Generate audio first')
    return
  }

  const coursewareId = await resolveCoursewareId()
  if (!coursewareId) {
    ElMessage.warning('Missing coursewareId, please re-run course parse first')
    return
  }

  publishing.value = true

  try {
    const res = await publishLessonAPI({
      coursewareId,
      scriptId: form.value.scriptId,
      audioId: form.value.audioId,
      publisherId: teacherInfo.teacherId || teacherInfo.userId || ''
    })

    const data = res.data || {}
    publishInfo.value = {
      published: data.publishStatus === 'published',
      lessonId: data.lessonId || '',
      publishId: data.publishId || ''
    }

    saveAudioResult({
      ...cachedAudioResult,
      audioId: form.value.audioId,
      audioUrl: form.value.audioUrl,
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

async function resolveCoursewareId() {
  if (parseResult.coursewareId) {
    return parseResult.coursewareId
  }

  const parseId = scriptResult.parseId || parseResult.parseId
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
      return data.coursewareId
    }
  } catch (error) {
    return ''
  }

  return ''
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
    return `${hours}h ${String(minutes).padStart(2, '0')}m ${String(seconds).padStart(2, '0')}s`
  }

  return `${String(minutes).padStart(2, '0')}m ${String(seconds).padStart(2, '0')}s`
}
</script>

<style scoped>
.status-panel {
  margin-bottom: 16px;
}

.voice-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  width: 100%;
}

.voice-card {
  border: 1px solid #dcdfe6;
  border-radius: 12px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.voice-card.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.voice-title {
  font-weight: 600;
}

.voice-desc {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
}
</style>
