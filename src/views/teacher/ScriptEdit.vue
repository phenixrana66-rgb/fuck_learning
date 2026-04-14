<template>
  <TeacherLayout>
    <div class="page-card teacher-card">
      <div class="page-title">讲稿编辑</div>

      <el-form label-width="110px" class="teacher-form">
        <el-form-item label="当前课程">
          <el-input :model-value="currentCourse.courseName || '-'" readonly />
        </el-form-item>
        <el-form-item label="讲稿 ID">
          <el-input v-model="form.scriptId" readonly />
        </el-form-item>
        <el-form-item label="讲稿状态">
          <el-tag :type="statusTagType(form.status)">{{ form.status || '未生成' }}</el-tag>
        </el-form-item>
        <el-form-item label="讲稿内容">
          <el-input
            v-model="form.scriptContent"
            type="textarea"
            :rows="18"
            resize="vertical"
            placeholder="请先生成讲稿，再在这里做人工修订。"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSave">保存讲稿</el-button>
          <el-button @click="refreshStatus">重新加载</el-button>
          <el-button type="success" :disabled="!form.scriptId" @click="goAudioPage">进入音频生成</el-button>
        </el-form-item>
      </el-form>

      <Loading :visible="saving || loading" :text="saving ? '正在保存讲稿…' : '正在加载讲稿…'" />
      <ErrorTip v-if="errorCode" :code="errorCode" :message="errorMsg" @retry="refreshStatus" />
    </div>
  </TeacherLayout>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import TeacherLayout from '@/components/teacher/TeacherLayout.vue'
import Loading from '@/components/teacher/Loading.vue'
import ErrorTip from '@/components/teacher/ErrorTip.vue'
import { getLessonStatus, saveScript } from '@/api/teacher'
import { getCurrentCourse, getScriptResult, saveScriptResult } from '@/utils/platform'

const router = useRouter()
const currentCourse = getCurrentCourse()
const localScript = getScriptResult()

const loading = ref(false)
const saving = ref(false)
const errorCode = ref('')
const errorMsg = ref('')
const form = ref({
  scriptId: localScript.scriptId || '',
  status: localScript.status || '',
  scriptType: localScript.scriptType || '',
  scriptContent: localScript.scriptContent || ''
})

onMounted(() => {
  refreshStatus()
})

async function refreshStatus() {
  if (!currentCourse.courseId) return
  loading.value = true
  errorCode.value = ''
  errorMsg.value = ''
  try {
    const res = await getLessonStatus({ courseId: currentCourse.courseId })
    const data = res.data?.script || {}
    if (data.scriptId) {
      form.value.scriptId = data.scriptId
      form.value.status = data.status || ''
      form.value.scriptType = data.scriptType || ''
      form.value.scriptContent = data.scriptContent || ''
      saveScriptResult({
        scriptId: data.scriptId,
        status: data.status,
        scriptType: data.scriptType,
        scriptContent: data.scriptContent,
        updatedAt: data.updatedAt
      })
    }
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || '加载讲稿失败。'
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!form.value.scriptId) {
    ElMessage.warning('请先生成讲稿。')
    return
  }
  if (!form.value.scriptContent.trim()) {
    ElMessage.warning('讲稿内容不能为空。')
    return
  }

  saving.value = true
  errorCode.value = ''
  errorMsg.value = ''
  try {
    const res = await saveScript({
      scriptId: form.value.scriptId,
      scriptContent: form.value.scriptContent
    })
    const data = res.data || {}
    form.value.status = data.status || 'edited'
    form.value.scriptContent = data.scriptContent || form.value.scriptContent
    saveScriptResult({
      scriptId: form.value.scriptId,
      status: form.value.status,
      scriptType: form.value.scriptType,
      scriptContent: form.value.scriptContent,
      updatedAt: data.updatedAt
    })
    ElMessage.success('讲稿已保存。')
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || '保存讲稿失败。'
  } finally {
    saving.value = false
  }
}

function goAudioPage() {
  router.push('/teacher/audio-generate')
}

function statusTagType(status) {
  if (status === 'published') return 'success'
  if (status === 'edited') return 'warning'
  if (status === 'generated') return 'info'
  return 'info'
}
</script>

<style scoped>
.teacher-card {
  border-radius: 22px;
  border: 1px solid #e7eef9;
  box-shadow: 0 16px 36px rgba(53, 82, 136, 0.08);
}

.teacher-form {
  max-width: 980px;
}
</style>
