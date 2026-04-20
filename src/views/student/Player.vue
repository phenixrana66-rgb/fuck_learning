<template>
  <div class="student-player-page">
    <header class="student-player-topbar">
      <div
        class="student-topbar-brand"
        role="button"
        tabindex="0"
        @click="goStudentHome"
        @keydown.enter.prevent="goStudentHome"
        @keydown.space.prevent="goStudentHome"
      >
        <img class="student-topbar-brand-mark" src="/chaoxing-erya-logo.svg" alt="超星尔雅" />
        <div class="student-topbar-brand-name">尔雅</div>
      </div>

      <div class="student-topbar-center">
        <nav ref="topbarNavRef" class="student-topbar-nav">
          <span class="student-topbar-nav-indicator" :style="navIndicatorStyle"></span>
          <button
            v-for="item in primaryNavItems"
            :key="item.value"
            :ref="(element) => setPrimaryNavButton(element, item.value)"
            type="button"
            class="student-topbar-nav-item"
            :class="{ active: activeView === item.value }"
            @click="switchView(item.value)"
          >
            {{ item.label }}
          </button>
        </nav>
      </div>

      <div ref="topbarUserRef" class="student-topbar-user" :class="{ open: userMenuOpen }">
        <button type="button" class="student-topbar-user-trigger" @click="toggleUserMenu">
          <el-avatar :size="42">{{ (studentProfile.studentName || fallbackProfile.studentName).slice(0, 1) }}</el-avatar>
          <span>{{ studentProfile.studentName || fallbackProfile.studentName }}</span>
          <el-icon class="student-topbar-user-arrow"><ArrowDown /></el-icon>
        </button>
        <div v-if="userMenuOpen" class="student-topbar-user-menu">
          <button type="button" class="student-topbar-user-menu-item" @click="handleUserMenuAction('home')">回到首页</button>
          <button type="button" class="student-topbar-user-menu-item" @click="handleUserMenuAction('message')">消息中心</button>
        </div>
      </div>
    </header>

    <main
      ref="pageMainRef"
      class="student-player-main app-scrollable"
      :class="{ 'is-progress-view': activeView === 'progress' }"
    >
      <section v-if="showCourseOverview" class="student-course-overview">
        <div class="student-course-overview-main">
          <h1>{{ lesson.courseName || lesson.lessonName }}</h1>
          <h3 class="student-course-overview-teacher">授课教师：{{ lesson.teacherName || '未设置' }}</h3>
        </div>
        <div class="student-course-overview-meta">
          <div class="student-course-overview-metric">
            <span>课程总进度</span>
            <strong>{{ overallProgress }}%</strong>
          </div>
          <div class="student-course-overview-metric">
            <span>章节理解度</span>
            <strong>{{ overallMastery }}%</strong>
          </div>
        </div>
      </section>

      <section v-if="activeView === 'knowledge'" class="student-knowledge-page">
        <section
          v-for="unit in aggregatedUnitChapters"
          :key="unit.unitId"
          class="student-unit-section"
        >
          <div class="student-unit-header">
            <div class="student-unit-header-main">
              <div class="student-unit-badge">知识单元</div>
              <h2>{{ unit.unitTitle }}</h2>
            </div>
            <div class="student-unit-header-meta">{{ unit.chapters?.filter((chapter) => Number(chapter.progressPercent || 0) >= 100).length || 0 }}/{{ unit.chapters?.length || 0 }} 已完成</div>
          </div>

          <div class="student-chapter-grid">
            <article
              v-for="chapter in unit.chapters"
              :key="chapter.chapterId"
              class="student-chapter-card"
              :class="{ active: chapter.chapterId === activeKnowledgeChapter.chapterId }"
              @click="setActiveKnowledgeChapter(chapter)"
            >
              <div class="student-chapter-card-head">
                <div>
                  <div class="student-chapter-status" :class="getAggregatedChapterStatusClass(chapter)">{{ getAggregatedChapterStatusLabel(chapter) }}</div>
                  <h3>{{ chapter.chapterTitle }}</h3>
                </div>
                <div class="student-chapter-mastery-badge">
                  <span>掌握度</span>
                  <strong>{{ Number(chapter.masteryPercent || 0) }}%</strong>
                </div>
              </div>
              <div class="student-chapter-card-footer">
                <div class="student-chapter-progress-block">
                  <div class="student-chapter-progress-text">
                    <span>学习进度</span>
                    <strong>{{ Number(chapter.progressPercent || 0) }}%</strong>
                  </div>
                  <el-progress :percentage="Number(chapter.progressPercent || 0)" :stroke-width="8" :show-text="false" />
                </div>
                <div class="student-chapter-footer-row">
                  <button type="button" class="student-knowledge-action-button" @click.stop="goToKnowledgeLearning(chapter)">
                    <span class="student-knowledge-action-button-core">
                      <span class="student-knowledge-action-button-text">进入章节</span>
                      <span class="student-knowledge-action-button-glow" aria-hidden="true"></span>
                    </span>
                  </button>
                </div>
              </div>
            </article>
          </div>
        </section>
      </section>

      <section v-else-if="activeView === 'progress'" class="student-progress-page">
        <section class="student-progress-hero">
          <div class="student-progress-hero-main">
            <div class="student-progress-hero-copy">
              <h2>从上次学习位置继续，按当前状态调整学习节奏。</h2>
            </div>
            <div class="student-progress-hero-actions">
              <button type="button" class="student-resume-button" @click="resumeLearning">
                <span class="student-resume-button-core">
                  <span class="student-resume-button-text">{{ resumeLoading ? '正在续学...' : '继续学习' }}</span>
                  <span class="student-resume-button-glow" aria-hidden="true"></span>
                </span>
              </button>
            </div>
          </div>

          <div class="student-progress-stats">
            <div class="student-progress-stats-top">
              <div class="student-progress-stat-card">
                <span>章节总数</span>
                <strong>{{ chapterCount }} 个</strong>
              </div>
              <div class="student-progress-stat-card">
                <span>最近问答</span>
                <strong>{{ qaHistoryCount }} 条</strong>
              </div>
            </div>
            <div class="student-progress-stats-bottom">
              <div class="student-progress-stat-card chapter">
                <span>当前章节</span>
                <strong>{{ recommendedResumeChapter.chapterTitle || '待学习章节' }}</strong>
              </div>
            </div>
          </div>
        </section>

        <section class="student-progress-panel student-course-mastery-panel">
          <div class="student-progress-panel-head">
            <div>
              <div class="student-progress-panel-title">课程掌握度</div>
            </div>
          </div>

          <div class="student-course-mastery-card">
            <div v-if="allChapters.length" class="student-course-mastery-list">
              <div
                v-for="chapter in allChapters"
                :key="chapter.chapterId"
                class="student-course-mastery-item"
              >
                <div class="student-course-mastery-item-title">{{ chapter.chapterTitle }}</div>
                <div class="student-course-mastery-item-shell">
                  <div class="student-course-mastery-item-head">
                    <span class="student-course-mastery-item-label">章节掌握度</span>
                    <strong class="student-course-mastery-item-value">{{ Number(chapter.masteryPercent || 0) }}%</strong>
                  </div>
                  <el-progress
                    :percentage="Number(chapter.masteryPercent || 0)"
                    :stroke-width="10"
                    :show-text="false"
                    class="student-course-mastery-bar"
                  />
                </div>
              </div>
            </div>
            <div v-else class="student-course-mastery-empty">
              暂无章节掌握度数据
            </div>
          </div>
        </section>
      </section>

      <section v-else-if="activeView === 'ai'" class="student-ai-page" :class="{ collapsed: !aiToolsVisible }">
        <div class="student-ai-chat-card">
          <div class="student-ai-chat-header compact">
            <div class="student-ai-chat-header-main">
              <div class="student-ai-chat-title">AI实时问答</div>
            </div>
            <button type="button" class="student-ai-new-chat-button" @click="startNewConversation">新对话</button>
          </div>

          <div class="student-ai-chat-body app-scrollable" :class="{ empty: chatList.length === 0 }">
            <div v-if="chatList.length" class="student-chat-list">
              <div
                v-for="item in chatList"
                :key="item.id"
                class="student-chat-item"
                :class="`is-${item.role}`"
              >
                <div class="student-chat-role">{{ item.role === 'user' ? '我' : 'AI 学伴' }}</div>
                <div class="student-chat-bubble">
                  <div class="student-chat-content">{{ item.content }}</div>
                  <div v-if="item.relatedPoints?.length" class="student-chat-points">
                    <span v-for="point in item.relatedPoints" :key="point" class="student-chat-point-tag">{{ point }}</span>
                  </div>
                </div>
              </div>
              <div v-if="asking && !assistantStreamingStarted" class="student-chat-item is-assistant pending">
                <div class="student-chat-role">AI 学伴</div>
                <div class="student-chat-loading">
                  <span class="student-inline-loading" aria-hidden="true"></span>
                </div>
              </div>
            </div>
            <div v-else class="student-ai-welcome">
              <div class="student-ai-welcome-suggestions">
                <button
                  v-for="question in aiSuggestedQuestions"
                  :key="question"
                  type="button"
                  class="student-ai-suggestion-chip"
                  @click="submitSuggestedQuestion(question)"
                >
                  {{ question }}
                </button>
              </div>
              <div class="student-ai-welcome-spacer"></div>
            </div>
          </div>

          <div class="student-ai-input-area">
            <el-input
              v-model="questionText"
              type="textarea"
              :rows="4"
              resize="none"
              placeholder="输入你的问题"
              @keydown.enter.exact.prevent="submitTextQuestion"
            />
            <div class="student-ai-input-actions">
              <div v-if="isRecording" class="student-ai-voice-status">
                <span class="student-ai-voice-timer">{{ formatRecordingDuration(recordingSeconds) }}</span>
                <button
                  type="button"
                  class="student-ai-icon-button voice stop"
                  aria-label="结束录音"
                  @click="toggleRecording"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <rect x="7" y="7" width="10" height="10" rx="2" />
                  </svg>
                </button>
              </div>
              <button
                v-else
                type="button"
                class="student-ai-icon-button voice"
                :class="{ loading: voiceLoading }"
                :disabled="voiceLoading"
                :aria-label="voiceLoading ? '语音识别中' : '语音输入'"
                @click="!voiceLoading ? toggleRecording() : undefined"
              >
                <span v-if="voiceLoading" class="student-inline-loading" aria-hidden="true"></span>
                <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 3.5a2.5 2.5 0 0 1 2.5 2.5v5a2.5 2.5 0 0 1-5 0V6A2.5 2.5 0 0 1 12 3.5Z" />
                  <path d="M7.5 10.5a4.5 4.5 0 0 0 9 0" />
                  <path d="M12 15v5" />
                  <path d="M9 20.5h6" />
                </svg>
              </button>
              <button
                type="button"
                class="student-ai-icon-button send"
                :class="{ 'is-stop': asking }"
                :disabled="!asking && !questionText.trim()"
                :aria-label="asking ? '终止回答' : '发送问题'"
                @click="asking ? stopStreamingAnswer() : submitTextQuestion()"
              >
                <svg v-if="!asking" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 4v12" />
                  <path d="m7 9 5-5 5 5" />
                </svg>
                <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                  <rect x="7" y="7" width="10" height="10" rx="2" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <div class="student-ai-sidebar-shell" :class="{ collapsed: !aiToolsVisible }">
          <button
            type="button"
            class="student-ai-sidebar-toggle"
            :class="{ collapsed: !aiToolsVisible }"
            @click="toggleAiTools"
          >
            <el-icon><ArrowRight /></el-icon>
          </button>

          <aside v-if="aiToolsVisible" class="student-ai-sidebar-card">
            <section class="student-ai-sidebar-section">
              <div class="student-ai-tools-title">AI工具</div>
              <div class="student-ai-tool-stack">
                <button
                  v-for="tool in filteredAiTools"
                  :key="tool.id"
                  type="button"
                  class="student-ai-tool-tile"
                >
                  <span class="student-ai-tool-icon" :class="`is-${tool.id}`">{{ tool.name.slice(0, 1) }}</span>
                  <span class="student-ai-tool-name">{{ tool.name }}</span>
                  <el-icon><ArrowRight /></el-icon>
                </button>
              </div>
            </section>

            <section class="student-ai-sidebar-section history">
              <div class="student-ai-tools-title">历史问答</div>
              <div class="student-ai-history-list app-scrollable">
                <button
                  v-for="session in qaSessions"
                  :key="session.sessionId"
                  type="button"
                  class="student-ai-history-item"
                  :class="{ active: session.sessionId === activeSessionId }"
                  @click="openQaSession(session.sessionId)"
                  @dblclick.stop="startSessionTitleEdit(session)"
                >
                  <span class="student-ai-history-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24">
                      <path d="M6.5 7.5h11a3 3 0 0 1 3 3v2a3 3 0 0 1-3 3H11l-3.5 3v-3H6.5a3 3 0 0 1-3-3v-2a3 3 0 0 1 3-3Z" />
                      <path d="M9 11h6" />
                    </svg>
                  </span>
                  <input
                    v-if="editingSessionId === session.sessionId"
                    v-model="editingSessionTitle"
                    class="student-ai-history-input"
                    maxlength="24"
                    @click.stop
                    @blur="commitSessionTitleEdit(session.sessionId)"
                    @keydown.enter.prevent="commitSessionTitleEdit(session.sessionId)"
                    @keydown.esc.prevent="cancelSessionTitleEdit"
                  />
                  <span v-else class="student-ai-history-title">{{ getSessionDisplayTitle(session) }}</span>
                </button>
                <div v-if="!qaSessions.length" class="student-ai-history-empty">
                  暂无历史问答
                </div>
              </div>
            </section>
          </aside>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, ArrowRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { streamLessonInteraction } from '@/api/studentStream'
import {
  adjustStudentProgress,
  getStudentQaSessions as fetchStudentQaSessions,
  getStudentLessonList,
  getStudentProgress,
  playStudentLesson,
  resumeStudentLesson,
  saveStudentQaSession as persistStudentQaSession,
  verifyStudentAuth
} from '@/api/student'
import { findFrontendTestLesson, getFrontendTestLessons } from '@/mock/studentLessons'
import { useRealtimeAsr } from '@/composables/useRealtimeAsr'
import {
  ensurePlatformToken,
  getPlatformToken,
  getStudentLessonListCache,
  getStudentProfile,
  getStudentViewState,
  getStudentQaHistory,
  getStudentQaSessions,
  saveStudentLessonList,
  saveStudentProfile,
  saveStudentQaHistory,
  saveStudentQaSessions,
  saveStudentViewState
} from '@/utils/platform'
import { buildAggregatedKnowledgeUnits, findAggregatedChapterForSection } from '@/utils/studentKnowledge'

const route = useRoute()
const router = useRouter()
const topbarNavRef = ref(null)
const topbarUserRef = ref(null)
const pageMainRef = ref(null)
const lesson = ref({ units: [], aiTools: [] })
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
const progressState = ref({})
const activeView = ref('progress')
const aiToolsVisible = ref(true)
const questionText = ref('')
const asking = ref(false)
const activeAnswerController = ref(null)
const voiceDraftPrefix = ref('')
const assistantStreamingStarted = ref(false)
const resumeLoading = ref(false)
const adjustLoading = ref('')
const activeChapterId = ref('')
const activeKnowledgeChapterId = ref('')
const chatList = ref([])
const qaSessions = ref([])
const activeSessionId = ref('')
const editingSessionId = ref('')
const editingSessionTitle = ref('')
const primaryNavRefs = ref({})
const navIndicator = ref({ width: 0, left: 0, opacity: 0 })
const userMenuOpen = ref(false)
const progressFallbackNote = ref('若服务端节奏接口暂不可用，系统会自动回退为本地建议。')
const rhythmSuggestion = ref('建议先完成当前章节，再根据掌握度决定是否进入下一章。')
const hasLoadedLesson = ref(false)
const hasActivatedOnce = ref(false)

const primaryNavItems = [
  { label: '学习进度', value: 'progress' },
  { label: '智课讲授', value: 'knowledge' },
  { label: 'AI实时问答', value: 'ai' }
]

const lessonId = computed(() => route.params.lessonId)
const allChapters = computed(() => (lesson.value.units || []).flatMap((unit) => unit.chapters || []))
const activeChapter = computed(() => allChapters.value.find((chapter) => chapter.chapterId === activeChapterId.value) || allChapters.value[0] || {})
const aggregatedUnitChapters = computed(() => buildAggregatedKnowledgeUnits(lesson.value.units || []))
const allAggregatedChapters = computed(() => aggregatedUnitChapters.value.flatMap((unit) => unit.chapters || []))
const currentLearningAggregatedChapter = computed(() => {
  const locatedByProgress = findAggregatedChapterForSection(lesson.value.units || [], progressState.value.sectionId || '')
  if (locatedByProgress) return locatedByProgress
  const locatedByActiveSection = findAggregatedChapterForSection(lesson.value.units || [], activeChapter.value.sectionId || '')
  if (locatedByActiveSection) return locatedByActiveSection
  return allAggregatedChapters.value[0] || {}
})
const activeKnowledgeChapter = computed(() => {
  return allAggregatedChapters.value.find((chapter) => chapter.chapterId === activeKnowledgeChapterId.value)
    || currentLearningAggregatedChapter.value
    || allAggregatedChapters.value[0]
    || {}
})
const firstRealtimeChapter = computed(() => allChapters.value.find((chapter) => chapter.sectionId) || {})
const aiContextChapter = computed(() => {
  if (activeChapter.value?.sectionId) return activeChapter.value
  if (progressState.value?.sectionId) {
    return allChapters.value.find((chapter) => String(chapter.sectionId || '') === String(progressState.value.sectionId || ''))
      || firstRealtimeChapter.value
      || activeChapter.value
  }
  return firstRealtimeChapter.value || activeChapter.value
})
const { isRecording, voiceLoading, recordingSeconds, toggleRecording, cleanupRealtimeAsr } = useRealtimeAsr({
  getContext: () => ({
    studentId: studentProfile.value.studentId,
    lessonId: lessonId.value,
    sectionId: aiContextChapter.value.sectionId || progressState.value.sectionId || ''
  }),
  onTranscript: (text) => {
    questionText.value = `${voiceDraftPrefix.value}${text}`.trim()
  },
  onRecordingStart: () => {
    const prefix = questionText.value.trim()
    voiceDraftPrefix.value = prefix ? `${prefix}\n` : ''
  }
})

function formatRecordingDuration(totalSeconds) {
  const safeSeconds = Number(totalSeconds || 0)
  const minutes = Math.floor(safeSeconds / 60)
  const seconds = safeSeconds % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}
const overallProgress = computed(() => {
  if (!allChapters.value.length) return 0
  return Math.round(allChapters.value.reduce((sum, chapter) => sum + Number(chapter.progressPercent || 0), 0) / allChapters.value.length)
})
const overallMastery = computed(() => {
  if (!allChapters.value.length) return 0
  return Math.round(allChapters.value.reduce((sum, chapter) => sum + Number(chapter.masteryPercent || 0), 0) / allChapters.value.length)
})
const showCourseOverview = computed(() => activeView.value === 'progress' || activeView.value === 'knowledge')
const chapterCount = computed(() => allChapters.value.length)
const filteredAiTools = computed(() => {
  const fallbackTools = [
    { id: 'tool-1', name: 'AI陪练' },
    { id: 'tool-4', name: 'AI文档问答' }
  ]
  const sourceTools = (lesson.value.aiTools || []).filter((tool) => ['AI陪练', 'AI文档问答'].includes(tool.name))
  return (sourceTools.length ? sourceTools : fallbackTools).map((tool) => ({
    id: tool.id,
    name: tool.name
  }))
})
const aiSuggestedQuestions = computed(() => {
  const chapterTitle = aiContextChapter.value.chapterTitle || lesson.value.currentKnowledgePointName || '当前章节'
  return [
    `帮我概括《${chapterTitle}》的重点`,
    `《${chapterTitle}》里的核心公式之间有什么关系`,
    `《${chapterTitle}》在工程里通常怎么应用`
  ]
})
const latestAssistantMessage = computed(() => [...chatList.value].reverse().find((item) => item.role === 'assistant') || null)
const latestResumePoint = computed(() => ({
  anchorTitle: latestAssistantMessage.value?.anchorTitle || progressState.value.anchorTitle || activeChapter.value.chapterTitle || '',
  pageNo: latestAssistantMessage.value?.resumePageNo || progressState.value.pageNo || activeChapter.value.pageNo || 1
}))
const recommendedResumeChapter = computed(() => {
  const targetPageNo = Number(latestResumePoint.value.pageNo || 0)
  return allChapters.value.find((chapter) => chapter.pageNo === targetPageNo)
    || allChapters.value.find((chapter) => chapter.chapterTitle === latestResumePoint.value.anchorTitle)
    || activeChapter.value
    || allChapters.value[0]
    || {}
})
const qaHistoryCount = computed(() => qaSessions.value.reduce((count, session) => (
  count + (session.messages || []).filter((item) => item.role === 'assistant').length
), 0))
const navIndicatorStyle = computed(() => ({
  width: `${navIndicator.value.width}px`,
  transform: `translateX(${navIndicator.value.left}px)`,
  opacity: String(navIndicator.value.opacity)
}))

function buildCachedConversation(history) {
  return history.flatMap((item, index) => ([
    { id: `history-q-${index}`, role: 'user', content: item.question },
    {
      id: item.id || `history-a-${index}`,
      role: 'assistant',
      content: item.answer,
      anchorTitle: item.anchorTitle,
      resumePageNo: item.resumePageNo,
      understandingLabel: item.understandingLabel,
      relatedPoints: item.relatedPoints || []
    }
  ]))
}

function createSessionTitle(question = '') {
  const normalized = `${question || ''}`.replace(/\s+/g, ' ').trim()
  if (!normalized) return '未命名问答'
  return normalized.length > 24 ? `${normalized.slice(0, 24)}...` : normalized
}

function cloneMessages(messages = []) {
  return messages.map((item) => ({ ...item }))
}

function normalizeSession(rawSession, index = 0) {
  const messages = cloneMessages(rawSession?.messages || [])
  const firstQuestion = messages.find((item) => item.role === 'user')?.content || ''
  return {
    sessionId: rawSession?.sessionId || `session-${Date.now()}-${index}`,
    title: rawSession?.title || createSessionTitle(firstQuestion),
    messages,
    createdAt: rawSession?.createdAt || Date.now(),
    updatedAt: rawSession?.updatedAt || Date.now()
  }
}

function buildLegacySession(history) {
  const messages = buildCachedConversation(history)
  return normalizeSession({
    sessionId: `legacy-${lessonId.value}`,
    title: createSessionTitle(history[0]?.question || ''),
    messages,
    createdAt: Date.now(),
    updatedAt: Date.now()
  })
}

function buildHistoryPairsFromMessages(messages) {
  const historyPairs = []
  for (let index = 0; index < messages.length; index += 2) {
    const questionItem = messages[index]
    const answerItem = messages[index + 1]
    if (!questionItem || !answerItem) continue
    historyPairs.push({
      id: answerItem.id,
      question: questionItem.content,
      answer: answerItem.content,
      anchorTitle: answerItem.anchorTitle,
      resumePageNo: answerItem.resumePageNo,
      understandingLabel: answerItem.understandingLabel,
      relatedPoints: answerItem.relatedPoints || []
    })
  }
  return historyPairs
}

function getSessionDisplayTitle(session) {
  return session?.title || '未命名问答'
}

async function persistQaSessions(targetSessionId = activeSessionId.value) {
  const normalized = qaSessions.value
    .map((session, index) => normalizeSession(session, index))
    .sort((left, right) => Number(right.updatedAt || 0) - Number(left.updatedAt || 0))
  qaSessions.value = normalized
  saveStudentQaSessions(lessonId.value, normalized)
  const currentSession = normalized.find((session) => session.sessionId === targetSessionId)
  saveStudentQaHistory(lessonId.value, buildHistoryPairsFromMessages(currentSession?.messages || []))
  if (!currentSession) return
  try {
    await persistStudentQaSession({
      studentId: studentProfile.value.studentId,
      lessonId: lessonId.value,
      sectionId: aiContextChapter.value.sectionId || progressState.value.sectionId || '',
      session: currentSession
    })
  } catch {
    // use local cache as non-blocking fallback
  }
}

async function syncActiveSessionFromChatList() {
  if (!chatList.value.length) return
  const now = Date.now()
  const firstQuestion = chatList.value.find((item) => item.role === 'user')?.content || ''
  const nextSessionId = activeSessionId.value || `session-${now}`
  const existingIndex = qaSessions.value.findIndex((session) => session.sessionId === nextSessionId)
  const nextSession = normalizeSession({
    sessionId: nextSessionId,
    title: qaSessions.value[existingIndex]?.title || createSessionTitle(firstQuestion),
    messages: chatList.value,
    createdAt: qaSessions.value[existingIndex]?.createdAt || now,
    updatedAt: now
  }, existingIndex)
  if (existingIndex >= 0) {
    qaSessions.value.splice(existingIndex, 1, nextSession)
  } else {
    qaSessions.value.unshift(nextSession)
  }
  activeSessionId.value = nextSession.sessionId
  await persistQaSessions(nextSession.sessionId)
}

function loadSessionIntoChat(session) {
  activeSessionId.value = session?.sessionId || ''
  chatList.value = cloneMessages(session?.messages || [])
}

async function openQaSession(sessionId) {
  if (sessionId === activeSessionId.value) return
  await syncActiveSessionFromChatList()
  const target = qaSessions.value.find((session) => session.sessionId === sessionId)
  if (!target) return
  cancelSessionTitleEdit()
  loadSessionIntoChat(target)
}

function startSessionTitleEdit(session) {
  editingSessionId.value = session.sessionId
  editingSessionTitle.value = session.title || ''
}

function cancelSessionTitleEdit() {
  editingSessionId.value = ''
  editingSessionTitle.value = ''
}

async function commitSessionTitleEdit(sessionId) {
  const target = qaSessions.value.find((session) => session.sessionId === sessionId)
  if (!target) {
    cancelSessionTitleEdit()
    return
  }
  target.title = createSessionTitle(editingSessionTitle.value || target.title)
  target.updatedAt = Date.now()
  await persistQaSessions(sessionId)
  cancelSessionTitleEdit()
}

function buildFallbackPlayer(lessonSummary) {
  const fallbackLesson = lessonSummary || findFrontendTestLesson(lessonId.value) || getFrontendTestLessons()[0]
  const chapters = (fallbackLesson.units || []).flatMap((unit) => unit.chapters || [])
  return {
    ...fallbackLesson,
    coverImage: fallbackLesson.coverImage || '',
    slides: chapters.map((chapter) => ({
      pageNo: chapter.pageNo,
      title: chapter.chapterTitle,
      summary: chapter.summary,
      knowledgePoints: chapter.knowledgePoints || []
    })),
    anchors: chapters.map((chapter, index) => ({
      anchorId: `${fallbackLesson.lessonId}-A${index + 1}`,
      anchorTitle: chapter.chapterTitle,
      pageNo: chapter.pageNo,
      startTime: index * 90
    })),
    currentPage: fallbackLesson.currentPage || chapters[0]?.pageNo || 1,
    currentKnowledgePointName: fallbackLesson.currentKnowledgePointName || chapters[0]?.chapterTitle || '待学习章节',
    aiWelcome: `Hi，${studentProfile.value.studentName || fallbackProfile.studentName}同学，围绕《${fallbackLesson.courseName}》开始提问吧。`,
    aiPrompt: '可以输入文字问题，也可以直接使用语音输入。',
    aiTools: [
      { id: 'tool-1', name: 'AI陪练' },
      { id: 'tool-4', name: 'AI文档问答' }
    ]
  }
}

function getDefaultProgressState(targetLesson) {
  const firstChapter = (targetLesson.units || []).flatMap((unit) => unit.chapters || [])[0]
  return {
    anchorId: `${targetLesson.lessonId}-A1`,
    anchorTitle: firstChapter?.chapterTitle || '待学习章节',
    pageNo: firstChapter?.pageNo || 1,
    currentTime: 0,
    progressPercent: 0,
    understandingLevel: 'partial',
    weakPoints: []
  }
}

function syncLessonCache() {
  const cache = getStudentLessonListCache()
  const updated = cache.map((item) => {
    if (item.lessonId !== lesson.value.lessonId) return item
    return {
      ...item,
      units: lesson.value.units,
      progressPercent: overallProgress.value,
      currentPage: activeChapter.value.pageNo || item.currentPage,
      currentKnowledgePointName: activeChapter.value.chapterTitle || item.currentKnowledgePointName,
      currentChapter: activeChapter.value.chapterTitle || item.currentChapter,
      questionCount: qaHistoryCount.value
    }
  })
  saveStudentLessonList(updated)
}

function capturePlayerViewState() {
  saveStudentViewState(lessonId.value, {
    player: {
      activeView: activeView.value,
      activeChapterId: activeChapterId.value,
      activeKnowledgeChapterId: activeKnowledgeChapterId.value,
      scrollTop: pageMainRef.value?.scrollTop || 0
    }
  })
}

function handlePlayerScroll() {
  capturePlayerViewState()
}

async function restorePlayerViewState() {
  const viewState = getStudentViewState(lessonId.value)?.player || {}
  if (viewState.activeView && primaryNavItems.some((item) => item.value === viewState.activeView)) {
    activeView.value = viewState.activeView
  }
  if (viewState.activeChapterId) {
    activeChapterId.value = viewState.activeChapterId
  }
  if (viewState.activeKnowledgeChapterId) {
    activeKnowledgeChapterId.value = viewState.activeKnowledgeChapterId
  }
  await nextTick()
  if (pageMainRef.value && Number.isFinite(Number(viewState.scrollTop))) {
    pageMainRef.value.scrollTop = Number(viewState.scrollTop || 0)
  }
}

function setActiveChapter(chapter) {
  activeChapterId.value = chapter.chapterId
}

function setActiveKnowledgeChapter(chapter) {
  activeKnowledgeChapterId.value = chapter?.chapterId || ''
}

function goToKnowledgeLearning(chapter) {
  if (!chapter?.chapterId) return
  activeKnowledgeChapterId.value = chapter.chapterId
  capturePlayerViewState()
  router.push({
    name: 'StudentKnowledgeLearning',
    params: {
      lessonId: lessonId.value,
      unitId: chapter.unitId || '',
      chapterId: chapter.chapterId
    },
    query: route.query.token ? { token: route.query.token } : {}
  })
}

function setPrimaryNavButton(element, value) {
  if (!element) {
    delete primaryNavRefs.value[value]
    return
  }
  primaryNavRefs.value[value] = element
}

function updateNavIndicator() {
  const target = primaryNavRefs.value[activeView.value]
  if (!target) return
  navIndicator.value = {
    width: target.offsetWidth,
    left: target.offsetLeft,
    opacity: 1
  }
}

function switchView(value) {
  activeView.value = value
  userMenuOpen.value = false
  nextTick(() => {
    if (pageMainRef.value) {
      pageMainRef.value.scrollTo({ top: 0, left: 0, behavior: 'auto' })
    }
    capturePlayerViewState()
  })
}

function goStudentHome() {
  userMenuOpen.value = false
  capturePlayerViewState()
  router.push({
    name: 'StudentHome',
    query: route.query.token ? { token: route.query.token } : {}
  })
}

function toggleUserMenu() {
  userMenuOpen.value = !userMenuOpen.value
}

function handleUserMenuAction(action) {
  userMenuOpen.value = false
  if (action === 'home') {
    goStudentHome()
    return
  }
  ElMessage.info('消息中心开发中')
}

function handleDocumentPointerDown(event) {
  if (!userMenuOpen.value) return
  const target = event.target
  if (topbarUserRef.value && target instanceof Node && !topbarUserRef.value.contains(target)) {
    userMenuOpen.value = false
  }
}

function getChapterStatusLabel(chapter) {
  if (chapter.chapterId === activeChapter.value.chapterId) return '当前学习'
  if (Number(chapter.progressPercent || 0) >= 100) return '已完成'
  if (Number(chapter.progressPercent || 0) > 0) return '进行中'
  return '待学习'
}

function getChapterStatusClass(chapter) {
  if (chapter.chapterId === activeChapter.value.chapterId) return 'is-active'
  if (Number(chapter.progressPercent || 0) >= 100) return 'is-done'
  if (Number(chapter.progressPercent || 0) > 0) return 'is-progress'
  return 'is-pending'
}

function getAggregatedChapterStatusLabel(chapter) {
  if (chapter.chapterId === currentLearningAggregatedChapter.value.chapterId) return '当前学习'
  if (Number(chapter.progressPercent || 0) >= 100) return '已完成'
  if (Number(chapter.progressPercent || 0) > 0) return '进行中'
  return '待学习'
}

function getAggregatedChapterStatusClass(chapter) {
  if (chapter.chapterId === currentLearningAggregatedChapter.value.chapterId) return 'is-active'
  if (Number(chapter.progressPercent || 0) >= 100) return 'is-done'
  if (Number(chapter.progressPercent || 0) > 0) return 'is-progress'
  return 'is-pending'
}

function applyChapterPosition(chapter) {
  if (!chapter?.chapterId) return
  activeChapterId.value = chapter.chapterId
  const locatedAggregatedChapter = findAggregatedChapterForSection(lesson.value.units || [], chapter.sectionId || '')
  if (locatedAggregatedChapter?.chapterId) {
    activeKnowledgeChapterId.value = locatedAggregatedChapter.chapterId
  }
  lesson.value.currentPage = chapter.pageNo
  lesson.value.currentKnowledgePointName = chapter.chapterTitle
  progressState.value = {
    ...progressState.value,
    pageNo: chapter.pageNo,
    anchorTitle: chapter.chapterTitle
  }
}

function goToSlideLearning(chapter, pageNoOverride) {
  if (!chapter?.sectionId) return
  const aggregatedChapter = findAggregatedChapterForSection(lesson.value.units || [], chapter.sectionId || '')
  capturePlayerViewState()
  return router.push({
    name: 'StudentSlideLearning',
    params: {
      lessonId: lessonId.value,
      sectionId: chapter.sectionId
    },
    query: {
      ...(route.query.token ? { token: route.query.token } : {}),
      ...(chapter.chapterId ? { chapterId: chapter.chapterId } : {}),
      ...(aggregatedChapter?.unitId ? { unitId: aggregatedChapter.unitId } : {}),
      ...(aggregatedChapter?.chapterId ? { knowledgeChapterId: aggregatedChapter.chapterId } : {}),
      pageNo: String(pageNoOverride || chapter.pageNo || 1)
    }
  })
}

function goToRecommendedChapter() {
  const targetChapter = recommendedResumeChapter.value
  if (!targetChapter?.chapterId) return
  applyChapterPosition(targetChapter)
  goToSlideLearning(targetChapter, latestResumePoint.value.pageNo || targetChapter.pageNo)
}

function goToChapterById(chapterId) {
  const chapter = allChapters.value.find((item) => item.chapterId === chapterId)
  if (!chapter) return
  applyChapterPosition(chapter)
  goToSlideLearning(chapter)
}

async function resumeLearning() {
  resumeLoading.value = true
  try {
    const res = await resumeStudentLesson({
      studentId: studentProfile.value.studentId,
      lessonId: lessonId.value,
      anchorId: progressState.value.anchorId,
      anchorTitle: progressState.value.anchorTitle,
      pageNo: progressState.value.pageNo
    })
    const payload = res.data || {}
    const targetChapter = allChapters.value.find((chapter) => chapter.pageNo === Number(payload.pageNo))
      || allChapters.value.find((chapter) => chapter.chapterTitle === payload.anchorTitle)
      || recommendedResumeChapter.value
    applyChapterPosition(targetChapter)
    progressState.value = {
      ...progressState.value,
      ...payload,
      pageNo: payload.pageNo || targetChapter?.pageNo || progressState.value.pageNo,
      anchorTitle: payload.anchorTitle || targetChapter?.chapterTitle || progressState.value.anchorTitle
    }
    if (targetChapter?.chapterId) {
      await goToSlideLearning(targetChapter, payload.pageNo || targetChapter.pageNo || progressState.value.pageNo || 1)
    }
  } catch {
    const fallbackChapter = recommendedResumeChapter.value
    applyChapterPosition(fallbackChapter)
    if (fallbackChapter?.chapterId) {
      await goToSlideLearning(fallbackChapter, latestResumePoint.value.pageNo || fallbackChapter.pageNo || 1)
    }
  } finally {
    resumeLoading.value = false
  }
}

async function adjustLearningRhythm(mode) {
  adjustLoading.value = mode
  try {
    const res = await adjustStudentProgress({
      studentId: studentProfile.value.studentId,
      lessonId: lessonId.value,
      anchorId: progressState.value.anchorId,
      anchorTitle: latestResumePoint.value.anchorTitle,
      pageNo: latestResumePoint.value.pageNo,
      action: mode
    })
    rhythmSuggestion.value = res.data?.advice
      || (mode === 'fast'
        ? '建议优先推进核心章节，再通过实时问答快速补齐薄弱点。'
        : '建议先巩固当前章节摘要与关键词，再进入下一章节。')
    progressFallbackNote.value = '当前节奏建议已同步到服务端。'
    ElMessage.success('已更新学习节奏')
  } catch {
    rhythmSuggestion.value = mode === 'fast'
      ? '建议优先完成当前单元核心章节，再通过问答补齐理解盲点。'
      : '建议先回看当前章节摘要和关键词，再继续推进下一节。'
    progressFallbackNote.value = '当前使用本地节奏建议，服务端接口暂未返回结果。'
    ElMessage.info('当前使用本地节奏建议')
  } finally {
    adjustLoading.value = ''
  }
}

async function bootstrapStudent() {
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

    const lessonRes = await getStudentLessonList({
      studentId: studentProfile.value.studentId,
      token: getPlatformToken()
    })
    const lessons = lessonRes.data?.lessons || []
    saveStudentLessonList(lessons.length ? lessons : getFrontendTestLessons())
  } catch (error) {
    studentProfile.value = {
      ...fallbackProfile,
      ...studentProfile.value
    }
  }
}

async function loadLesson() {
  const cachedLesson = getStudentLessonListCache().find((item) => item.lessonId === lessonId.value) || findFrontendTestLesson(lessonId.value)
  if (cachedLesson) {
    lesson.value = buildFallbackPlayer(cachedLesson)
    if (!progressState.value.anchorId) {
      progressState.value = getDefaultProgressState(lesson.value)
    }
    const cachedTargetChapter = allChapters.value.find((chapter) => String(chapter.sectionId || '') === String(progressState.value.sectionId || ''))
      || allChapters.value.find((chapter) => chapter.pageNo === progressState.value.pageNo)
      || allChapters.value[0]
    activeChapterId.value = cachedTargetChapter?.chapterId || ''
  }

  await bootstrapStudent()

  try {
    const progressRes = await getStudentProgress({
      studentId: studentProfile.value.studentId,
      lessonId: lessonId.value
    })
    progressState.value = progressRes.data || {}
  } catch {
    progressState.value = getDefaultProgressState(cachedLesson || buildFallbackPlayer())
  }

  try {
    const playRes = await playStudentLesson({
      studentId: studentProfile.value.studentId,
      lessonId: lessonId.value,
      anchorId: progressState.value.anchorId
    })
    lesson.value = playRes.data || buildFallbackPlayer(cachedLesson)
  } catch {
    lesson.value = buildFallbackPlayer(cachedLesson)
  }

  if (!progressState.value.anchorId) {
    progressState.value = getDefaultProgressState(lesson.value)
  }

  const targetChapter = allChapters.value.find((chapter) => String(chapter.sectionId || '') === String(progressState.value.sectionId || ''))
    || allChapters.value.find((chapter) => chapter.sectionId)
    || allChapters.value.find((chapter) => chapter.pageNo === progressState.value.pageNo)
    || allChapters.value[0]
  activeChapterId.value = targetChapter?.chapterId || ''
  activeKnowledgeChapterId.value = findAggregatedChapterForSection(lesson.value.units || [], targetChapter?.sectionId || '')?.chapterId
    || activeKnowledgeChapterId.value
    || allAggregatedChapters.value[0]?.chapterId
    || ''

  try {
    const sessionRes = await fetchStudentQaSessions({
      studentId: studentProfile.value.studentId,
      lessonId: lessonId.value
    })
    const remoteSessions = sessionRes.data?.sessions || []
    if (remoteSessions.length) {
      qaSessions.value = remoteSessions.map((session, index) => normalizeSession(session, index))
      saveStudentQaSessions(lessonId.value, qaSessions.value)
    } else {
      const cachedSessions = getStudentQaSessions(lessonId.value)
      if (cachedSessions.length) {
        qaSessions.value = cachedSessions.map((session, index) => normalizeSession(session, index))
      } else {
        const cachedHistory = getStudentQaHistory(lessonId.value)
        qaSessions.value = cachedHistory.length ? [buildLegacySession(cachedHistory)] : []
        if (qaSessions.value.length) {
          await persistQaSessions(qaSessions.value[0]?.sessionId)
        }
      }
    }
  } catch {
    const cachedSessions = getStudentQaSessions(lessonId.value)
    if (cachedSessions.length) {
      qaSessions.value = cachedSessions.map((session, index) => normalizeSession(session, index))
    } else {
      const cachedHistory = getStudentQaHistory(lessonId.value)
      qaSessions.value = cachedHistory.length ? [buildLegacySession(cachedHistory)] : []
    }
  }
  activeSessionId.value = ''
  chatList.value = []
  hasLoadedLesson.value = true
  await restorePlayerViewState()

  await nextTick()
}

async function askQuestion(question, source = 'text') {
  asking.value = true
  try {
    const currentSectionId = aiContextChapter.value.sectionId || progressState.value.sectionId || ''
    if (!currentSectionId) {
      ElMessage.warning('当前章节尚未完成定位，请先进入具体章节后再提问')
      return
    }

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: question
    }
    const assistantMessage = {
      id: `ai-${Date.now()}`,
      role: 'assistant',
      content: ''
    }
    let assistantInserted = false
    chatList.value.push(userMessage)
    questionText.value = ''
    assistantStreamingStarted.value = false
    const controller = new AbortController()
    activeAnswerController.value = controller

    function ensureAssistantVisible() {
      if (assistantInserted) return
      assistantInserted = true
      chatList.value.push(assistantMessage)
    }

    const donePayload = await streamLessonInteraction({
      studentId: studentProfile.value.studentId,
      lessonId: lessonId.value,
      sectionId: currentSectionId,
      source,
      question,
      anchorId: progressState.value.anchorId,
      anchorTitle: aiContextChapter.value.chapterTitle,
      pageNo: aiContextChapter.value.pageNo || progressState.value.pageNo,
      context: {
        slideTitle: aiContextChapter.value.chapterTitle,
        slideSummary: aiContextChapter.value.summary,
        knowledgePoints: aiContextChapter.value.knowledgePoints || []
      }
    }, {
      signal: controller.signal,
      onDelta: (delta) => {
        assistantStreamingStarted.value = true
        ensureAssistantVisible()
        assistantMessage.content += delta
      }
    })

    assistantStreamingStarted.value = true
    ensureAssistantVisible()
    assistantMessage.content = donePayload?.answer || assistantMessage.content || '当前内容暂无更多解读。'
    assistantMessage.relatedPoints = donePayload?.relatedKnowledgePoints || []
    assistantMessage.understandingLevel = donePayload?.understandingLevel
    assistantMessage.understandingLabel = donePayload?.understandingLabel
    assistantMessage.anchorTitle = donePayload?.resumeAnchor?.anchorTitle
    assistantMessage.resumePageNo = donePayload?.resumeAnchor?.pageNo

    await syncActiveSessionFromChatList()
    syncLessonCache()
  } catch (error) {
    if (error?.name === 'AbortError') {
      assistantStreamingStarted.value = true
      const lastAssistant = [...chatList.value].reverse().find((item) => item.role === 'assistant')
      if (lastAssistant && !lastAssistant.content) {
        lastAssistant.content = '已终止本次回答。'
      }
      await syncActiveSessionFromChatList()
    } else {
      chatList.value = chatList.value.filter((item) => !(item.role === 'assistant' && !item.content))
      ElMessage.error(error?.message || error?.msg || 'AI 问答失败')
    }
  } finally {
    asking.value = false
    assistantStreamingStarted.value = false
    activeAnswerController.value = null
  }
}

async function submitTextQuestion() {
  if (!questionText.value.trim()) {
    ElMessage.warning('请输入问题内容')
    return
  }
  await askQuestion(questionText.value.trim(), 'text')
}

async function submitSuggestedQuestion(question) {
  if (!question) return
  await askQuestion(question, 'text')
}

function toggleAiTools() {
  aiToolsVisible.value = !aiToolsVisible.value
}

function stopStreamingAnswer() {
  activeAnswerController.value?.abort()
}

async function startNewConversation() {
  activeAnswerController.value?.abort()
  if (chatList.value.length) {
    await syncActiveSessionFromChatList()
  }
  activeSessionId.value = ''
  chatList.value = []
  questionText.value = ''
  editingSessionId.value = ''
  editingSessionTitle.value = ''
}

onMounted(async () => {
  document.addEventListener('pointerdown', handleDocumentPointerDown)
  try {
    await loadLesson()
    await nextTick()
    updateNavIndicator()
    window.addEventListener('resize', updateNavIndicator)
    pageMainRef.value?.addEventListener('scroll', handlePlayerScroll, { passive: true })
    hasActivatedOnce.value = true
  } catch (error) {
    if (error?.handled) return
    ElMessage.error(error?.msg || '课程详情加载失败')
  }
})

onActivated(async () => {
  if (!hasActivatedOnce.value) return
  if (!hasLoadedLesson.value) {
    await loadLesson()
  } else {
    await restorePlayerViewState()
  }
  await nextTick()
  updateNavIndicator()
  pageMainRef.value?.addEventListener('scroll', handlePlayerScroll, { passive: true })
})

watch(activeView, async () => {
  await nextTick()
  updateNavIndicator()
})

watch([activeView, activeChapterId, activeKnowledgeChapterId], () => {
  capturePlayerViewState()
})

watch(
  [allAggregatedChapters, currentLearningAggregatedChapter],
  ([chapters, currentChapter]) => {
    if (!Array.isArray(chapters) || !chapters.length) {
      activeKnowledgeChapterId.value = ''
      return
    }
    const hasActive = chapters.some((chapter) => chapter.chapterId === activeKnowledgeChapterId.value)
    if (hasActive) return
    activeKnowledgeChapterId.value = currentChapter?.chapterId || chapters[0]?.chapterId || ''
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleDocumentPointerDown)
  activeAnswerController.value?.abort()
  cleanupRealtimeAsr()
  window.removeEventListener('resize', updateNavIndicator)
  pageMainRef.value?.removeEventListener('scroll', handlePlayerScroll)
  capturePlayerViewState()
})

onDeactivated(() => {
  pageMainRef.value?.removeEventListener('scroll', handlePlayerScroll)
  capturePlayerViewState()
})
</script>

<style scoped>
.student-player-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #eff3fb 0%, #f7f8fc 100%);
}

.student-player-topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 30;
  height: 84px;
  padding: 0 28px;
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr) 220px;
  align-items: center;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1px solid #edf1f7;
  backdrop-filter: blur(14px);
}

.student-topbar-brand,
.student-topbar-user {
  display: flex;
  align-items: center;
  gap: 12px;
}

.student-topbar-brand {
  cursor: pointer;
}

.student-topbar-brand:focus-visible {
  outline: 2px solid rgba(82, 126, 246, 0.45);
  outline-offset: 6px;
  border-radius: 16px;
}

.student-topbar-brand-mark {
  width: 40px;
  height: 40px;
  display: block;
  object-fit: contain;
  flex: 0 0 auto;
  border-radius: 10px;
}

.student-topbar-brand-name {
  font-size: 26px;
  font-weight: 700;
  color: #222833;
}

.student-topbar-center {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
}

.student-topbar-nav {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px;
  border-radius: 999px;
  background: linear-gradient(180deg, #f7faff, #edf3ff);
  border: 1px solid #d9e4f6;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.85);
  min-width: 0;
}

.student-topbar-nav-indicator {
  position: absolute;
  top: 6px;
  left: 0;
  bottom: 6px;
  border-radius: 999px;
  background: linear-gradient(135deg, #7da0ee, #5b83de);
  box-shadow: 0 10px 22px rgba(91, 131, 222, 0.22);
  transition: transform 0.24s ease, width 0.24s ease, opacity 0.18s ease;
  pointer-events: none;
}

.student-topbar-nav-item {
  border: 0;
  background: transparent;
  color: #4f5b75;
  font-size: 15px;
  min-height: 42px;
  padding: 0 20px;
  border-radius: 999px;
  cursor: pointer;
  position: relative;
  white-space: nowrap;
  z-index: 1;
  transition: color 0.2s ease, transform 0.2s ease;
}

.student-topbar-nav-item.active {
  color: #fff;
  font-weight: 600;
}

.student-topbar-user {
  position: relative;
  justify-self: end;
  color: #33415f;
  font-size: 14px;
  font-weight: 500;
}

.student-topbar-user-trigger {
  border: 0;
  background: transparent;
  padding: 0;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  color: inherit;
  font: inherit;
  cursor: pointer;
}

.student-topbar-user-arrow {
  transition: transform 0.2s ease;
}

.student-topbar-user.open .student-topbar-user-arrow {
  transform: rotate(180deg);
}

.student-topbar-user-menu {
  position: absolute;
  top: calc(100% + 12px);
  right: 0;
  min-width: 156px;
  padding: 8px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(216, 227, 246, 0.96);
  box-shadow: 0 18px 36px rgba(88, 115, 165, 0.16);
  backdrop-filter: blur(12px);
  display: grid;
  gap: 6px;
  z-index: 40;
}

.student-topbar-user-menu-item {
  min-height: 42px;
  padding: 0 14px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: #23375f;
  font-size: 14px;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
  transition: background 0.18s ease, color 0.18s ease, transform 0.18s ease;
}

.student-topbar-user-menu-item:hover {
  background: #eef4ff;
  color: #2f63c7;
  transform: translateY(-1px);
}

.student-secondary-action,
.student-ghost-action {
  min-height: 42px;
  padding: 0 18px;
  border-radius: 14px;
  cursor: pointer;
  font-size: 14px;
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease, border-color 0.18s ease;
}

.student-secondary-action {
  border: 0;
  background: linear-gradient(135deg, #6d94f1, #4d78de);
  color: #fff;
  box-shadow: 0 12px 22px rgba(94, 130, 208, 0.18);
}

.student-secondary-action:hover {
  transform: translateY(-1px);
}

.student-ghost-action {
  border: 1px solid #d7e2f3;
  background: #fff;
  color: #2b4f8c;
}

.student-ghost-action:hover {
  background: #f4f8ff;
  border-color: #c6d8f2;
}

.student-player-main {
  height: calc(100vh - 84px);
  box-sizing: border-box;
  padding: 24px 36px 36px;
  margin-top: 84px;
  overflow-y: auto;
  overflow-x: hidden;
}

.student-player-main::-webkit-scrollbar-button,
.student-player-main::-webkit-scrollbar-button:single-button,
.student-player-main::-webkit-scrollbar-button:vertical:decrement,
.student-player-main::-webkit-scrollbar-button:vertical:increment {
  display: none;
  width: 0;
  height: 0;
  background: transparent;
}

.student-player-main.is-progress-view {
  height: calc(100vh - 84px);
  overflow-y: auto;
  overflow-x: hidden;
  padding-top: 18px;
  padding-bottom: 28px;
}

.student-course-overview {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  align-items: stretch;
  gap: 16px;
  margin-bottom: 10px;
  min-height: 164px;
  padding: 18px 24px;
  border-radius: 32px;
  border: 1px solid rgba(205, 223, 247, 0.92);
  background:
    radial-gradient(circle at 16% 18%, rgba(255, 255, 255, 0.84), transparent 28%),
    radial-gradient(circle at 84% 18%, rgba(255, 255, 255, 0.34), transparent 24%),
    linear-gradient(135deg, #dbeafe 0%, #cfe3ff 42%, #eaf3ff 100%);
  box-shadow: 0 24px 50px rgba(111, 144, 199, 0.12);
  color: #17315d;
}

.student-course-overview-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.student-course-overview h1 {
  margin: 0;
  color: #17315d;
  font-size: 30px;
  line-height: 1.22;
}

.student-course-overview-teacher {
  margin: 10px 0 0;
  color: rgba(49, 79, 133, 0.9);
  font-size: 20px;
  font-weight: 600;
  line-height: 1.42;
}

.student-course-overview-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  align-self: center;
  justify-self: end;
  width: 100%;
  max-width: 420px;
}

.student-course-overview-metric {
  min-height: 108px;
  padding: 16px 15px 24px;
  border-radius: 24px;
  border: 1px solid rgba(156, 186, 233, 0.28);
  background: rgba(255, 255, 255, 0.62);
  backdrop-filter: blur(12px);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.student-course-overview-metric span {
  display: block;
  color: rgba(54, 85, 140, 0.72);
  font-size: 15px;
  text-align: left;
}

.student-course-overview-metric strong {
  display: block;
  margin-top: 8px;
  color: #16315e;
  font-size: 28px;
  line-height: 1.24;
  text-align: center;
}

.student-knowledge-page {
  display: grid;
  gap: 22px;
}

.student-progress-page {
  display: grid;
  gap: 0;
  min-height: 0;
}

.student-unit-section,
.student-progress-hero,
.student-progress-panel,
.student-ai-chat-card,
.student-ai-sidebar-card {
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(227, 236, 247, 0.96);
  box-shadow: 0 18px 44px rgba(93, 121, 172, 0.08);
  backdrop-filter: blur(12px);
}

.student-unit-badge {
  display: inline-flex;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(217, 232, 255, 0.96);
  color: #3c67b8;
  font-size: 12px;
  font-weight: 600;
}

.student-unit-badge {
  background: rgba(233, 240, 255, 0.98);
  color: #466ab0;
}

.student-unit-section {
  padding: 28px;
}

.student-unit-header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
}

.student-unit-header-main h2 {
  margin: 14px 0 0;
  color: #17315d;
  font-size: 24px;
}

.student-unit-header-meta {
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  background: #f4f8ff;
  border: 1px solid #dde7f7;
  color: #496da8;
  font-size: 13px;
  white-space: nowrap;
}

.student-chapter-grid {
  margin-top: 24px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.student-chapter-card {
  display: flex;
  flex-direction: column;
  min-height: 292px;
  padding: 22px;
  border-radius: 24px;
  background: linear-gradient(180deg, #fbfdff, #f4f8ff);
  border: 1px solid #e2eaf7;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease, background 0.2s ease;
}

.student-chapter-card:hover,
.student-chapter-card.active {
  transform: translateY(-2px);
  border-color: #c9d9f3;
  background: linear-gradient(180deg, #ffffff, #eef5ff);
  box-shadow: 0 18px 34px rgba(92, 123, 180, 0.1);
}

.student-chapter-card-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.student-chapter-card-head h3 {
  margin: 10px 0 0;
  color: #172f58;
  font-size: 20px;
  line-height: 1.5;
}

.student-chapter-status {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.student-chapter-status.is-active {
  background: #ddebff;
  color: #2f63c7;
}

.student-chapter-status.is-done {
  background: #e9f8ef;
  color: #2d8a54;
}

.student-chapter-status.is-progress {
  background: #eef4ff;
  color: #4e6faa;
}

.student-chapter-status.is-pending {
  background: #f4f7fc;
  color: #8090ae;
}

.student-chapter-mastery-badge {
  flex-shrink: 0;
  width: 100px;
  height: 100px;
  padding: 12px;
  border-radius: 20px;
  background: rgba(232, 240, 255, 0.9);
  border: 1px solid rgba(207, 220, 243, 0.98);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
}

.student-chapter-mastery-badge span {
  display: block;
  color: #7f90b1;
  font-size: 12px;
}

.student-chapter-mastery-badge strong {
  display: block;
  margin-top: 6px;
  color: #17305f;
  font-size: 20px;
}

.student-chapter-card-footer {
  display: grid;
  gap: 14px;
  margin-top: auto;
  padding-top: 18px;
}

.student-chapter-progress-block {
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.68);
  border: 1px solid rgba(228, 236, 247, 0.96);
}

.student-chapter-progress-text {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #6d7a98;
  font-size: 13px;
}

.student-chapter-progress-text strong {
  color: #18325f;
}
.student-chapter-footer-row {
  display: flex;
  justify-content: flex-end;
  gap: 14px;
  align-items: center;
}

.student-chapter-footer-row :deep(.el-button) {
  min-height: 42px;
  padding: 0 18px;
  border-radius: 14px;
  border: 0;
  background: linear-gradient(135deg, #6d94f1, #4d78de);
  box-shadow: 0 12px 22px rgba(94, 130, 208, 0.18);
}

.student-knowledge-action-button {
  position: relative;
  min-width: 118px;
  height: 42px;
  padding: 0;
  border: 0;
  border-radius: 14px;
  background:
    linear-gradient(140deg, rgba(90, 180, 255, 0.22), rgba(90, 180, 255, 0.1)),
    radial-gradient(circle at 18% 20%, rgba(255, 255, 255, 0.4), transparent 42%),
    linear-gradient(135deg, rgb(90, 180, 255), rgb(72, 158, 240) 56%, rgb(57, 136, 224) 100%);
  box-shadow:
    0 14px 26px rgba(73, 150, 221, 0.2),
    inset 0 0 0 1px rgba(190, 232, 255, 0.24),
    inset 0 1px 0 rgba(255, 255, 255, 0.24);
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.24s ease, box-shadow 0.24s ease, filter 0.24s ease;
}

.student-knowledge-action-button::before {
  content: '';
  position: absolute;
  inset: 1px;
  border-radius: 13px;
  background:
    linear-gradient(135deg, rgba(90, 180, 255, 0.98), rgba(72, 158, 240, 0.98) 62%, rgba(57, 136, 224, 0.98));
}

.student-knowledge-action-button::after {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(115deg, transparent 20%, rgba(218, 245, 255, 0.44) 34%, transparent 52%),
    linear-gradient(90deg, transparent, rgba(176, 231, 255, 0.24), transparent);
  transform: translateX(-120%);
  transition: transform 0.55s ease;
}

.student-knowledge-action-button:hover {
  transform: translateY(-2px);
  box-shadow:
    0 20px 30px rgba(73, 150, 221, 0.26),
    inset 0 0 0 1px rgba(201, 238, 255, 0.34),
    inset 0 1px 0 rgba(255, 255, 255, 0.26);
  filter: saturate(1.12);
}

.student-knowledge-action-button:hover::after {
  transform: translateX(120%);
}

.student-knowledge-action-button:active {
  transform: translateY(0) scale(0.988);
}

.student-knowledge-action-button-core {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
  padding: 0 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.student-knowledge-action-button-text {
  position: relative;
  z-index: 2;
  color: #f4fbff;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-shadow: 0 0 16px rgba(217, 244, 255, 0.32);
}

.student-knowledge-action-button-glow {
  position: absolute;
  inset: 8px 10px;
  border-radius: 10px;
  background:
    linear-gradient(90deg, rgba(190, 238, 255, 0.1), rgba(234, 248, 255, 0.32), rgba(190, 238, 255, 0.1));
  filter: blur(9px);
  opacity: 0.7;
  transition: opacity 0.22s ease, filter 0.22s ease;
}

.student-knowledge-action-button:hover .student-knowledge-action-button-glow {
  opacity: 1;
  filter: blur(11px);
}

.student-progress-hero,
.student-progress-panel {
  padding: 26px 28px;
}

.student-progress-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 14px;
  min-height: calc(100vh - 300px);
  padding: 16px 22px;
  background:
    radial-gradient(circle at 18% 18%, rgba(255, 255, 255, 0.86), transparent 28%),
    linear-gradient(135deg, #e7f0ff 0%, #d9e8ff 48%, #f2f7ff 100%);
}

.student-progress-hero-main {
  min-width: 0;
  display: grid;
  grid-template-rows: 136px auto;
  align-content: start;
  padding-right: 8px;
  min-height: 0;
}

.student-progress-hero-copy {
  display: grid;
  align-content: start;
  gap: 0;
  padding-top: 30px;
  height: 136px;
  overflow: hidden;
}

.student-progress-hero h2 {
  margin: 0;
  color: #17315d;
  font-size: 32px;
  line-height: 1.1;
  max-width: 720px;
  max-height: 100%;
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.student-progress-hero-actions,
.student-progress-resume-actions,
.student-progress-rhythm-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 0;
  padding-top: 2px;
  padding-left: 22px;
  align-self: flex-start;
}

.student-progress-stats {
  display: grid;
  grid-template-rows: auto auto;
  gap: 14px;
  align-self: start;
  justify-self: end;
  width: 100%;
  max-width: 420px;
}

.student-progress-stats-top {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.student-progress-stats-bottom {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 14px;
}

.student-progress-stat-card {
  min-height: 0;
  padding: 16px 18px 24px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.66);
  border: 1px solid rgba(208, 222, 245, 0.96);
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}

.student-progress-stat-card.chapter {
  min-height: 116px;
  justify-content: flex-start;
}

.student-progress-stats-top .student-progress-stat-card {
  min-height: 104px;
}

.student-progress-stat-card span {
  display: block;
  color: #7590bc;
  font-size: 15px;
  text-align: left;
}

.student-progress-stat-card strong {
  display: block;
  margin-top: auto;
  color: #17315d;
  font-size: 26px;
  line-height: 1.2;
  text-align: center;
}

.student-resume-button {
  position: relative;
  min-width: 254px;
  height: 86px;
  padding: 0;
  border: 0;
  border-radius: 28px;
  background:
    linear-gradient(140deg, rgba(90, 180, 255, 0.22), rgba(90, 180, 255, 0.1)),
    radial-gradient(circle at 18% 20%, rgba(255, 255, 255, 0.4), transparent 42%),
    linear-gradient(135deg, rgb(90, 180, 255), rgb(72, 158, 240) 56%, rgb(57, 136, 224) 100%);
  box-shadow:
    0 22px 38px rgba(73, 150, 221, 0.24),
    inset 0 0 0 1px rgba(190, 232, 255, 0.24),
    inset 0 1px 0 rgba(255, 255, 255, 0.24);
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.24s ease, box-shadow 0.24s ease, filter 0.24s ease;
}

.student-resume-button::before {
  content: '';
  position: absolute;
  inset: 1px;
  border-radius: 27px;
  background:
    linear-gradient(135deg, rgba(90, 180, 255, 0.98), rgba(72, 158, 240, 0.98) 62%, rgba(57, 136, 224, 0.98));
}

.student-resume-button::after {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(115deg, transparent 20%, rgba(218, 245, 255, 0.44) 34%, transparent 52%),
    linear-gradient(90deg, transparent, rgba(176, 231, 255, 0.24), transparent);
  transform: translateX(-120%);
  transition: transform 0.55s ease;
}

.student-resume-button:hover {
  transform: translateY(-3px);
  box-shadow:
    0 28px 46px rgba(73, 150, 221, 0.3),
    inset 0 0 0 1px rgba(201, 238, 255, 0.34),
    inset 0 1px 0 rgba(255, 255, 255, 0.26);
  filter: saturate(1.12);
}

.student-resume-button:hover::after {
  transform: translateX(120%);
}

.student-resume-button:active {
  transform: translateY(0) scale(0.988);
}

.student-resume-button-core {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
  padding: 0 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.student-resume-button-text {
  position: relative;
  z-index: 2;
  color: #f4fbff;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-shadow: 0 0 16px rgba(217, 244, 255, 0.32);
}

.student-resume-button-glow {
  position: absolute;
  inset: 16px 18px;
  border-radius: 16px;
  background:
    linear-gradient(90deg, rgba(190, 238, 255, 0.1), rgba(234, 248, 255, 0.32), rgba(190, 238, 255, 0.1));
  filter: blur(12px);
  opacity: 0.7;
  transition: opacity 0.22s ease, filter 0.22s ease;
}

.student-resume-button:hover .student-resume-button-glow {
  opacity: 1;
  filter: blur(15px);
}

.student-progress-panel-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.student-progress-panel-title {
  color: #17315d;
  font-size: 22px;
  font-weight: 700;
}

.student-progress-panel-subtitle {
  margin-top: 8px;
  color: #7284a6;
  font-size: 13px;
  line-height: 1.8;
}

.student-course-mastery-panel {
  margin-top: 18px;
}

.student-course-mastery-card {
  padding: 22px 24px 24px;
  border-radius: 24px;
  background: linear-gradient(180deg, #fbfdff, #f5f8ff);
  border: 1px solid #e2eaf7;
}

.student-course-mastery-list {
  display: grid;
  gap: 16px;
}

.student-course-mastery-item {
  display: grid;
  gap: 10px;
}

.student-course-mastery-item-title {
  color: #17315d;
  font-size: 16px;
  font-weight: 600;
  line-height: 1.5;
}

.student-course-mastery-item-shell {
  padding: 16px 18px 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(220, 231, 247, 0.96);
  display: grid;
  gap: 12px;
}

.student-course-mastery-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.student-course-mastery-item-label {
  color: #7284a6;
  font-size: 13px;
  line-height: 1.4;
}

.student-course-mastery-item-value {
  color: #17315d;
  font-size: 18px;
  line-height: 1;
}

.student-course-mastery-empty {
  color: #7284a6;
  font-size: 14px;
  line-height: 1.8;
}

.student-course-mastery-bar :deep(.el-progress-bar__outer) {
  background: #e8effa;
}

.student-course-mastery-bar :deep(.el-progress-bar__inner) {
  background: linear-gradient(135deg, rgb(70, 150, 255), rgb(70, 150, 255));
}

.student-progress-resume-card,
.student-progress-rhythm-card {
  padding: 20px 22px;
  border-radius: 24px;
  background: linear-gradient(180deg, #fbfdff, #f5f8ff);
  border: 1px solid #e2eaf7;
}

.student-progress-resume-label {
  color: #7c90b8;
  font-size: 12px;
}

.student-progress-resume-card strong {
  display: block;
  margin-top: 10px;
  color: #17315d;
  font-size: 22px;
  line-height: 1.4;
}

.student-progress-resume-card p,
.student-progress-rhythm-copy,
.student-progress-rhythm-note {
  margin: 10px 0 0;
  color: #6e809f;
  font-size: 14px;
  line-height: 1.8;
}

.student-progress-resume-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.student-progress-resume-meta span {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  background: #eef4ff;
  color: #48669d;
  font-size: 12px;
}

.student-progress-chapter-list {
  display: grid;
  gap: 14px;
}

.student-progress-chapter-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(140px, 220px) auto;
  gap: 16px;
  align-items: center;
  padding: 16px 18px;
  border-radius: 20px;
  background: linear-gradient(180deg, #fcfdff, #f6f9ff);
  border: 1px solid #e3ebf7;
}

.student-progress-chapter-item.active {
  border-color: #cddbf2;
  box-shadow: 0 14px 28px rgba(92, 123, 180, 0.08);
}

.student-progress-chapter-title {
  color: #17315d;
  font-size: 16px;
  font-weight: 600;
  line-height: 1.5;
}

.student-progress-chapter-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 6px;
  color: #7c8daa;
  font-size: 12px;
}

.student-progress-chapter-bar {
  height: 8px;
  border-radius: 999px;
  background: #e9f0fb;
  overflow: hidden;
}

.student-progress-chapter-bar-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(135deg, #8cb0f4, #5d83df);
}

.student-progress-chapter-side {
  display: grid;
  justify-items: end;
  gap: 8px;
}

.student-progress-chapter-side strong {
  color: #17315d;
  font-size: 16px;
}

.student-progress-inline-link {
  border: 0;
  background: transparent;
  color: #4a6fae;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}

.student-ai-page {
  --student-ai-card-height: 620px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  grid-template-areas: "chat sidebar";
  gap: 22px;
  align-items: stretch;
}

.student-ai-page.collapsed {
  grid-template-columns: minmax(0, 1fr) 28px;
  grid-template-areas: "chat sidebar";
}

.student-ai-chat-card {
  grid-area: chat;
  height: var(--student-ai-card-height);
  padding: 22px;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) 25%;
  background: rgba(255, 255, 255, 0.9);
}

.student-ai-chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.student-ai-chat-header.compact {
  padding-bottom: 6px;
}

.student-ai-chat-header-main {
  min-width: 0;
}

.student-ai-chat-title,
.student-ai-tools-title {
  color: #17315d;
  font-size: 24px;
  font-weight: 700;
}

.student-ai-new-chat-button {
  min-height: 40px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid #d8e3f5;
  background: linear-gradient(180deg, #ffffff, #f6f9ff);
  color: #33578f;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}

.student-ai-new-chat-button:hover {
  background: #f4f8ff;
  border-color: #c7d8f2;
  transform: translateY(-1px);
}

.student-ai-chat-body {
  min-height: 0;
  padding: 8px 2px 10px 0;
  overflow-y: auto;
}

.student-ai-chat-body.empty {
  display: grid;
  grid-template-rows: minmax(0, 1fr);
  overflow: hidden;
  padding-right: 0;
}

.student-ai-welcome {
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
  height: 100%;
}

.student-ai-welcome-suggestions {
  display: grid;
  gap: 10px;
  align-content: start;
}

.student-ai-welcome-spacer {
  min-height: 0;
}

.student-ai-suggestion-chip {
  width: fit-content;
  max-width: 100%;
  padding: 15px 22px;
  border-radius: 999px;
  border: 1px solid #d8e4f7;
  background: #ffffff;
  color: #466ab0;
  font-size: 14px;
  line-height: 1.5;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
}

.student-ai-suggestion-chip:hover {
  background: #f7fbff;
  border-color: #c8d8f2;
  transform: translateY(-1px);
}

.student-chat-list {
  display: grid;
  gap: 14px;
  align-content: start;
}

.student-chat-item {
  display: grid;
  gap: 6px;
}

.student-chat-role {
  color: #8792aa;
  font-size: 12px;
}

.student-chat-item.is-user .student-chat-role {
  justify-self: end;
  text-align: right;
}

.student-chat-bubble {
  max-width: 86%;
  padding: 14px 16px 12px;
  border-radius: 20px;
  background: linear-gradient(180deg, #ffffff, #f7faff);
  border: 0;
  color: #24345d;
  line-height: 1.65;
  box-shadow: 0 12px 28px rgba(101, 128, 176, 0.08);
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.student-chat-item.is-user {
  justify-items: end;
}

.student-chat-item.is-user .student-chat-bubble {
  background: linear-gradient(180deg, #edf4ff, #e6efff);
  box-shadow: 0 12px 28px rgba(111, 144, 199, 0.14);
}

.student-chat-content {
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.student-chat-points {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.student-chat-point-tag {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.76);
  border: 1px solid rgba(214, 225, 244, 0.96);
  color: #49689f;
  font-size: 12px;
}

.student-ai-input-area {
  min-height: 0;
  padding: 14px 18px;
  border: 0;
  border-radius: 24px;
  background:
    radial-gradient(circle at 14% 16%, rgba(255, 255, 255, 0.48), transparent 24%),
    linear-gradient(180deg, #eef4ff, #e6eefc);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.75),
    0 10px 24px rgba(128, 155, 205, 0.08);
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 12px;
}

.student-ai-input-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.student-ai-voice-status {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.student-ai-voice-timer {
  color: #7c8dac;
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}

.student-ai-icon-button {
  width: 44px;
  height: 44px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #d8e2f3;
  background: rgba(255, 255, 255, 0.96);
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.student-ai-icon-button svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.student-ai-icon-button.voice {
  color: #5f6a80;
  box-shadow: 0 8px 18px rgba(140, 158, 196, 0.14);
}

.student-ai-icon-button.voice.loading {
  background: rgba(255, 255, 255, 0.82);
}

.student-ai-icon-button.voice.stop {
  color: #11161c;
}

.student-ai-icon-button.send {
  border-color: #101418;
  background: #101418;
  color: #fff;
  box-shadow: 0 10px 24px rgba(16, 20, 24, 0.18);
}

.student-ai-icon-button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.student-ai-icon-button.voice:hover:not(:disabled) {
  background: #f6f9ff;
  border-color: #c6d6ef;
}

.student-ai-icon-button.send:hover:not(:disabled) {
  background: #1c232d;
  border-color: #1c232d;
}

.student-ai-icon-button.send.is-stop {
  border-color: #101418;
  background: #101418;
  box-shadow: 0 10px 24px rgba(16, 20, 24, 0.18);
}

.student-ai-icon-button.send.is-stop:hover:not(:disabled) {
  background: #1c232d;
  border-color: #1c232d;
}

.student-ai-icon-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.student-inline-loading {
  width: 18px;
  height: 18px;
  display: inline-block;
  border-radius: 999px;
  border: 2px solid rgba(157, 169, 193, 0.28);
  border-top-color: #c7cedd;
  animation: student-loading-spin 0.9s linear infinite;
}

.student-chat-item.pending {
  justify-items: start;
}

.student-chat-loading {
  padding: 8px 0;
}

@keyframes student-loading-spin {
  to {
    transform: rotate(360deg);
  }
}


.student-ai-input-area :deep(.el-textarea) {
  height: 100%;
}

.student-ai-input-area :deep(.el-textarea__inner) {
  height: 100%;
  min-height: 0;
  border-radius: 22px;
  border: 0;
  background: transparent;
  color: #24345d;
  box-shadow: none;
  padding: 4px 2px 0;
  font-size: 14px;
  line-height: 1.65;
}

.student-ai-input-area :deep(.el-textarea__inner:focus) {
  box-shadow: none;
}

.student-ai-sidebar-shell {
  grid-area: sidebar;
  position: relative;
  height: var(--student-ai-card-height);
}

.student-ai-sidebar-card {
  display: flex;
  flex-direction: column;
  gap: 0;
  height: 100%;
  padding: 24px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(227, 236, 247, 0.96);
  box-shadow: 0 18px 44px rgba(93, 121, 172, 0.08);
  backdrop-filter: blur(12px);
}

.student-ai-sidebar-section {
  display: grid;
  gap: 16px;
  align-content: start;
  flex: 0 0 auto;
}

.student-ai-sidebar-section.history {
  margin-top: 28px;
  padding-top: 22px;
  border-top: 1px solid #edf2f8;
  min-height: 0;
  flex: 1 1 auto;
}

.student-ai-sidebar-toggle {
  position: absolute;
  top: 50%;
  left: 0;
  width: 34px;
  height: 48px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #d9e4f6;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.96);
  color: #33568f;
  box-shadow: 0 10px 24px rgba(93, 121, 172, 0.12);
  cursor: pointer;
  transform: translate(-50%, -50%);
  z-index: 2;
}

.student-ai-sidebar-toggle .el-icon {
  transition: transform 0.2s ease;
}

.student-ai-sidebar-toggle.collapsed .el-icon {
  transform: rotate(180deg);
}

.student-ai-tool-stack {
  display: grid;
  gap: 12px;
}

.student-ai-tool-tile {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  width: 100%;
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid #dde7f7;
  background: linear-gradient(180deg, #ffffff, #f6f9ff);
  text-align: left;
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.student-ai-tool-tile:hover {
  transform: translateY(-1px);
  border-color: #cbd9f2;
  box-shadow: 0 14px 28px rgba(92, 123, 180, 0.08);
}

.student-ai-tool-icon {
  display: inline-flex;
  width: 38px;
  height: 38px;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  font-size: 14px;
  font-weight: 700;
  color: #4b5fd1;
  background: linear-gradient(180deg, #eef0ff, #e0e7ff);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.85);
}

.student-ai-tool-icon.is-tool-4 {
  color: #c25587;
  background: linear-gradient(180deg, #ffeaf3, #ffdce9);
}

.student-ai-tool-name {
  flex: 1;
  color: #17315d;
  font-size: 16px;
  font-weight: 600;
}

.student-ai-history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  min-height: 0;
  max-height: none;
  overflow-y: auto;
  padding-right: 4px;
}

.student-ai-history-item {
  width: 100%;
  min-height: 46px;
  padding: 8px 10px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-radius: 12px;
  border: 0;
  background: transparent;
  cursor: pointer;
  text-align: left;
  transition: background 0.2s ease, color 0.2s ease;
}

.student-ai-history-item:hover,
.student-ai-history-item.active {
  background: #f3f7ff;
}

.student-ai-history-icon {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  border: 1px solid #d9e4f6;
  background: #fff;
  color: #97a4bc;
}

.student-ai-history-icon svg {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.student-ai-history-title {
  display: block;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  color: #33415f;
  font-size: 15px;
  font-weight: 600;
}

.student-ai-history-input {
  flex: 1;
  min-width: 0;
  border: 1px solid #c8d8f2;
  border-radius: 12px;
  background: #fff;
  color: #22345e;
  font-size: 14px;
  padding: 10px 12px;
  outline: none;
}

.student-ai-history-empty {
  padding: 8px 4px;
  color: #7b8cad;
  font-size: 13px;
  line-height: 1.6;
}

@media (max-width: 1180px) {
  .student-progress-hero {
    grid-template-columns: 1fr;
  }

  .student-player-main.is-progress-view {
    height: auto;
    overflow: auto;
  }

  .student-progress-page {
    height: auto;
    min-height: 0;
  }

  .student-progress-stats {
    max-width: none;
  }

  .student-progress-stats-top,
  .student-progress-stats-bottom {
    grid-template-columns: 1fr;
  }

  .student-ai-page,
  .student-ai-page.collapsed {
    grid-template-columns: 1fr;
    grid-template-areas:
      "sidebar"
      "chat";
    align-items: start;
  }

  .student-ai-sidebar-toggle {
    display: none;
  }

  .student-ai-chat-card {
    height: 580px;
  }

  .student-ai-sidebar-shell,
  .student-ai-sidebar-card {
    min-height: 0;
    height: auto;
  }
}

@media (max-width: 960px) {
  .student-player-topbar {
    grid-template-columns: 1fr;
    height: auto;
    gap: 16px;
    padding: 18px 20px;
  }

  .student-topbar-center {
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .student-topbar-nav {
    justify-content: flex-start;
    overflow: auto;
    max-width: 100%;
  }

  .student-topbar-user {
    justify-self: start;
  }

  .student-player-main {
    padding: 80px 20px 28px;
  }

  .student-course-overview {
    grid-template-columns: 1fr;
  }

  .student-course-overview-meta {
    grid-template-columns: 1fr;
    max-width: none;
  }

  .student-progress-chapter-item {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .student-chapter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .student-unit-header,
  .student-chapter-footer-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .student-progress-chapter-side {
    justify-items: start;
  }

  .student-ai-chat-card {
    height: 540px;
  }
}

@media (max-width: 640px) {
  .student-chapter-grid {
    grid-template-columns: 1fr;
  }

  .student-player-main {
    padding: 80px 16px 24px;
  }

  .student-course-overview,
  .student-unit-section,
  .student-progress-hero,
  .student-progress-panel,
  .student-ai-chat-card,
  .student-ai-sidebar-card {
    padding: 22px 18px;
    border-radius: 24px;
  }

  .student-course-overview h1,
  .student-progress-hero h2,
  .student-ai-chat-title,
  .student-ai-tools-title {
    font-size: 24px;
  }

  .student-resume-button {
    min-width: 220px;
    height: 78px;
  }

  .student-resume-button-text {
    font-size: 20px;
  }

  .student-progress-stats {
    grid-template-rows: auto;
  }

  .student-chat-bubble {
    max-width: 100%;
  }
}
</style>
