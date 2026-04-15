<template>
  <TeacherLayout>
    <div class="page-card">
      <div class="page-title">Audio Generate</div>

      <el-form :model="form" label-width="110px">
        <el-form-item label="scriptId">
          <el-input v-model="form.scriptId" readonly />
        </el-form-item>

        <el-form-item label="Voice">
          <div class="voice-grid">
            <div
              v-for="voice in voiceList"
              :key="voice.value"
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

      <Loading :visible="loading" text="Generating audio, please wait..." />

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
        <el-button type="success" @click="publishLesson">Publish Lesson</el-button>
      </div>
    </div>

    <div class="page-card" v-if="publishInfo.published">
      <el-result
        icon="success"
        title="Lesson Published"
        :sub-title="`Course: ${currentCourse.courseName || '-'}, audio: ${form.audioId || '-'}`"
      />
    </div>
  </TeacherLayout>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import TeacherLayout from '@/components/teacher/TeacherLayout.vue'
import Loading from '@/components/teacher/Loading.vue'
import ErrorTip from '@/components/teacher/ErrorTip.vue'
import { generateAudio } from '@/api/teacher'
import { getCurrentCourse, getScriptResult, saveAudioResult } from '@/utils/platform'

const currentCourse = getCurrentCourse()
const scriptResult = getScriptResult()

const voiceList = [
  { label: 'Female Standard', value: 'female_standard', desc: 'Clear and neutral for everyday teaching.' },
  { label: 'Male Standard', value: 'male_standard', desc: 'Stable voice for technical topics.' },
  { label: 'Female Warm', value: 'female_warm', desc: 'Softer voice for guided lessons.' },
  { label: 'Male Deep', value: 'male_deep', desc: 'Lower tone for presentation style delivery.' }
]

const form = ref({
  scriptId: scriptResult.scriptId || '',
  voiceType: 'female_standard',
  audioId: '',
  audioUrl: '',
  status: ''
})

const publishInfo = ref({
  published: false
})

const loading = ref(false)
const errorCode = ref('')
const errorMsg = ref('')

const selectedVoiceLabel = computed(() => {
  return voiceList.find((item) => item.value === form.value.voiceType)?.label || '-'
})

async function handleGenerateAudio() {
  if (!form.value.scriptId) {
    ElMessage.warning('Generate a script first')
    return
  }

  loading.value = true
  errorCode.value = ''
  errorMsg.value = ''

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
      status: form.value.status
    })
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || 'Failed to generate audio'
  } finally {
    loading.value = false
  }
}

function publishLesson() {
  if (!form.value.audioId) {
    ElMessage.warning('Generate audio first')
    return
  }

  publishInfo.value = {
    published: true,
    courseId: currentCourse.courseId,
    audioId: form.value.audioId
  }

  ElMessage.success('Lesson has been bound to the course and published')
}
</script>

<style scoped>
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
