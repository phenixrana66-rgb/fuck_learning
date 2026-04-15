<template>
  <TeacherLayout>
    <div class="page-card">
      <div class="page-title">智课管理</div>

      <div class="info-grid">
        <div class="info-item">
          <div class="info-label">当前课程</div>
          <div class="info-value">{{ currentCourse.courseName || '-' }}</div>
        </div>
        <div class="info-item">
          <div class="info-label">课程ID</div>
          <div class="info-value">{{ currentCourse.courseId || '-' }}</div>
        </div>
        <div class="info-item">
          <div class="info-label">班级ID</div>
          <div class="info-value">{{ currentCourse.classId || '-' }}</div>
        </div>
      </div>
    </div>

    <div class="page-card">
      <div class="sub-title">课程操作</div>
      <div class="toolbar">
        <el-select
          v-model="selectedCourseId"
          placeholder="切换课程"
          style="width: 320px"
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
        <el-button type="success" @click="goPage('/teacher/script-generate')">脚本生成</el-button>
        <el-button type="warning" @click="goPage('/teacher/audio-generate')">语音合成</el-button>
      </div>
    </div>

    <div class="page-card">
      <div class="sub-title">任务状态总览</div>

      <el-table :data="statusTable" border>
        <el-table-column prop="name" label="模块" width="180" />
        <el-table-column prop="id" label="任务ID" min-width="220" />
        <el-table-column label="状态" width="160">
          <template #default="{ row }">
            <el-tag :type="getTagType(row.status)">
              {{ row.status || '未开始' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="desc" label="说明" min-width="240" />
      </el-table>
    </div>
  </TeacherLayout>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import TeacherLayout from '@/components/teacher/TeacherLayout.vue'
import {
  getCourseList,
  getCurrentCourse,
  saveCurrentCourse,
  getParseResult,
  getScriptResult,
  getAudioResult
} from '@/utils/platform'

const router = useRouter()

const courseList = getCourseList()
const currentCourse = getCurrentCourse()
const parseResult = getParseResult()
const scriptResult = getScriptResult()
const audioResult = getAudioResult()

const selectedCourseId = ref(currentCourse.courseId || '')

const statusTable = computed(() => [
  {
    name: '课件解析',
    id: parseResult.parseId || '-',
    status: parseResult.status || '未开始',
    desc: parseResult.fileName || '尚未上传课件'
  },
  {
    name: '脚本生成',
    id: scriptResult.scriptId || '-',
    status: scriptResult.status || '未开始',
    desc: scriptResult.teachingStyle || '尚未生成脚本'
  },
  {
    name: '语音合成',
    id: audioResult.audioId || '-',
    status: audioResult.status || '未开始',
    desc: audioResult.voiceType || '尚未生成音频'
  }
])

function handleChangeCourse(courseId) {
  const target = courseList.find((item) => String(item.courseId) === String(courseId))
  if (target) {
    saveCurrentCourse(target)
    window.location.reload()
  }
}

function getTagType(status) {
  if (status === 'success') return 'success'
  if (status === 'processing') return 'warning'
  if (status === 'failed') return 'danger'
  return 'info'
}

function goPage(path) {
  router.push(path)
}
</script>