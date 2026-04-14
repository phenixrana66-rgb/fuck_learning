<template>
  <TeacherLayout>
    <div class="page-card teacher-card">
      <div class="page-title">音频生成</div>

      <el-form :model="form" label-width="110px" class="teacher-form">
        <el-form-item label="当前课程">
          <el-input :model-value="currentCourse.courseName || '-'" readonly />
        </el-form-item>
        <el-form-item label="讲稿 ID">
          <el-input v-model="form.scriptId" readonly />
        </el-form-item>
        <el-form-item label="音色选择">
          <div class="voice-grid">
            <button
              v-for="voice in voiceList"
              :key="voice.value"
              type="button"
              class="voice-card"
              :class="{ active: form.voiceType === voice.value }"
              @click="form.voiceType = voice.value"
            >
              <div class="voice-label">{{ voice.label }}</div>
              <div class="voice-desc">{{ voice.desc }}</div>
            </button>
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleGenerateAudio">生成音频</el-button>
          <el-button @click="refreshStatus">刷新状态</el-button>
        </el-form-item>
      </el-form>

      <Loading :visible="loading || publishing" :text="publishing ? '正在发布智课…' : '正在生成音频…'" />
      <ErrorTip v-if="errorCode" :code="errorCode" :message="errorMsg" @retry="refreshStatus" />
    </div>

    <div v-if="form.audioUrl" class="page-card teacher-card">
      <div class="sub-title">音频预览与发布</div>

      <div class="teacher-audio-meta">
        <div class="info-item">
          <div class="info-label">音频 ID</div>
          <div class="info-value">{{ form.audioId || '-' }}</div>
        </div>
        <div class="info-item">
          <div class="info-label">音色</div>
          <div class="info-value">{{ selectedVoiceLabel }}</div>
        </div>
        <div class="info-item">
          <div class="info-label">状态</div>
          <div class="info-value">{{ form.status || '-' }}</div>
        </div>
      </div>

      <audio class="audio-preview" :src="form.audioUrl" controls />

      <div class="toolbar" style="margin-top: 18px;">
        <el-button type="success" :loading="publishing" @click="handlePublish">发布智课</el-button>
      </div>
    </div>

    <div v-if="publishInfo.status === 'published'" class="page-card teacher-card">
      <el-result
        icon="success"
        title="智课发布完成"
        :sub-title="`章节：${publishInfo.chapterName || '-'}，发布时间：${publishInfo.publishedAt || '-'}`"
      />
    </div>
  </TeacherLayout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import TeacherLayout from '@/components/teacher/TeacherLayout.vue'
import Loading from '@/components/teacher/Loading.vue'
import ErrorTip from '@/components/teacher/ErrorTip.vue'
import { generateAudio, getLessonStatus, publishLesson } from '@/api/teacher'
import { getCurrentCourse, getScriptResult, saveAudioResult } from '@/utils/platform'

const currentCourse = getCurrentCourse()
const localScript = getScriptResult()

const voiceList = [
  { label: '女声·标准', value: 'female_standard', desc: '清晰自然，适合常规授课。' },
  { label: '男声·标准', value: 'male_standard', desc: '稳重清晰，适合理工类课程。' },
  { label: '女声·亲和', value: 'female_warm', desc: '语气柔和，适合导学内容。' },
  { label: '男声·磁性', value: 'male_deep', desc: '沉稳集中，适合公开讲解。' }
]

const form = ref({
  scriptId: localScript.scriptId || '',
  voiceType: 'female_standard',
  audioId: '',
  audioUrl: '',
  status: ''
})

const chapterInfo = ref({
  chapterId: '',
  chapterName: ''
})
const publishInfo = ref({
  status: '',
  chapterName: '',
  publishedAt: ''
})

const loading = ref(false)
const publishing = ref(false)
const errorCode = ref('')
const errorMsg = ref('')

const selectedVoiceLabel = computed(() => voiceList.find((item) => item.value === form.value.voiceType)?.label || '-')

onMounted(() => {
  refreshStatus()
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
    ElMessage.warning('请先完成讲稿生成。')
    return
  }

  loading.value = true
  errorCode.value = ''
  errorMsg.value = ''

  try {
    const res = await generateAudio({
      scriptId: form.value.scriptId,
      courseId: currentCourse.courseId,
      voiceType: form.value.voiceType
    })

    const data = res.data || {}
    form.value.audioId = data.audioId || ''
    form.value.audioUrl = data.audioUrl || ''
    form.value.status = data.status || 'generated'

    saveAudioResult({
      ...data,
      scriptId: form.value.scriptId,
      voiceType: form.value.voiceType
    })

    ElMessage.success('音频生成完成。')
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || '音频生成失败。'
  } finally {
    loading.value = false
  }
}

async function handlePublish() {
  if (!form.value.audioId) {
    ElMessage.warning('请先生成音频。')
    return
  }
  if (!chapterInfo.value.chapterId) {
    ElMessage.warning('当前课程还没有可发布的章节。')
    return
  }

  publishing.value = true
  errorCode.value = ''
  errorMsg.value = ''
  try {
    const res = await publishLesson({
      courseId: currentCourse.courseId,
      chapterId: chapterInfo.value.chapterId
    })
    const data = res.data || {}
    publishInfo.value.status = data.publishStatus || 'published'
    publishInfo.value.chapterName = data.chapterName || chapterInfo.value.chapterName
    publishInfo.value.publishedAt = data.publishedAt || ''
    form.value.status = 'published'
    ElMessage.success('智课已发布到学生端。')
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || '智课发布失败。'
  } finally {
    publishing.value = false
  }
}
</script>

<style scoped>
.teacher-card {
  border-radius: 22px;
  border: 1px solid #e7eef9;
  box-shadow: 0 16px 36px rgba(53, 82, 136, 0.08);
}

.teacher-form {
  max-width: 940px;
}

.voice-grid {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.voice-card {
  border: 1px solid #e4ecfa;
  border-radius: 16px;
  padding: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  text-align: left;
  cursor: pointer;
  transition: border-color 0.18s ease, transform 0.18s ease, background 0.18s ease;
}

.voice-card:hover {
  border-color: #7d9fe8;
}

.voice-card.active {
  border-color: #5b83dd;
  background: linear-gradient(135deg, #edf4ff 0%, #e2edff 100%);
}

.voice-label {
  color: #1f3b70;
  font-size: 15px;
  font-weight: 600;
}

.voice-desc {
  margin-top: 6px;
  color: #7e91b2;
  font-size: 12px;
  line-height: 1.7;
}

.teacher-audio-meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(180px, 1fr));
  gap: 16px;
}

.audio-preview {
  width: 100%;
  margin-top: 18px;
}
</style>
