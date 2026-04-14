<template>
  <TeacherLayout>
    <div class="page-card teacher-card">
      <div class="page-title">讲稿生成</div>

      <el-form :model="form" label-width="110px" class="teacher-form">
        <el-form-item label="当前课程">
          <el-input :model-value="currentCourse.courseName || '-'" readonly />
        </el-form-item>
        <el-form-item label="解析任务">
          <el-input v-model="form.parseId" readonly />
        </el-form-item>
        <el-form-item label="讲稿风格">
          <el-radio-group v-model="form.scriptType">
            <el-radio label="standard">标准</el-radio>
            <el-radio label="detail">详细</el-radio>
            <el-radio label="simple">简洁</el-radio>
          </el-radio-group>
          <div class="light-tip" style="margin-top: 8px;">
            标准适合常规讲授，详细适合精讲，简洁适合导学页或短时讲解。
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleGenerate">生成讲稿</el-button>
          <el-button @click="refreshStatus">刷新状态</el-button>
        </el-form-item>
      </el-form>

      <Loading :visible="loading" text="讲稿生成中，请稍候…" />
      <ErrorTip v-if="errorCode" :code="errorCode" :message="errorMsg" @retry="handleGenerate" />
    </div>

    <div v-if="scriptContent" class="page-card teacher-card">
      <div class="sub-title">讲稿预览</div>
      <div class="script-preview">{{ scriptContent }}</div>
      <div class="toolbar" style="margin-top: 18px;">
        <el-button type="primary" @click="goEditPage">进入讲稿编辑</el-button>
      </div>
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
import { generateScript, getLessonStatus } from '@/api/teacher'
import { getCurrentCourse, getParseResult, saveScriptResult } from '@/utils/platform'

const router = useRouter()
const currentCourse = getCurrentCourse()
const parseResult = getParseResult()

const form = ref({
  parseId: parseResult.parseId || '',
  scriptType: 'standard'
})

const loading = ref(false)
const errorCode = ref('')
const errorMsg = ref('')
const scriptContent = ref('')

onMounted(() => {
  refreshStatus()
})

async function refreshStatus() {
  if (!currentCourse.courseId) return
  try {
    const res = await getLessonStatus({ courseId: currentCourse.courseId })
    const data = res.data || {}
    form.value.parseId = form.value.parseId || data.parse?.parseId || ''
    scriptContent.value = data.script?.scriptContent || ''
  } catch (_error) {
    // 状态刷新失败不阻断页面使用
  }
}

async function handleGenerate() {
  if (!form.value.parseId) {
    ElMessage.warning('请先完成课件解析。')
    return
  }

  loading.value = true
  errorCode.value = ''
  errorMsg.value = ''

  try {
    const res = await generateScript({
      parseId: form.value.parseId,
      courseId: currentCourse.courseId,
      scriptType: form.value.scriptType
    })

    const data = res.data || {}
    scriptContent.value = data.scriptContent || ''
    saveScriptResult({
      ...data,
      parseId: form.value.parseId,
      scriptType: form.value.scriptType,
      status: data.status || 'generated'
    })
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || '讲稿生成失败。'
  } finally {
    loading.value = false
  }
}

function goEditPage() {
  router.push('/teacher/script-edit')
}
</script>

<style scoped>
.teacher-card {
  border-radius: 22px;
  border: 1px solid #e7eef9;
  box-shadow: 0 16px 36px rgba(53, 82, 136, 0.08);
}

.teacher-form {
  max-width: 760px;
}

.script-preview {
  padding: 18px 20px;
  border-radius: 18px;
  background: linear-gradient(180deg, #f8fbff 0%, #f1f6ff 100%);
  border: 1px solid #e6eefb;
  color: #304767;
  line-height: 1.9;
  white-space: pre-wrap;
}
</style>
