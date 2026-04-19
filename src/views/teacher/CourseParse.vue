<template>
  <TeacherLayout>
    <div class="page-card teacher-card">
      <div class="page-title">课件解析</div>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        class="teacher-alert"
        title="支持 PPTX、PDF。上传后系统会解析章节结构、页图与知识点。"
      />

      <div class="toolbar">
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :show-file-list="true"
          :limit="1"
          :on-change="handleFileChange"
          :on-exceed="handleFileExceed"
          :on-remove="handleFileRemove"
          :disabled="submitting || polling"
          accept=".pptx,.pdf"
        >
          <el-button :loading="submitting">选择文件并解析</el-button>
        </el-upload>

        <el-button type="primary" :loading="submitting" @click="submitParse">上传并解析</el-button>
        <el-button :disabled="!parseForm.parseId" @click="pollStatus">查询状态</el-button>
      </div>

      <el-form :model="parseForm" label-width="96px" class="teacher-form">
        <el-form-item label="当前课程">
          <el-input :model-value="currentCourse.courseName || '-'" readonly />
        </el-form-item>
        <el-form-item label="文件名称">
          <el-input v-model="parseForm.fileName" readonly />
        </el-form-item>
        <el-form-item label="解析任务">
          <el-input v-model="parseForm.parseId" readonly />
        </el-form-item>
        <el-form-item label="解析状态">
          <el-tag :type="statusTagType(parseForm.status)">
            {{ parseForm.status || '未开始' }}
          </el-tag>
        </el-form-item>
        <el-form-item label="目标章节">
          <el-input :model-value="parseForm.chapterName || '-'" readonly />
        </el-form-item>
      </el-form>

      <Loading
        :visible="submitting || polling"
        :text="polling ? '课件解析中，正在轮询状态…' : '课件上传中…'"
        :showProgress="polling"
        :percentage="progress"
      />

      <ErrorTip v-if="errorCode" :code="errorCode" :message="errorMsg" @retry="pollStatus" />
    </div>

    <div v-if="knowledgeTree.length" class="page-card teacher-card">
      <div class="sub-title">知识点结构预览</div>
      <div v-if="chapterSummary" class="teacher-summary">{{ chapterSummary }}</div>

      <div class="tree-box">
        <el-tree :data="knowledgeTree" node-key="id" default-expand-all :props="treeProps" />
      </div>

      <div class="toolbar" style="margin-top: 18px;">
        <el-button type="primary" @click="goScriptPage">进入讲稿生成</el-button>
      </div>
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
import { lessonParse, getParseStatusAPI} from '@/api/teacher'
import { getCurrentCourse, saveParseResult } from '@/utils/platform'

const router = useRouter()
const currentCourse = getCurrentCourse()
const uploadRef = ref(null)

const parseForm = ref({
  fileName: '',
  fileBase64: '',
  parseId: '',
  status: '',
  chapterId: '',
  chapterName: ''
})

const submitting = ref(false)
const polling = ref(false)
const progress = ref(0)
const chapterSummary = ref('')
const knowledgeTree = ref([])
const errorCode = ref('')
const errorMsg = ref('')

const treeProps = {
  children: 'children',
  label: 'name'
}

let pollTimer = null

function resetParseState() {
  clearTimeout(pollTimer)
  parseForm.value.parseId = ''
  parseForm.value.status = ''
  knowledgeTree.value = []
  errorCode.value = ''
  errorMsg.value = ''
  progress.value = 0
  polling.value = false
}

function handleFileExceed(files) {
  uploadRef.value?.clearFiles()
  const rawFile = files?.[0]
  if (rawFile) {
    handleSelectedFile(rawFile)
  }
}

function handleFileRemove() {
  clearTimeout(pollTimer)
  parseForm.value.fileName = ''
  parseForm.value.fileBase64 = ''
  resetParseState()
}

function handleFileChange(file) {
  const rawFile = file?.raw || file
  if (!rawFile) return
  handleSelectedFile(rawFile)
}

function handleSelectedFile(file) {
  const isValid = /\.(pptx|pdf)$/i.test(file.name)
  if (!isValid) {
    ElMessage.warning('仅支持 PPTX、PDF 文件。')
    return false
  }

  resetParseState()
  parseForm.value.fileName = file.name
  const reader = new FileReader()
  reader.readAsDataURL(file)
  reader.onload = async () => {
    parseForm.value.fileBase64 = reader.result
    await submitParse()
  }
  reader.onerror = () => {
    ElMessage.error('课件文件读取失败，请重新选择')
    uploadRef.value?.clearFiles()
    parseForm.value.fileBase64 = ''
  }
}

async function submitParse() {
  if (!currentCourse.courseId) {
    ElMessage.warning('请先选择课程。')
    return
  }

  if (!parseForm.value.fileBase64) {
    ElMessage.warning('请先选择课件文件。')
    return
  }

  submitting.value = true
  errorCode.value = ''
  errorMsg.value = ''

  try {
    const res = await lessonParse({
      courseId: currentCourse.courseId,
      classId: currentCourse.classId,
      schoolId: currentCourse.schoolId,
      fileName: parseForm.value.fileName,
      fileContent: parseForm.value.fileBase64,
    })

    const data = res.data || {}
    parseForm.value.parseId = data.parseId || ''
    parseForm.value.status = data.status || 'processing'
    parseForm.value.chapterId = data.chapterId || ''
    parseForm.value.chapterName = data.chapterName || ''
    chapterSummary.value = data.chapterSummary || ''
    knowledgeTree.value = data.knowledgeTree || []

    saveParseResult({
      ...data,
      fileName: parseForm.value.fileName
    })

    if (parseForm.value.parseId && parseForm.value.status !== 'success') {
      pollStatus()
    }
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || '解析提交失败。'
  } finally {
    submitting.value = false
  }
}

async function pollStatus() {
  if (!parseForm.value.parseId) {
    ElMessage.warning('当前没有可查询的解析任务。')
    return
  }

  clearTimeout(pollTimer)
  polling.value = true
  progress.value = 15

  const doPoll = async () => {
    try {
      const res = await getParseStatusAPI(parseForm.value.parseId)

      const data = res.data || {}
      parseForm.value.status = data.status || parseForm.value.status
      parseForm.value.chapterId = data.chapterId || parseForm.value.chapterId
      parseForm.value.chapterName = data.chapterName || parseForm.value.chapterName
      chapterSummary.value = data.chapterSummary || chapterSummary.value
      knowledgeTree.value = data.knowledgeTree || knowledgeTree.value
      progress.value = Math.min(progress.value + 18, 95)

      saveParseResult({
        ...data,
        parseId: parseForm.value.parseId,
        fileName: parseForm.value.fileName
      })

      if (data.status === 'success') {
        polling.value = false
        progress.value = 100
        return
      }

      if (data.status === 'failed') {
        polling.value = false
        errorCode.value = 500
        errorMsg.value = data.msg || '解析失败。'
        return
      }

      pollTimer = setTimeout(doPoll, 3000)
    } catch (error) {
      polling.value = false
      errorCode.value = error.code || 500
      errorMsg.value = error.msg || '轮询解析状态失败。'
    }
  }

  doPoll()
}

function statusTagType(status) {
  if (status === 'success' || status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'processing') return 'warning'
  return 'info'
}

function goScriptPage() {
  router.push('/teacher/script-generate')
}
</script>
