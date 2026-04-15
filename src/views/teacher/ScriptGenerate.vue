<template>
  <TeacherLayout>
    <div class="page-card">
      <div class="page-title">Script Generate</div>

      <el-form :model="form" label-width="110px">
        <el-form-item label="parseId">
          <el-input v-model="form.parseId" readonly />
        </el-form-item>

        <el-form-item label="Style">
          <el-radio-group v-model="form.teachingStyle">
            <el-radio label="standard">Standard</el-radio>
            <el-radio label="detailed">Detailed</el-radio>
            <el-radio label="concise">Concise</el-radio>
          </el-radio-group>
          <div class="light-tip" style="margin-top: 8px;">
            Standard fits normal teaching, Detailed fits deeper explanation, Concise fits short guided lessons.
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleGenerate">
            Generate Script
          </el-button>
        </el-form-item>
      </el-form>

      <Loading :visible="loading" text="Generating script, please wait..." />

      <ErrorTip
        v-if="errorCode"
        :code="errorCode"
        :message="errorMsg"
        @retry="handleGenerate"
      />
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
import { getParseResult, saveScriptResult } from '@/utils/platform'

const router = useRouter()
const parseResult = getParseResult()

const form = ref({
  parseId: parseResult.parseId || '',
  teachingStyle: 'standard'
})

const loading = ref(false)
const errorCode = ref('')
const errorMsg = ref('')

async function handleGenerate() {
  if (!form.value.parseId) {
    ElMessage.warning('Complete courseware parsing first')
    return
  }

  loading.value = true
  errorCode.value = ''
  errorMsg.value = ''

  try {
    const res = await generateScript({
      parseId: form.value.parseId,
      teachingStyle: form.value.teachingStyle,
      speechSpeed: 'normal',
      customOpening: ''
    })

    const data = res.data || {}
    saveScriptResult({
      ...data,
      parseId: form.value.parseId,
      teachingStyle: form.value.teachingStyle,
      speechSpeed: 'normal',
      status: 'success'
    })

    router.push('/teacher/script-edit')
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || 'Failed to generate script'
  } finally {
    loading.value = false
  }
}
</script>
