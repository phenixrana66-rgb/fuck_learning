<template>
  <TeacherLayout>
    <div class="page-card">
      <div class="page-title">脚本生成</div>

      <el-form :model="form" label-width="110px">
        <el-form-item label="parseId">
          <el-input v-model="form.parseId" readonly />
        </el-form-item>

        <el-form-item label="脚本类型">
          <el-radio-group v-model="form.scriptType">
            <el-radio label="standard">标准</el-radio>
            <el-radio label="detail">详细</el-radio>
            <el-radio label="simple">简洁</el-radio>
          </el-radio-group>
          <div class="light-tip" style="margin-top: 8px;">
            标准适合常规授课，详细适合精讲，简洁适合短课或导学。
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleGenerate">
            生成脚本
          </el-button>
        </el-form-item>
      </el-form>

      <Loading :visible="loading" text="脚本生成中，请稍候..." />

      <ErrorTip
        v-if="errorCode"
        :code="errorCode"
        :message="errorMsg"
        @retry="handleGenerate"
      />
    </div>

    <div class="page-card" v-if="generateSuccess">
      <el-result
        icon="success"
        title="脚本生成成功"
        sub-title="已生成脚本内容，点击下方按钮进入脚本编辑页"
      >
        <template #extra>
          <el-button type="success" @click="goEditPage">进入脚本编辑</el-button>
        </template>
      </el-result>
    </div>
  </TeacherLayout>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import TeacherLayout from '@/components/teacher/TeacherLayout.vue'
import Loading from '@/components/teacher/Loading.vue'
import ErrorTip from '@/components/teacher/ErrorTip.vue'
import { generateScript } from '@/api/teacher'
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
const generateSuccess = ref(false)

async function handleGenerate() {
  if (!form.value.parseId) {
    ElMessage.warning('请先完成课件解析')
    return
  }

  loading.value = true
  errorCode.value = ''
  errorMsg.value = ''
  generateSuccess.value = false

  try {
    const res = await generateScript({
      parseId: form.value.parseId,
      courseId: currentCourse.courseId,
      scriptType: form.value.scriptType
    })

    const data = res.data || {}

    saveScriptResult({
      ...data,
      parseId: form.value.parseId,
      scriptType: form.value.scriptType,
      status: data.status || 'success'
    })

    generateSuccess.value = true
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || '脚本生成失败'
  } finally {
    loading.value = false
  }
}

function goEditPage() {
  router.push('/teacher/script-edit')
}
</script>