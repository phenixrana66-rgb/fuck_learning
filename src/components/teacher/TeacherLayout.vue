<template>
  <div class="teacher-layout">
    <header class="teacher-header">
      <div class="teacher-brand" role="button" tabindex="0" @click="go('/teacher/lesson-manage')" @keydown.enter="go('/teacher/lesson-manage')" @keydown.space.prevent="go('/teacher/lesson-manage')">
        <div class="teacher-brand-mark">泛</div>
        <div class="teacher-brand-copy">
          <div class="teacher-brand-title">泛雅 AI 互动智课</div>
          <div class="teacher-brand-subtitle">教师工作台</div>
        </div>
      </div>

      <div class="teacher-user">
        <el-avatar :size="36" class="teacher-user-avatar">
          {{ teacherInitial }}
        </el-avatar>
        <div class="teacher-user-copy">
          <div class="teacher-user-name">{{ teacherName }}</div>
          <div class="teacher-user-school">{{ teacherSchool }}</div>
        </div>
      </div>
    </header>

    <div class="teacher-main">
      <aside class="teacher-sidebar">
        <div class="teacher-course-card">
          <div class="teacher-course-label">当前课程</div>
          <div class="teacher-course-title">{{ courseName }}</div>
          <div class="teacher-course-meta">
            <span>课程 ID：{{ currentCourse.courseId || '-' }}</span>
            <span>班级 ID：{{ currentCourse.classId || '-' }}</span>
          </div>
        </div>

        <div class="teacher-menu-group">功能菜单</div>

        <button
          v-for="item in menuList"
          :key="item.path"
          type="button"
          class="teacher-menu-item"
          :class="{ active: route.path === item.path }"
          @click="go(item.path)"
        >
          <el-icon class="teacher-menu-icon">
            <component :is="item.icon" />
          </el-icon>
          <span>{{ item.label }}</span>
        </button>
      </aside>

      <main class="teacher-content">
        <div class="teacher-course-bar">
          <div>
            <div class="teacher-course-bar-title">{{ courseName }}</div>
            <div class="teacher-course-bar-meta">教师端内容生产与发布流程</div>
          </div>

          <div class="teacher-course-actions">
            <el-button size="small" @click="go('/teacher/login')">重新同步</el-button>
            <el-button size="small" type="primary" @click="go('/teacher/lesson-manage')">返回管理页</el-button>
          </div>
        </div>

        <div class="teacher-page-body">
          <slot />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DataBoard, Document, EditPen, House, Microphone } from '@element-plus/icons-vue'
import { getCurrentCourse, getTeacherProfile } from '@/utils/platform'

const router = useRouter()
const route = useRoute()

const teacherInfo = ref(getTeacherProfile())
const currentCourse = ref(getCurrentCourse())

const menuList = [
  { label: '智课管理', path: '/teacher/lesson-manage', icon: House },
  { label: '课件解析', path: '/teacher/course-parse', icon: DataBoard },
  { label: '讲稿生成', path: '/teacher/script-generate', icon: Document },
  { label: '讲稿编辑', path: '/teacher/script-edit', icon: EditPen },
  { label: '音频生成', path: '/teacher/audio-generate', icon: Microphone }
]

const teacherName = computed(() => teacherInfo.value.teacherName || teacherInfo.value.userName || '教师用户')
const teacherSchool = computed(() => teacherInfo.value.schoolName || '泛雅平台')
const teacherInitial = computed(() => String(teacherName.value || '教').slice(0, 1))
const courseName = computed(() => currentCourse.value.courseName || '未选择课程')

function go(path) {
  router.push(path)
}
</script>

<style scoped>
.teacher-layout {
  --teacher-header-height: 78px;
  --teacher-sidebar-width: 292px;
  min-height: 100vh;
  background: linear-gradient(180deg, #f7faff 0%, #eef4fd 100%);
}

.teacher-header {
  position: fixed;
  inset: 0 0 auto 0;
  z-index: 30;
  height: var(--teacher-header-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 22px;
  background: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid #e5eefb;
  backdrop-filter: blur(14px);
}

.teacher-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  outline: none;
}

.teacher-brand:focus-visible {
  border-radius: 14px;
  box-shadow: 0 0 0 3px rgba(80, 122, 220, 0.18);
}

.teacher-brand-mark {
  width: 46px;
  height: 46px;
  border-radius: 16px;
  background: linear-gradient(135deg, #ff6d60 0%, #ff4d4f 100%);
  color: #fff;
  font-size: 22px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.teacher-brand-title {
  color: #183a72;
  font-size: 24px;
  font-weight: 700;
}

.teacher-brand-subtitle {
  margin-top: 2px;
  color: #8395b5;
  font-size: 13px;
}

.teacher-user {
  display: flex;
  align-items: center;
  gap: 10px;
}

.teacher-user-avatar {
  background: linear-gradient(135deg, #eff4ff 0%, #dfeaff 100%);
  color: #2552a5;
  font-weight: 700;
}

.teacher-user-name {
  color: #213d71;
  font-size: 14px;
  font-weight: 600;
}

.teacher-user-school {
  margin-top: 2px;
  color: #8b9abb;
  font-size: 12px;
}

.teacher-main {
  min-height: 100vh;
  padding-top: var(--teacher-header-height);
}

.teacher-sidebar {
  position: fixed;
  top: var(--teacher-header-height);
  left: 0;
  bottom: 0;
  width: var(--teacher-sidebar-width);
  padding: 18px 14px 20px;
  overflow-y: auto;
  background: rgba(255, 255, 255, 0.88);
  border-right: 1px solid #e8eef9;
  backdrop-filter: blur(14px);
}

.teacher-course-card {
  border-radius: 22px;
  padding: 20px 18px;
  background: linear-gradient(145deg, #1f325b 0%, #5f84d2 100%);
  color: #fff;
  box-shadow: 0 18px 34px rgba(53, 82, 136, 0.2);
}

.teacher-course-label {
  font-size: 12px;
  opacity: 0.82;
  letter-spacing: 0.08em;
}

.teacher-course-title {
  margin-top: 10px;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.5;
  word-break: break-word;
}

.teacher-course-meta {
  margin-top: 12px;
  display: grid;
  gap: 6px;
  font-size: 12px;
  opacity: 0.88;
}

.teacher-menu-group {
  margin: 18px 8px 10px;
  color: #90a0bf;
  font-size: 12px;
  letter-spacing: 0.08em;
}

.teacher-menu-item {
  width: 100%;
  height: 52px;
  padding: 0 14px;
  border: 0;
  border-radius: 14px;
  display: flex;
  align-items: center;
  gap: 12px;
  background: transparent;
  color: #5a6f95;
  cursor: pointer;
  text-align: left;
  transition: background 0.18s ease, color 0.18s ease;
}

.teacher-menu-item:hover {
  background: #f1f6ff;
  color: #2d69da;
}

.teacher-menu-item.active {
  background: linear-gradient(135deg, #edf4ff 0%, #e1edff 100%);
  color: #2c67d8;
  font-weight: 600;
}

.teacher-menu-icon {
  font-size: 16px;
}

.teacher-content {
  margin-left: var(--teacher-sidebar-width);
  min-height: calc(100vh - var(--teacher-header-height));
  padding: 20px 22px 28px;
}

.teacher-course-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
  padding: 20px 22px;
  border-radius: 20px;
  border: 1px solid #e7eef9;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 12px 28px rgba(53, 82, 136, 0.08);
}

.teacher-course-bar-title {
  color: #203b70;
  font-size: 22px;
  font-weight: 700;
}

.teacher-course-bar-meta {
  margin-top: 8px;
  color: #8c9bb7;
  font-size: 13px;
}

.teacher-course-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.teacher-page-body {
  min-height: calc(100vh - var(--teacher-header-height) - 110px);
}

@media (max-width: 1100px) {
  .teacher-sidebar {
    position: static;
    width: auto;
    border-right: 0;
    backdrop-filter: none;
  }

  .teacher-content {
    margin-left: 0;
  }

  .teacher-main {
    display: block;
  }
}
</style>
