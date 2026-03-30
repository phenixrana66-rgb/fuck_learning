<template>
  <header class="student-topbar">
    <div class="student-brand">
      <div class="student-brand-logo">智</div>
      <div class="student-brand-text">
        <div class="student-brand-title">在线大学 AI 智课</div>
        <div class="student-brand-subtitle">{{ schoolName }}</div>
      </div>
    </div>

    <div class="student-topbar-actions">
      <div
        ref="notificationRef"
        class="student-notification"
        @mouseenter="handleEnter"
        @mouseleave="handleLeave"
      >
        <button
          type="button"
          class="student-notification-trigger"
          aria-label="消息提醒"
          @click="handleTriggerClick"
        >
          <el-badge :hidden="unreadCount === 0" :value="unreadCount" :max="99">
            <el-icon><Bell /></el-icon>
          </el-badge>
        </button>

        <transition name="student-notification-fade">
          <div
            v-if="notificationPanelVisible"
            class="student-notification-panel"
            @mouseenter="handleEnter"
            @mouseleave="handleLeave"
          >
            <div class="student-notification-panel-header">
              <div>
                <strong>消息提醒</strong>
                <span>当前未读 {{ unreadCount }} 条</span>
              </div>
            </div>

            <div v-if="loadingNotifications" class="student-notification-empty">
              正在加载通知...
            </div>
            <div v-else-if="unreadNotifications.length === 0" class="student-notification-empty">
              暂无未读消息
            </div>
            <button
              v-for="item in unreadNotifications"
              :key="item.id"
              type="button"
              class="student-notification-item"
              @click="openNotification(item)"
            >
              <div class="student-notification-item-title">{{ item.title }}</div>
              <div class="student-notification-item-summary">{{ item.summary }}</div>
              <div class="student-notification-item-meta">
                <span>{{ item.type }}</span>
                <span>{{ item.createdAt }}</span>
              </div>
            </button>
          </div>
        </transition>
      </div>

      <div class="student-topbar-user">
        <el-avatar :size="42">
          {{ displayName.slice(0, 1) }}
        </el-avatar>
        <div class="student-topbar-user-meta">
          <div class="student-topbar-user-name">{{ displayName }}</div>
          <div class="student-topbar-user-sub">{{ majorName || '学习通免登账号' }}</div>
        </div>
      </div>
    </div>
  </header>

  <el-dialog v-model="detailVisible" title="通知详情" width="520px">
    <div v-if="activeNotification" class="student-notification-detail">
      <div class="student-notification-detail-title">{{ activeNotification.title }}</div>
      <div class="student-notification-detail-meta">
        <span>{{ activeNotification.type }}</span>
        <span>{{ activeNotification.createdAt }}</span>
      </div>
      <div class="student-notification-detail-content">{{ activeNotification.content }}</div>
    </div>
  </el-dialog>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Bell } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  getStudentNotificationDetail,
  getStudentNotifications,
  markStudentNotificationRead
} from '@/api/student'

const props = defineProps({
  student: {
    type: Object,
    default: () => ({})
  },
  schoolName: {
    type: String,
    default: '超星学习通'
  }
})

const displayName = computed(() => props.student.studentName || props.student.userName || '同学')
const majorName = computed(() => props.student.majorName || props.student.collegeName || '')
const studentId = computed(() => props.student.studentId || '')

const notificationRef = ref(null)
const notifications = ref([])
const notificationPanelVisible = ref(false)
const detailVisible = ref(false)
const activeNotification = ref(null)
const loadingNotifications = ref(false)
const supportsHover = ref(false)

let closeTimer = null

const unreadNotifications = computed(() => notifications.value.filter((item) => !item.read))
const unreadCount = computed(() => unreadNotifications.value.length)

async function loadNotifications() {
  if (!studentId.value) return

  loadingNotifications.value = true
  try {
    const res = await getStudentNotifications({
      studentId: studentId.value
    })
    notifications.value = res.data.notifications || []
  } catch (error) {
    ElMessage.error(error?.msg || '通知加载失败')
  } finally {
    loadingNotifications.value = false
  }
}

function clearCloseTimer() {
  if (closeTimer) {
    window.clearTimeout(closeTimer)
    closeTimer = null
  }
}

function handleEnter() {
  if (!supportsHover.value) return
  clearCloseTimer()
  notificationPanelVisible.value = true
}

function handleLeave() {
  if (!supportsHover.value) return
  clearCloseTimer()
  closeTimer = window.setTimeout(() => {
    notificationPanelVisible.value = false
  }, 120)
}

function handleTriggerClick() {
  if (supportsHover.value) {
    notificationPanelVisible.value = true
    return
  }
  notificationPanelVisible.value = !notificationPanelVisible.value
}

async function openNotification(item) {
  try {
    const detailRes = await getStudentNotificationDetail({
      studentId: studentId.value,
      notificationId: item.id
    })

    activeNotification.value = detailRes.data
    detailVisible.value = true
    notificationPanelVisible.value = false

    await markStudentNotificationRead({
      studentId: studentId.value,
      notificationId: item.id
    })

    notifications.value = notifications.value.map((notification) => {
      if (notification.id !== item.id) return notification
      return { ...notification, read: true }
    })
  } catch (error) {
    ElMessage.error(error?.msg || '通知详情加载失败')
  }
}

function handleDocumentClick(event) {
  if (!notificationPanelVisible.value || supportsHover.value) return
  const target = event.target
  if (target instanceof Node && notificationRef.value?.contains(target)) return
  notificationPanelVisible.value = false
}

watch(
  studentId,
  (value) => {
    if (value) {
      loadNotifications()
    }
  },
  { immediate: true }
)

onMounted(() => {
  supportsHover.value = window.matchMedia('(hover: hover)').matches
  document.addEventListener('click', handleDocumentClick)
})

onBeforeUnmount(() => {
  clearCloseTimer()
  document.removeEventListener('click', handleDocumentClick)
})
</script>

<style scoped>
.student-topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  min-height: 88px;
  padding: 18px 32px;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1px solid #e8edf6;
  box-shadow: 0 10px 30px rgba(16, 32, 84, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  color: #13254b;
  backdrop-filter: blur(10px);
}

.student-brand {
  display: flex;
  align-items: center;
  gap: 16px;
}

.student-brand-logo {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  background: linear-gradient(135deg, #2a56ea 0%, #4567ff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  box-shadow: 0 10px 24px rgba(42, 86, 234, 0.28);
}

.student-brand-title {
  font-size: 20px;
  font-weight: 700;
}

.student-brand-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #5e6b89;
  letter-spacing: 0.08em;
}

.student-topbar-actions {
  display: flex;
  align-items: center;
  gap: 20px;
}

.student-notification {
  position: relative;
}

.student-notification-trigger {
  width: 44px;
  height: 44px;
  border: 1px solid #dce4f3;
  border-radius: 14px;
  background: #f7f9fd;
  color: #173061;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.student-notification-trigger:hover {
  background: #eef3ff;
  border-color: #bdd0ff;
}

.student-notification-trigger :deep(svg) {
  font-size: 20px;
}

.student-notification-panel {
  position: absolute;
  top: calc(100% + 12px);
  right: 0;
  width: 320px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid #e7edf7;
  background: #fff;
  box-shadow: 0 20px 48px rgba(17, 32, 73, 0.14);
}

.student-notification-panel-header {
  margin-bottom: 12px;
}

.student-notification-panel-header strong {
  display: block;
  color: #182b56;
  font-size: 16px;
}

.student-notification-panel-header span {
  display: block;
  margin-top: 4px;
  color: #7c88a7;
  font-size: 12px;
}

.student-notification-empty {
  padding: 28px 12px;
  text-align: center;
  color: #7f8aa7;
  font-size: 14px;
}

.student-notification-item {
  width: 100%;
  padding: 14px 0;
  border: 0;
  border-top: 1px solid #edf2f8;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.student-notification-item:first-of-type {
  border-top: 0;
}

.student-notification-item-title {
  color: #15264d;
  font-size: 14px;
  font-weight: 600;
}

.student-notification-item-summary {
  margin-top: 6px;
  color: #6e7b99;
  font-size: 13px;
  line-height: 1.6;
}

.student-notification-item-meta {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #95a0ba;
  font-size: 12px;
}

.student-topbar-user {
  display: flex;
  align-items: center;
  gap: 12px;
}

.student-topbar-user-name {
  font-size: 16px;
  font-weight: 600;
}

.student-topbar-user-sub {
  margin-top: 4px;
  font-size: 12px;
  color: #66748f;
}

.student-notification-detail-title {
  color: #16284f;
  font-size: 20px;
  font-weight: 700;
}

.student-notification-detail-meta {
  margin-top: 10px;
  display: flex;
  gap: 16px;
  color: #7f8ba7;
  font-size: 13px;
}

.student-notification-detail-content {
  margin-top: 18px;
  color: #44516d;
  line-height: 1.85;
  white-space: pre-wrap;
}

.student-notification-fade-enter-active,
.student-notification-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.student-notification-fade-enter-from,
.student-notification-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

@media (max-width: 992px) {
  .student-topbar {
    padding: 16px;
    gap: 16px;
  }

  .student-brand-title {
    font-size: 18px;
  }

  .student-notification-panel {
    width: min(320px, calc(100vw - 32px));
    right: -8px;
  }
}

@media (max-width: 768px) {
  .student-topbar {
    align-items: flex-start;
  }

  .student-brand-title {
    font-size: 16px;
  }

  .student-brand-subtitle,
  .student-topbar-user-sub {
    font-size: 11px;
  }
}
</style>
