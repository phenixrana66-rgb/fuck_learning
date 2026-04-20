<template>
  <div class="teacher-login-page app-scrollable">
    <div class="teacher-login-shell">
      <div class="teacher-login-hero">
        <div class="teacher-login-brand">
          <div class="teacher-login-mark">泛</div>
          <div>
            <div class="teacher-login-title">泛雅 AI 互动智课教师端</div>
            <div class="teacher-login-desc">完成平台同步后即可进入课件解析、讲稿编辑、音频生成与智课发布流程。</div>
          </div>
        </div>

        <div class="teacher-login-highlight">
          <div class="highlight-badge">当前流程</div>
          <div class="highlight-title">同步课程 -> 解析课件 -> 编辑讲稿 -> 生成音频 -> 发布智课</div>
          <div class="highlight-subtitle">发布成功后，学生端会直接读取数据库中的最新章节内容与页图。</div>
        </div>
      </div>

      <div class="teacher-login-panel">
        <div class="page-card teacher-login-card">
          <div class="page-title">平台鉴权与课程同步</div>

          <div class="toolbar">
            <el-input v-model="token" placeholder="请输入平台 token，例如 test_token_001" clearable />
            <el-button type="primary" :loading="loading" @click="handleSync">同步用户与课程</el-button>
          </div>

          <Loading :visible="loading" text="正在同步平台用户与课程…" />

          <ErrorTip v-if="errorCode" :code="errorCode" :message="errorMsg" @retry="handleSync" />

          <div v-if="teacherInfo.teacherId || teacherInfo.userId" class="info-grid teacher-login-info">
            <div class="info-item">
              <div class="info-label">教师 ID</div>
              <div class="info-value">{{ teacherInfo.teacherId || teacherInfo.userId || '-' }}</div>
            </div>
            <div class="info-item">
              <div class="info-label">教师姓名</div>
              <div class="info-value">{{ teacherInfo.teacherName || teacherInfo.userName || '-' }}</div>
            </div>
            <div class="info-item">
              <div class="info-label">所属学校</div>
              <div class="info-value">{{ teacherInfo.schoolName || '-' }}</div>
            </div>
          </div>
        </div>

        <div v-if="courseList.length" class="page-card teacher-course-table-card">
          <div class="sub-title">可管理课程</div>
          <el-table :data="courseList" border>
            <el-table-column prop="courseId" label="课程 ID" min-width="140" />
            <el-table-column prop="courseName" label="课程名称" min-width="220" />
            <el-table-column prop="classId" label="班级 ID" min-width="120" />
            <el-table-column prop="schoolId" label="学校 ID" min-width="120" />
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button type="primary" link @click="selectCourse(row)">进入管理</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Loading from '@/components/teacher/Loading.vue'
import ErrorTip from '@/components/teacher/ErrorTip.vue'
import { syncCourse, syncUser } from '@/api/teacher'
import {
  getPlatformToken,
  savePlatformToken,
  saveTeacherProfile,
  saveCourseList,
  saveCurrentCourse
} from '@/utils/platform'

const router = useRouter()

const token = ref('')
const loading = ref(false)
const errorCode = ref('')
const errorMsg = ref('')
const teacherInfo = ref({})
const courseList = ref([])

onMounted(() => {
  token.value = getPlatformToken() || 'test_token_001'
  if (getPlatformToken()) {
    handleSync()
  }
})

async function handleSync() {
  if (!token.value) {
    errorCode.value = 400
    errorMsg.value = '请输入平台 token。'
    return
  }

  loading.value = true
  errorCode.value = ''
  errorMsg.value = ''

  try {
    savePlatformToken(token.value)

    const userRes = await syncUser({ token: token.value })
    teacherInfo.value = userRes.data || {}
    saveTeacherProfile(teacherInfo.value)

    const courseRes = await syncCourse({
      token: token.value,
      teacherId: teacherInfo.value.teacherId || teacherInfo.value.userId,
      schoolId: teacherInfo.value.schoolId
    })

    courseList.value = courseRes.data?.courseList || courseRes.data || []
    saveCourseList(courseList.value)

    if (courseList.value.length === 1) {
      saveCurrentCourse(courseList.value[0])
    }
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || '同步失败。'
  } finally {
    loading.value = false
  }
}

function selectCourse(course) {
  saveCurrentCourse(course)
  router.push('/teacher/lesson-manage')
}
</script>

<style scoped>
.teacher-login-page {
  height: 100vh;
  min-height: 100vh;
  padding: 36px 20px;
  background: linear-gradient(180deg, #f7faff 0%, #edf4fd 100%);
  box-sizing: border-box;
  overflow-y: auto;
  overflow-x: hidden;
}

.teacher-login-shell {
  max-width: 1280px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(320px, 460px) minmax(0, 1fr);
  gap: 20px;
}

.teacher-login-hero {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.teacher-login-brand,
.teacher-login-highlight {
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #e7eef9;
  box-shadow: 0 16px 36px rgba(53, 82, 136, 0.08);
}

.teacher-login-brand {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
}

.teacher-login-mark {
  width: 58px;
  height: 58px;
  border-radius: 18px;
  background: linear-gradient(135deg, #ff6d60 0%, #ff4d4f 100%);
  color: #fff;
  font-size: 28px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.teacher-login-title {
  color: #193b72;
  font-size: 30px;
  font-weight: 700;
}

.teacher-login-desc,
.highlight-subtitle {
  margin-top: 8px;
  color: #7388ab;
  font-size: 14px;
  line-height: 1.7;
}

.teacher-login-highlight {
  padding: 24px;
  background: linear-gradient(145deg, #224072 0%, #5e80ca 100%);
  color: #fff;
}

.highlight-badge {
  display: inline-flex;
  align-items: center;
  height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  font-size: 12px;
}

.highlight-title {
  margin-top: 14px;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.6;
}

.highlight-subtitle {
  color: rgba(255, 255, 255, 0.82);
}

.teacher-login-panel {
  min-width: 0;
}

.teacher-login-card,
.teacher-course-table-card {
  border-radius: 24px;
  border: 1px solid #e7eef9;
  box-shadow: 0 16px 36px rgba(53, 82, 136, 0.08);
}

.teacher-login-info {
  margin-top: 20px;
}

@media (max-width: 1100px) {
  .teacher-login-shell {
    grid-template-columns: 1fr;
  }
}
</style>
