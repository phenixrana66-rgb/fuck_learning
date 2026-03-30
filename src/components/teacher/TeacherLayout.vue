<template>
  <div class="teacher-layout">
    <header class="teacher-header">
      <div class="teacher-header-left">
        <div class="logo-box">
          <div class="logo-mark">泛</div>
          <div class="logo-text">超星 AI 互动智课</div>
        </div>
      </div>

      <div class="teacher-header-right">
        <div class="teacher-user">
          <el-avatar :size="27">
            {{ (teacherInfo.teacherName || teacherInfo.userName || '师').slice(0, 1) }}
          </el-avatar>
          <span class="teacher-name">
            {{ teacherInfo.teacherName || teacherInfo.userName || '教师用户' }}
          </span>
        </div>
      </div>
    </header>

    <div class="teacher-main">
      <aside class="teacher-sidebar">
      <div class="course-cover">
        <div class="course-cover-inner">
          <div class="course-cover-title">{{ currentCourse.courseName || '未选择课程' }}</div>
          <div class="course-cover-sub">AI 智课教师端</div>
        </div>
      </div>

      <div class="menu-group-title">功能菜单</div>

      <div
        v-for="item in menuList"
        :key="item.path"
        class="menu-item"
        :class="{ active: route.path === item.path }"
        @click="go(item.path)"
      >
        <el-icon class="menu-icon">
          <component :is="item.icon" />
        </el-icon>
        <span>{{ item.label }}</span>
      </div>
    </aside>

      <section class="teacher-content">
      <div class="teacher-course-bar">
        <div class="course-info">
          <div class="course-name">{{ currentCourse.courseName || '未选择课程' }}</div>
          <div class="course-meta">
            课程ID：{{ currentCourse.courseId || '-' }}
            <span class="dot">•</span>
            班级ID：{{ currentCourse.classId || '-' }}
          </div>
        </div>

        <div class="course-actions">
          <el-button size="small" @click="go('/teacher/login')">重新同步</el-button>
          <el-button size="small" type="primary" @click="go('/teacher/lesson-manage')">
            返回管理
          </el-button>
        </div>
      </div>

      <div class="teacher-page-body">
        <slot />
      </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { useRouter, useRoute } from 'vue-router'
import {
  House,
  DataBoard,
  Document,
  EditPen,
  Microphone
} from '@element-plus/icons-vue'
import { getTeacherProfile, getCurrentCourse } from '@/utils/platform'

const router = useRouter()
const route = useRoute()

const teacherInfo = getTeacherProfile()
const currentCourse = getCurrentCourse()

const menuList = [
  { label: '智课管理', path: '/teacher/lesson-manage', icon: House },
  { label: '课件解析', path: '/teacher/course-parse', icon: DataBoard },
  { label: '脚本生成', path: '/teacher/script-generate', icon: Document },
  { label: '脚本编辑', path: '/teacher/script-edit', icon: EditPen },
  { label: '语音合成', path: '/teacher/audio-generate', icon: Microphone }
]

function go(path) {
  router.push(path)
}
</script>

<style scoped>
.teacher-layout {
  --teacher-header-height: 69px;
  --teacher-sidebar-width: 288px;
  height: 100vh;
  overflow: hidden;
  background: #f3f6fb;
}

.teacher-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: var(--teacher-header-height);
  background: #ffffff;
  border-bottom: 1px solid #edf2f7;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  z-index: 1000;
}

.teacher-main {
  height: 100%;
  padding-top: var(--teacher-header-height);
}

.logo-box {
  display: flex;
  align-items: center;
  gap: 11px;
}

.logo-mark {
  width: 37px;
  height: 37px;
  border-radius: 11px;
  background: linear-gradient(135deg, #ff6a5f 0%, #ff4d4f 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 19px;
}

.logo-text {
  font-size: 22px;
  font-weight: 700;
  color: #1f2d3d;
}

.teacher-user {
  display: flex;
  align-items: center;
  gap: 10px;
}

.teacher-name {
  color: #303133;
  font-size: 14px;
  font-weight: 500;
}

.teacher-sidebar {
  position: fixed;
  top: var(--teacher-header-height);
  left: 0;
  bottom: 0;
  width: var(--teacher-sidebar-width);
  background: #fff;
  border-right: 1px solid #edf2f7;
  overflow-y: auto;
  z-index: 900;
}

.teacher-content {
  height: calc(100vh - var(--teacher-header-height));
  margin-left: var(--teacher-sidebar-width);
  overflow-y: auto;
  padding: 24px;
  min-width: 0;
}

.teacher-course-bar {
  background: #fff;
  border-radius: 16px;
  padding: 26px 30px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 6px 18px rgba(31, 35, 41, 0.06);
  margin-bottom: 24px;
}

.teacher-page-body {
  min-height: 200px;
}

.course-cover {
  padding: 16px 11px 14px;
}

.course-cover-inner {
  min-height: 138px;
  border-radius: 16px;
  padding: 19px;
  background: linear-gradient(135deg, #2d3561 0%, #4f5fb5 100%);
  color: #fff;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  box-shadow: 0 12px 24px rgba(50, 69, 120, 0.22);
}

.course-cover-title {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.45;
  word-break: break-word;
}

.course-cover-sub {
  margin-top: 8px;
  font-size: 13px;
  opacity: 0.95;
}

.menu-group-title {
  padding: 5px 13px 10px;
  font-size: 12px;
  color: #909399;
}

.menu-item {
  height: 58px;
  padding: 0 19px;
  display: flex;
  align-items: center;
  gap: 11px;
  color: #606266;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 14px;
}

.menu-item:hover {
  background: #f5f9ff;
  color: #409eff;
}

.menu-item.active {
  background: #eaf3ff;
  color: #2f7df6;
  border-right: 4px solid #2f7df6;
}

.menu-icon {
  font-size: 19px;
}

.course-name {
  font-size: 28px;
  font-weight: 700;
  color: #1f2d3d;
  margin-bottom: 8px;
}

.course-meta {
  font-size: 16px;
  color: #909399;
}

.dot {
  margin: 0 10px;
}

@media (max-width: 1200px) {
  .teacher-layout {
    --teacher-sidebar-width: 240px;
  }
}

@media (max-width: 992px) {
  .teacher-layout {
    height: auto;
    min-height: 100vh;
    overflow: visible;
  }

  .teacher-header {
    position: static;
  }

  .teacher-main {
    height: auto;
    padding-top: 0;
  }

  .teacher-sidebar {
    display: none;
  }

  .teacher-content {
    height: auto;
    margin-left: 0;
    overflow: visible;
    min-height: auto;
    padding: 16px;
  }

  .teacher-course-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .logo-text {
    font-size: 22px;
  }
}
</style>
