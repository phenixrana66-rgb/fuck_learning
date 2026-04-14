<template>
  <TeacherLayout>
    <div class="page-card teacher-card">
      <div class="page-title">智课管理</div>

      <div class="toolbar teacher-manage-toolbar">
        <el-select
          v-model="selectedCourseId"
          placeholder="切换课程"
          class="teacher-course-select"
          @change="handleChangeCourse"
        >
          <el-option
            v-for="item in courseList"
            :key="item.courseId"
            :label="item.courseName"
            :value="item.courseId"
          />
        </el-select>

        <el-button type="primary" @click="goPage('/teacher/course-parse')">课件解析</el-button>
        <el-button type="success" @click="goPage('/teacher/script-generate')">讲稿生成</el-button>
        <el-button type="warning" @click="goPage('/teacher/audio-generate')">音频生成与发布</el-button>
        <el-button @click="fetchStatus">刷新状态</el-button>
      </div>

      <div class="info-grid">
        <div class="info-item">
          <div class="info-label">当前课程</div>
          <div class="info-value">{{ currentCourse.courseName || '-' }}</div>
        </div>
        <div class="info-item">
          <div class="info-label">当前章节</div>
          <div class="info-value">{{ statusData.chapterName || '-' }}</div>
        </div>
        <div class="info-item">
          <div class="info-label">发布时间</div>
          <div class="info-value">{{ formatDateTime(statusData.publish?.publishedAt) }}</div>
        </div>
      </div>

      <Loading :visible="loading" text="正在读取课程状态…" />
      <ErrorTip v-if="errorCode" :code="errorCode" :message="errorMsg" @retry="fetchStatus" />
    </div>

    <div class="teacher-status-grid">
      <div class="page-card teacher-card status-card">
        <div class="status-card-header">
          <div class="sub-title">课件解析</div>
          <el-tag :type="statusType(statusData.parse?.status)">{{ statusText(statusData.parse?.status) }}</el-tag>
        </div>
        <div class="status-card-id">任务 ID：{{ statusData.parse?.parseId || '-' }}</div>
        <div class="status-card-desc">文件：{{ statusData.parse?.fileName || '尚未上传课件' }}</div>
      </div>

      <div class="page-card teacher-card status-card">
        <div class="status-card-header">
          <div class="sub-title">讲稿生成</div>
          <el-tag :type="statusType(statusData.script?.status)">{{ statusText(statusData.script?.status) }}</el-tag>
        </div>
        <div class="status-card-id">讲稿 ID：{{ statusData.script?.scriptId || '-' }}</div>
        <div class="status-card-desc">风格：{{ scriptTypeText(statusData.script?.scriptType) }}</div>
      </div>

      <div class="page-card teacher-card status-card">
        <div class="status-card-header">
          <div class="sub-title">音频生成</div>
          <el-tag :type="statusType(statusData.audio?.status)">{{ statusText(statusData.audio?.status) }}</el-tag>
        </div>
        <div class="status-card-id">音频 ID：{{ statusData.audio?.audioId || '-' }}</div>
        <div class="status-card-desc">音色：{{ voiceTypeText(statusData.audio?.voiceType) }}</div>
      </div>

      <div class="page-card teacher-card status-card">
        <div class="status-card-header">
          <div class="sub-title">智课发布</div>
          <el-tag :type="statusType(statusData.publish?.status)">{{ statusText(statusData.publish?.status) }}</el-tag>
        </div>
        <div class="status-card-id">课程序号：{{ statusData.publish?.lessonNo || '-' }}</div>
        <div class="status-card-desc">章节 ID：{{ statusData.publish?.sectionId || '-' }}</div>
      </div>
    </div>
  </TeacherLayout>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import TeacherLayout from '@/components/teacher/TeacherLayout.vue'
import Loading from '@/components/teacher/Loading.vue'
import ErrorTip from '@/components/teacher/ErrorTip.vue'
import { getLessonStatus } from '@/api/teacher'
import { getCourseList, getCurrentCourse, saveCurrentCourse } from '@/utils/platform'

const router = useRouter()

const courseList = ref(getCourseList())
const currentCourse = ref(getCurrentCourse())
const selectedCourseId = ref(currentCourse.value.courseId || courseList.value[0]?.courseId || '')
const loading = ref(false)
const errorCode = ref('')
const errorMsg = ref('')
const statusData = ref({
  chapterName: '',
  parse: {},
  script: {},
  audio: {},
  publish: {}
})

onMounted(() => {
  if (!currentCourse.value.courseId && courseList.value[0]) {
    currentCourse.value = courseList.value[0]
    saveCurrentCourse(currentCourse.value)
    selectedCourseId.value = currentCourse.value.courseId
  }
  fetchStatus()
})

async function fetchStatus() {
  if (!currentCourse.value.courseId) return

  loading.value = true
  errorCode.value = ''
  errorMsg.value = ''
  try {
    const res = await getLessonStatus({ courseId: currentCourse.value.courseId })
    statusData.value = res.data || {}
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || '读取课程状态失败。'
  } finally {
    loading.value = false
  }
}

function handleChangeCourse(courseId) {
  const target = courseList.value.find((item) => String(item.courseId) === String(courseId))
  if (!target) return
  currentCourse.value = target
  saveCurrentCourse(target)
  window.location.reload()
}

function goPage(path) {
  router.push(path)
}

function statusText(status) {
  const map = {
    idle: '未开始',
    processing: '处理中',
    completed: '已完成',
    generated: '已生成',
    edited: '已编辑',
    published: '已发布',
    draft: '草稿',
    failed: '失败'
  }
  return map[status] || '未开始'
}

function statusType(status) {
  if (status === 'published' || status === 'completed') return 'success'
  if (status === 'generated' || status === 'edited' || status === 'processing') return 'warning'
  if (status === 'failed') return 'danger'
  return 'info'
}

function scriptTypeText(type) {
  const map = {
    standard: '标准',
    detail: '详细',
    simple: '简洁'
  }
  return map[type] || '-'
}

function voiceTypeText(type) {
  const map = {
    female_standard: '女声·标准',
    male_standard: '男声·标准',
    female_warm: '女声·亲和',
    male_deep: '男声·磁性'
  }
  return map[type] || '-'
}

function formatDateTime(value) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString('zh-CN', { hour12: false })
  } catch (_error) {
    return value
  }
}
</script>

<style scoped>
.teacher-card {
  border-radius: 22px;
  border: 1px solid #e7eef9;
  box-shadow: 0 16px 36px rgba(53, 82, 136, 0.08);
}

.teacher-manage-toolbar {
  margin-bottom: 18px;
}

.teacher-course-select {
  width: 320px;
}

.teacher-status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(280px, 1fr));
  gap: 16px;
}

.status-card {
  min-height: 174px;
}

.status-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.status-card-id {
  margin-top: 18px;
  color: #213c70;
  font-size: 18px;
  font-weight: 600;
  line-height: 1.6;
  word-break: break-all;
}

.status-card-desc {
  margin-top: 10px;
  color: #7b8eaf;
  font-size: 14px;
  line-height: 1.8;
}

@media (max-width: 1100px) {
  .teacher-status-grid {
    grid-template-columns: 1fr;
  }
}
</style>
