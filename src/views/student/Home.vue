<template>
  <div class="student-home">
    <section class="student-home-hero">
      <div class="student-home-hero-main">
        <div class="student-home-identity">
          <el-avatar :size="76" class="student-home-avatar">
            {{ heroStudentName.slice(0, 1) }}
          </el-avatar>

          <div class="student-home-user-block">
            <div class="student-home-greet">Hi，{{ heroStudentName }}同学</div>
            <div class="student-home-meta">{{ heroCollegeName }}</div>
          </div>
        </div>
      </div>

      <div class="student-home-stats">
        <div class="student-stat-card">
          <div class="student-stat-value">{{ dashboardStats.studyDays }}</div>
          <div class="student-stat-label">连续学习/天</div>
        </div>
        <div class="student-stat-card">
          <div class="student-stat-value">{{ dashboardStats.activeLessons }}</div>
          <div class="student-stat-label">正在学习/门</div>
        </div>
        <div class="student-stat-card">
          <div class="student-stat-value">{{ dashboardStats.finishedLessons }}</div>
          <div class="student-stat-label">已完成课程/门</div>
        </div>
      </div>
    </section>

    <main class="student-home-body">
      <div class="student-home-main">
        <section class="student-card student-course-card">
          <div class="student-card-header">
            <div>
              <h2>课程入口</h2>
              <p>首页课程总进度按各章节学习进度平均值计算。当前测试数据初始均为 0%。</p>
            </div>
            <div class="student-card-actions">
              <el-segmented v-model="activeFilter" :options="filterOptions" />
            </div>
          </div>

          <div v-if="loading" class="student-empty">正在加载课程数据...</div>
          <div v-else-if="loadError" class="student-empty">{{ loadError }}</div>
          <div v-else-if="filteredLessons.length === 0" class="student-empty">
            当前暂无课程，后续接入课程后将在此展示。
          </div>
          <div v-else class="student-course-grid">
            <article
              v-for="lesson in filteredLessons"
              :key="lesson.lessonId"
              class="student-course-item"
              @click="openLesson(lesson)"
            >
              <div class="student-course-cover"></div>
              <div class="student-course-content">
                <div class="student-course-title">{{ lesson.courseName }}</div>
                <div class="student-course-teacher">{{ lesson.teacherName }}</div>
                <div class="student-course-meta-row">
                  <span>当前章节</span>
                  <strong>{{ lesson.currentChapter }}</strong>
                </div>
                <div class="student-course-progress-row">
                  <span>学习进度</span>
                  <strong>{{ getLessonProgress(lesson) }}%</strong>
                </div>
                <el-progress :percentage="getLessonProgress(lesson)" :stroke-width="6" :show-text="false" />
              </div>
            </article>
          </div>
        </section>
      </div>

      <aside class="student-home-side">
        <section class="student-side-card">
          <h3>学习系统</h3>
          <div
            ref="notificationRef"
            class="student-side-link student-side-link-notification"
            @mouseenter="handleNotificationEnter"
            @mouseleave="handleNotificationLeave"
            @click="handleNotificationTriggerClick"
          >
            <div>
              <div class="student-side-link-title">
                学习通知
                <span v-if="unreadCount > 0" class="student-side-link-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
              </div>
              <div class="student-side-link-desc">查看最新未读提醒与课程更新通知。</div>
            </div>
            <el-icon><ArrowRight /></el-icon>

            <transition name="student-notification-fade">
              <div
                v-if="notificationPanelVisible"
                class="student-notification-panel"
                @mouseenter="handleNotificationEnter"
                @mouseleave="handleNotificationLeave"
              >
                <div class="student-notification-panel-header">
                  <strong>学习通知</strong>
                  <span>未读 {{ unreadCount }} 条</span>
                </div>

                <div v-if="loadingNotifications" class="student-notification-empty">正在加载通知...</div>
                <div v-else-if="unreadPreview.length === 0" class="student-notification-empty">暂无未读消息</div>
                <button
                  v-for="item in unreadPreview"
                  :key="item.id"
                  type="button"
                  class="student-notification-item"
                  @click.stop="openNotification(item)"
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

          <div class="student-side-link" @click="showHelp = true">
            <div>
              <div class="student-side-link-title">使用说明</div>
              <div class="student-side-link-desc">课程详情页默认进入知识学习，可在顶部切换 AI 互动室。</div>
            </div>
            <el-icon><ArrowRight /></el-icon>
          </div>
        </section>

        <section class="student-side-card student-history-side-card">
          <div class="student-side-card-header">
            <h3>最近学习记录</h3>
            <p>保留最近 3 条课程学习与问答记录。</p>
          </div>

          <div v-if="historyLessons.length === 0" class="student-side-empty">
            当前暂无学习记录。
          </div>
          <div v-else class="student-history-side-list">
            <article
              v-for="lesson in historyLessons"
              :key="lesson.lessonId"
              class="student-history-side-item"
            >
              <div class="student-history-side-main">
                <div class="student-history-side-title">{{ lesson.courseName }}</div>
                <div class="student-history-side-summary">{{ getHistorySummary(lesson) }}</div>
                <div class="student-history-side-meta">{{ lesson.lastStudyAt || '最近已学习' }}</div>
              </div>
              <el-button text type="primary" @click.stop="openHistory(lesson)">查看问答</el-button>
            </article>
          </div>
        </section>
      </aside>
    </main>

    <el-drawer v-model="historyVisible" title="问答记录" size="460px">
      <div v-if="selectedHistory.length === 0" class="student-empty student-drawer-empty">当前课程暂无问答记录。</div>
      <div v-else class="student-history-chat">
        <div v-for="item in selectedHistory" :key="item.id" class="student-history-chat-item">
          <div class="student-history-chat-question">Q：{{ item.question }}</div>
          <div class="student-history-chat-answer">A：{{ item.answer }}</div>
          <div class="student-history-chat-meta">
            <span>{{ item.anchorTitle }}</span>
            <span>理解程度：{{ item.understandingLabel }}</span>
          </div>
        </div>
      </div>
    </el-drawer>

    <el-dialog v-model="showHelp" title="学生端使用说明" width="620px">
      <div class="student-help-text">
        首页展示课程入口。点击任意课程可进入课程详情页，默认查看知识学习模块；顶部固定栏中可切换至 AI 互动室进行文字或语音提问，右侧 AI 工具栏支持隐藏与恢复。
      </div>
    </el-dialog>

    <el-dialog v-model="notificationDetailVisible" title="通知详情" width="520px">
      <div v-if="activeNotification" class="student-notification-detail">
        <div class="student-notification-detail-title">{{ activeNotification.title }}</div>
        <div class="student-notification-detail-meta">
          <span>{{ activeNotification.type }}</span>
          <span>{{ activeNotification.createdAt }}</span>
        </div>
        <div class="student-notification-detail-content">{{ activeNotification.content }}</div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  getStudentLessonList,
  getStudentNotificationDetail,
  getStudentNotifications,
  markStudentNotificationRead,
  verifyStudentAuth
} from '@/api/student'
import { getFrontendTestLessons } from '@/mock/studentLessons'
import {
  ensurePlatformToken,
  getPlatformToken,
  getStudentLessonListCache,
  getStudentProfile,
  getStudentQaHistory,
  saveStudentLessonList,
  saveStudentProfile
} from '@/utils/platform'

const router = useRouter()
const loading = ref(true)
const loadError = ref('')
const activeFilter = ref('all')
const historyVisible = ref(false)
const showHelp = ref(false)
const selectedHistory = ref([])
const notifications = ref([])
const notificationPanelVisible = ref(false)
const notificationDetailVisible = ref(false)
const activeNotification = ref(null)
const loadingNotifications = ref(false)
const notificationRef = ref(null)
const supportsHover = ref(false)

const fallbackProfile = {
  studentId: 'S2026001',
  studentName: '左睿涛',
  collegeName: '计算机与软件学院',
  studyDays: 0
}

const studentProfile = ref({
  ...fallbackProfile,
  ...getStudentProfile()
})
const lessonList = ref([])
const filterOptions = [
  { label: '全部', value: 'all' },
  { label: '进行中', value: 'inProgress' },
  { label: '已完成', value: 'completed' }
]

let closeTimer = null

const heroStudentName = computed(() => studentProfile.value.studentName || fallbackProfile.studentName)
const heroCollegeName = computed(() => studentProfile.value.collegeName || fallbackProfile.collegeName)

function calculateLessonProgress(lesson) {
  const chapters = (lesson.units || []).flatMap((unit) => unit.chapters || [])
  if (!chapters.length) return Number(lesson.progressPercent || 0)
  return Math.round(chapters.reduce((sum, chapter) => sum + Number(chapter.progressPercent || 0), 0) / chapters.length)
}

function normalizeLesson(lesson) {
  const currentPage = Number(lesson.currentPage || 1)
  const chapters = (lesson.units || []).flatMap((unit) => unit.chapters || [])
  const currentChapter = chapters.find((chapter) => chapter.pageNo === currentPage) || chapters[0] || {}
  const progressPercent = calculateLessonProgress(lesson)
  return {
    ...lesson,
    progressPercent,
    status: progressPercent >= 100 ? 'completed' : 'inProgress',
    currentChapter: currentChapter.chapterTitle || lesson.currentChapter || '待学习章节',
    currentKnowledgePointName: currentChapter.chapterTitle || lesson.currentKnowledgePointName || '待学习章节'
  }
}

const dashboardStats = computed(() => {
  const completed = lessonList.value.filter((item) => calculateLessonProgress(item) >= 100).length
  const active = lessonList.value.filter((item) => calculateLessonProgress(item) < 100).length
  return {
    studyDays: studentProfile.value.studyDays ?? fallbackProfile.studyDays,
    activeLessons: active,
    finishedLessons: completed
  }
})

const unreadNotifications = computed(() => notifications.value.filter((item) => !item.read))
const unreadPreview = computed(() => unreadNotifications.value.slice(0, 4))
const unreadCount = computed(() => unreadNotifications.value.length)

const filteredLessons = computed(() => {
  if (activeFilter.value === 'all') return lessonList.value
  return lessonList.value.filter((item) => item.status === activeFilter.value)
})

const historyLessons = computed(() => {
  return [...lessonList.value]
    .sort((a, b) => new Date(b.lastStudyAt || 0) - new Date(a.lastStudyAt || 0))
    .slice(0, 3)
})

async function bootstrapStudent() {
  loading.value = true
  loadError.value = ''
  const token = ensurePlatformToken('student_demo_token_001')

  try {
    const authRes = await verifyStudentAuth({
      token,
      platform: 'chaoxing',
      clientType: /Mobile|Android|iPhone/i.test(navigator.userAgent) ? 'mobile' : 'pc'
    })

    studentProfile.value = {
      ...fallbackProfile,
      ...(authRes.data?.student || {})
    }
    saveStudentProfile(studentProfile.value)

    const lessonsRes = await getStudentLessonList({
      studentId: studentProfile.value.studentId,
      token: getPlatformToken()
    })

    const apiLessons = (lessonsRes.data?.lessons || []).map(normalizeLesson)
    if (apiLessons.length > 0) {
      lessonList.value = apiLessons
    } else {
      lessonList.value = getFrontendTestLessons().map(normalizeLesson)
    }

    saveStudentLessonList(lessonList.value)
  } catch (error) {
    studentProfile.value = {
      ...fallbackProfile,
      ...studentProfile.value
    }
    lessonList.value = []
    loadError.value = error?.msg || '课程数据加载失败'
    ElMessage.error(loadError.value)
  } finally {
    loading.value = false
  }
}

async function loadNotifications() {
  if (!studentProfile.value.studentId) return
  loadingNotifications.value = true
  try {
    const res = await getStudentNotifications({ studentId: studentProfile.value.studentId })
    notifications.value = res.data?.notifications || []
  } catch (error) {
    notifications.value = []
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

function handleNotificationEnter() {
  if (!supportsHover.value) return
  clearCloseTimer()
  notificationPanelVisible.value = true
}

function handleNotificationLeave() {
  if (!supportsHover.value) return
  clearCloseTimer()
  closeTimer = window.setTimeout(() => {
    notificationPanelVisible.value = false
  }, 120)
}

function handleNotificationTriggerClick() {
  if (supportsHover.value) {
    notificationPanelVisible.value = true
    return
  }
  notificationPanelVisible.value = !notificationPanelVisible.value
}

async function openNotification(item) {
  try {
    const detailRes = await getStudentNotificationDetail({
      studentId: studentProfile.value.studentId,
      notificationId: item.id
    })
    activeNotification.value = detailRes.data
    notificationDetailVisible.value = true
    notificationPanelVisible.value = false

    await markStudentNotificationRead({
      studentId: studentProfile.value.studentId,
      notificationId: item.id
    })

    notifications.value = notifications.value.map((notification) => (
      notification.id === item.id ? { ...notification, read: true } : notification
    ))
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

function openLesson(lesson) {
  router.push(`/student/player/${lesson.lessonId}`)
}

function openHistory(lesson) {
  selectedHistory.value = getStudentQaHistory(lesson.lessonId)
  historyVisible.value = true
}

function getLessonProgress(lesson) {
  return calculateLessonProgress(lesson)
}

function getHistorySummary(lesson) {
  return `当前章节 ${lesson.currentChapter} · 进度 ${getLessonProgress(lesson)}% · 问答 ${lesson.questionCount || 0} 条`
}

onMounted(async () => {
  supportsHover.value = window.matchMedia('(hover: hover)').matches
  document.addEventListener('click', handleDocumentClick)

  const cachedLessons = (getStudentLessonListCache() || []).map(normalizeLesson)
  if (cachedLessons.length > 0) {
    lessonList.value = cachedLessons
  }

  await bootstrapStudent()
  await loadNotifications()
})

onBeforeUnmount(() => {
  clearCloseTimer()
  document.removeEventListener('click', handleDocumentClick)
})
</script>

<style scoped>
.student-home {
  min-height: 100vh;
  background: linear-gradient(180deg, #eff2fb 0%, #f7f8fc 100%);
}

.student-home-hero {
  min-height: 300px;
  padding: 88px 48px 112px;
  background:
    linear-gradient(135deg, rgba(39, 153, 120, 0.96), rgba(63, 179, 145, 0.9)),
    radial-gradient(circle at 24% 22%, rgba(255, 255, 255, 0.09), transparent 30%),
    radial-gradient(circle at 82% 24%, rgba(255, 255, 255, 0.05), transparent 24%);
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 24px;
  align-items: end;
  color: #fff;
}

.student-home-identity {
  display: flex;
  align-items: center;
  gap: 20px;
  padding-top: 20px;
}

.student-home-avatar {
  border: 2px solid rgba(255, 255, 255, 0.72);
  background: rgba(240, 243, 250, 0.4);
  color: #fff;
}

.student-home-greet {
  font-size: 22px;
  font-weight: 600;
  line-height: 1.35;
}

.student-home-meta {
  margin-top: 10px;
  color: rgba(255, 255, 255, 0.88);
  font-size: 17px;
  line-height: 1.7;
}

.student-home-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  align-self: end;
}

.student-stat-card {
  min-height: 112px;
  padding: 16px 14px;
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.05);
  text-align: center;
  backdrop-filter: blur(6px);
}

.student-stat-value {
  font-size: 24px;
  font-weight: 700;
}

.student-stat-label {
  margin-top: 12px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.84);
}

.student-home-body {
  position: relative;
  z-index: 1;
  margin-top: -72px;
  padding: 0 48px 40px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 24px;
  align-items: start;
}

.student-home-main {
  display: grid;
  gap: 24px;
}

.student-card,
.student-side-card {
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid #edf2f8;
  box-shadow: 0 16px 40px rgba(25, 43, 92, 0.05);
}

.student-card {
  padding: 30px 34px;
}

.student-side-card {
  padding: 26px 28px;
}

.student-card-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
  margin-bottom: 24px;
}

.student-card-header h2,
.student-side-card h3 {
  margin: 0;
  color: #1a2b57;
  font-size: 26px;
  font-weight: 600;
}

.student-card-header p {
  margin: 10px 0 0;
  color: #7a86a0;
  font-size: 14px;
  line-height: 1.8;
}

.student-card-actions {
  flex-shrink: 0;
}

.student-empty {
  min-height: 220px;
  border-radius: 22px;
  border: 1px dashed #d7e0f0;
  background: #fbfcff;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8490aa;
  font-size: 15px;
  text-align: center;
  padding: 24px;
}

.student-course-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
}

.student-course-item {
  overflow: hidden;
  border-radius: 22px;
  border: 1px solid #e7edf7;
  background: #fff;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.student-course-item:hover {
  transform: translateY(-2px);
  border-color: #d4deef;
  box-shadow: 0 16px 30px rgba(31, 47, 94, 0.08);
}

.student-course-cover {
  height: 150px;
  background: linear-gradient(135deg, #f7f9fc 0%, #edf2f8 100%);
  border-bottom: 1px solid #eef3f8;
}

.student-course-content {
  padding: 20px;
}

.student-course-title {
  font-size: 19px;
  color: #1c2a52;
  line-height: 1.5;
  min-height: 56px;
}

.student-course-teacher {
  margin-top: 10px;
  color: #7f8aa2;
  font-size: 14px;
}

.student-course-meta-row,
.student-course-progress-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 14px;
  color: #6b7793;
  font-size: 13px;
}

.student-course-meta-row strong,
.student-course-progress-row strong {
  color: #1c2a52;
  font-weight: 600;
  text-align: right;
}

.student-home-side {
  display: grid;
  gap: 24px;
}

.student-side-card-header h3 {
  margin: 0;
}

.student-side-card-header p {
  margin: 10px 0 0;
  color: #7b86a1;
  font-size: 13px;
  line-height: 1.7;
}

.student-side-link {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 18px 0;
  border-top: 1px solid #edf2f8;
  cursor: pointer;
}

.student-side-link:first-of-type {
  margin-top: 14px;
}

.student-side-link-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #1c2a52;
  font-size: 18px;
  font-weight: 600;
}

.student-side-link-desc {
  margin-top: 8px;
  color: #7b86a1;
  font-size: 14px;
  line-height: 1.7;
}

.student-side-link-badge {
  display: inline-flex;
  min-width: 22px;
  height: 22px;
  padding: 0 7px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: #ef4444;
  color: #fff;
  font-size: 12px;
  line-height: 1;
}

.student-side-link-notification > .el-icon,
.student-side-link > .el-icon {
  margin-top: 3px;
  color: #8e99b1;
}

.student-notification-panel {
  position: absolute;
  top: 50%;
  right: calc(100% + 14px);
  left: auto;
  transform: translateY(-50%);
  width: min(340px, calc(100vw - 440px));
  max-height: 360px;
  overflow: auto;
  padding: 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid rgba(222, 230, 245, 0.95);
  box-shadow: 0 22px 50px rgba(20, 40, 80, 0.16);
  color: #13254b;
  z-index: 20;
}

.student-notification-panel-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.student-notification-panel-header strong {
  font-size: 15px;
}

.student-notification-panel-header span,
.student-notification-item-meta,
.student-notification-empty {
  color: #7b86a1;
  font-size: 12px;
}

.student-notification-empty {
  padding: 16px 0 6px;
}

.student-notification-item {
  width: 100%;
  padding: 14px 0;
  border: 0;
  border-top: 1px solid #edf2f9;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.student-notification-item:first-of-type {
  border-top: 0;
}

.student-notification-item-title {
  color: #182a55;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.student-notification-item-summary {
  margin-top: 6px;
  color: #6f7c98;
  font-size: 12px;
  line-height: 1.7;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.student-notification-item-meta {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.student-help-text,
.student-notification-detail-content,
.student-drawer-empty {
  color: #5f6f93;
  line-height: 1.9;
  font-size: 14px;
}

.student-notification-detail-title {
  color: #1c2a52;
  font-size: 20px;
  font-weight: 600;
}

.student-notification-detail-meta {
  margin: 12px 0 18px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #8a95ad;
  font-size: 13px;
}

.student-history-chat {
  display: grid;
  gap: 16px;
}

.student-history-chat-item {
  padding: 18px;
  border-radius: 18px;
  background: #f8fbff;
  border: 1px solid #e8eef8;
}

.student-history-chat-question,
.student-history-chat-answer {
  color: #1f2d53;
  line-height: 1.8;
}

.student-history-chat-answer {
  margin-top: 8px;
  color: #5e6d92;
}

.student-history-chat-meta {
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #8792aa;
  font-size: 12px;
}

.student-history-side-card {
  padding-top: 24px;
}

.student-side-empty {
  margin-top: 18px;
  padding: 18px 16px;
  border-radius: 18px;
  background: #fbfcff;
  border: 1px dashed #d7e0f0;
  color: #8490aa;
  font-size: 13px;
  line-height: 1.8;
}

.student-history-side-list {
  margin-top: 18px;
  display: grid;
  gap: 14px;
}

.student-history-side-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 14px;
  align-items: start;
  padding: 16px 0;
  border-top: 1px solid #edf2f8;
}

.student-history-side-item:first-child {
  padding-top: 0;
  border-top: 0;
}

.student-history-side-title {
  color: #1c2a52;
  font-size: 16px;
  line-height: 1.5;
}

.student-history-side-summary,
.student-history-side-meta {
  color: #7f8aa2;
  font-size: 12px;
  line-height: 1.7;
}

.student-history-side-summary {
  margin-top: 6px;
}

.student-history-side-meta {
  margin-top: 4px;
}

.student-notification-fade-enter-active,
.student-notification-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.student-notification-fade-enter-from,
.student-notification-fade-leave-to {
  opacity: 0;
  transform: translate(-8px, -50%);
}

@media (max-width: 1100px) {
  .student-home-body {
    grid-template-columns: 1fr;
  }

  .student-home-stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .student-notification-panel {
    top: calc(100% + 10px);
    right: auto;
    left: 0;
    transform: none;
    width: min(360px, calc(100vw - 72px));
  }

  .student-notification-fade-enter-from,
  .student-notification-fade-leave-to {
    transform: translateY(6px);
  }
}

@media (max-width: 768px) {
  .student-home-hero {
    grid-template-columns: 1fr;
    padding: 76px 20px 104px;
  }

  .student-home-body {
    margin-top: -56px;
    padding: 0 20px 28px;
  }

  .student-home-stats {
    grid-template-columns: 1fr;
  }

  .student-card,
  .student-side-card {
    padding: 24px 20px;
  }

  .student-card-header {
    flex-direction: column;
  }

  .student-history-side-item {
    grid-template-columns: 1fr;
  }

  .student-notification-panel {
    width: min(360px, calc(100vw - 40px));
  }
}
</style>
