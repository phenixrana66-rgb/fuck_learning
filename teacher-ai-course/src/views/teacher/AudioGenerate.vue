<template>
  <TeacherLayout>
    <div class="page-card">
      <div class="page-title">语音合成</div>

      <el-form :model="form" label-width="110px">
        <el-form-item label="scriptId">
          <el-input v-model="form.scriptId" readonly />
        </el-form-item>

        <el-form-item label="音色选择">
          <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; width: 100%;">
            <div
              v-for="voice in voiceList"
              :key="voice.value"
              class="voice-card"
              :class="{ active: form.voiceType === voice.value }"
              @click="form.voiceType = voice.value"
            >
              <div style="font-weight: 600;">{{ voice.label }}</div>
              <div style="font-size: 12px; color: #909399; margin-top: 6px;">{{ voice.desc }}</div>
            </div>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleGenerateAudio">
            生成音频
          </el-button>
        </el-form-item>
      </el-form>

      <Loading :visible="loading" text="语音合成中，请稍候..." />

      <ErrorTip
        v-if="errorCode"
        :code="errorCode"
        :message="errorMsg"
        @retry="handleGenerateAudio"
      />
    </div>

    <div class="page-card" v-if="form.audioUrl">
      <div class="sub-title">音频预览</div>

      <el-descriptions :column="1" border>
        <el-descriptions-item label="audioId">{{ form.audioId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="音色">{{ selectedVoiceLabel }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag type="success">{{ form.status || 'success' }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <audio class="audio-preview" :src="form.audioUrl" controls />

      <div class="toolbar" style="margin-top: 16px;">
        <el-button type="success" @click="publishLesson">智课发布</el-button>
      </div>
    </div>

    <div class="page-card" v-if="publishInfo.published">
      <el-result
        icon="success"
        title="智课发布完成"
        :sub-title="`课程：${currentCourse.courseName || '-'}，音频：${form.audioId || '-'}`"
      />
    </div>
  </TeacherLayout>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import TeacherLayout from '@/components/teacher/TeacherLayout.vue'
import Loading from '@/components/teacher/Loading.vue'
import ErrorTip from '@/components/teacher/ErrorTip.vue'
import { generateAudio } from '@/api/teacher'
import {
  getCurrentCourse,
  getScriptResult,
  saveAudioResult
} from '@/utils/platform'

const currentCourse = getCurrentCourse()
const scriptResult = getScriptResult()

const voiceList = [
  { label: '女声-标准', value: 'female_standard', desc: '清晰自然，适合常规讲解' },
  { label: '男声-标准', value: 'male_standard', desc: '沉稳清晰，适合理工课程' },
  { label: '女声-亲和', value: 'female_warm', desc: '亲和柔和，适合文科课程' },
  { label: '男声-磁性', value: 'male_deep', desc: '磁性稳重，适合公开课' }
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
    ElMessage.warning('请先完成脚本生成')
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
    form.value.status = data.status || 'success'

    saveAudioResult({
      ...data,
      scriptId: form.value.scriptId,
      voiceType: form.value.voiceType
    })
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || '语音合成失败'
  } finally {
    loading.value = false
  }
}

function publishLesson() {
  if (!form.value.audioId) {
    ElMessage.warning('请先生成音频')
    return
  }

  publishInfo.value = {
    published: true,
    courseId: currentCourse.courseId,
    audioId: form.value.audioId
  }

  ElMessage.success('智课已绑定课程并发布至平台')
}
</script>