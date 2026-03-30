<template>
  <div class="login-page">
    <div class="login-panel">
      <div class="login-brand">
        <div class="brand-mark">泛</div>
        <div>
          <div class="brand-title">超星 AI 互动智课教师端</div>
          <div class="brand-desc">学习通 / 泛雅平台内嵌式轻量化 Web 应用</div>
        </div>
      </div>

      <div class="page-card" style="box-shadow: none; padding: 0; margin: 0;">
        <div class="page-title">平台鉴权与同步</div>

        <div class="toolbar">
          <el-input v-model="token" placeholder="请输入或自动接收平台 token" clearable />
          <el-button type="primary" :loading="loading" @click="handleSync">
            同步用户与课程
          </el-button>
        </div>

        <Loading :visible="loading" text="正在同步平台用户与课程信息..." />

        <ErrorTip
          v-if="errorCode"
          :code="errorCode"
          :message="errorMsg"
          @retry="handleSync"
        />

        <div class="info-grid" v-if="teacherInfo.teacherId || teacherInfo.userId">
          <div class="info-item">
            <div class="info-label">教师ID</div>
            <div class="info-value">{{ teacherInfo.teacherId || teacherInfo.userId || '-' }}</div>
          </div>
          <div class="info-item">
            <div class="info-label">学校ID</div>
            <div class="info-value">{{ teacherInfo.schoolId || '-' }}</div>
          </div>
          <div class="info-item">
            <div class="info-label">教师姓名</div>
            <div class="info-value">{{ teacherInfo.teacherName || teacherInfo.userName || '-' }}</div>
          </div>
        </div>
      </div>

      <div class="page-card" v-if="courseList.length">
        <div class="sub-title">课程列表</div>
        <el-table :data="courseList" border>
          <el-table-column prop="courseId" label="课程ID" min-width="120" />
          <el-table-column prop="courseName" label="课程名称" min-width="220" />
          <el-table-column prop="classId" label="班级ID" min-width="120" />
          <el-table-column prop="schoolId" label="学校ID" min-width="120" />
          <el-table-column label="操作" width="140">
            <template #default="{ row }">
              <el-button type="primary" link @click="selectCourse(row)">
                进入管理
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { syncUser, syncCourse } from '@/api/teacher'
import Loading from '@/components/teacher/Loading.vue'
import ErrorTip from '@/components/teacher/ErrorTip.vue'
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
  token.value = getPlatformToken()
  if (token.value) {
    handleSync()
  }
})

async function handleSync() {
  if (!token.value) {
    errorCode.value = 400
    errorMsg.value = '缺少平台 token'
    return
  }

  loading.value = true
  errorCode.value = ''
  errorMsg.value = ''

  try {
    savePlatformToken(token.value)

    const userRes = await syncUser({
      token: token.value
    })

    teacherInfo.value = userRes.data || {}
    saveTeacherProfile(teacherInfo.value)

    const courseRes = await syncCourse({
      token: token.value,
      teacherId: teacherInfo.value.teacherId || teacherInfo.value.userId,
      schoolId: teacherInfo.value.schoolId
    })

    courseList.value = courseRes.data?.courseList || courseRes.data || []
    saveCourseList(courseList.value)
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || '同步失败'
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
.login-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #f7f9fc 0%, #eef3f9 100%);
  padding: 40px 16px;
}

.login-panel {
  max-width: 1180px;
  margin: 0 auto;
}

.login-brand {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
}

.brand-mark {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: linear-gradient(135deg, #ff6a5f 0%, #ff4d4f 100%);
  color: #fff;
  font-size: 24px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.brand-title {
  font-size: 28px;
  font-weight: 700;
  color: #1f2d3d;
}

.brand-desc {
  margin-top: 4px;
  font-size: 13px;
  color: #909399;
}
</style>