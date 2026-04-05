<template>
  <div class="student-player-page">
    <header class="student-player-topbar">
      <div class="student-topbar-brand">
        <div class="student-topbar-brand-mark"></div>
        <div class="student-topbar-brand-name">泛雅</div>
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

      <div class="student-topbar-user">
        <el-avatar :size="42">{{ (studentProfile.studentName || fallbackProfile.studentName).slice(0, 1) }}</el-avatar>
        <span>{{ studentProfile.studentName || fallbackProfile.studentName }}</span>
        <el-icon><ArrowDown /></el-icon>
      </div>
    </header>

    <main class="student-player-main">
      <section v-if="activeView !== 'ai'" class="student-course-overview">
        <div class="student-course-overview-main">
          <div class="student-course-overview-tag">课程详情</div>
          <h1>{{ lesson.courseName || lesson.lessonName }}</h1>
          <p>{{ lesson.teacherName }} · 围绕当前章节持续学习，首页进度会自动同步更新。</p>
          <div class="student-course-overview-context">
            <span>{{ currentUnit.unitTitle || '当前单元待解锁' }}</span>
            <span>{{ allChapters.length }} 个章节</span>
            <span>{{ activeChapter.chapterTitle || '待学习章节' }}</span>
          </div>
        </div>
        <div class="student-course-overview-meta">
          <div class="student-course-overview-metric">
            <span>课程总进度</span>
            <strong>{{ overallProgress }}%</strong>
          </div>
          <div class="student-course-overview-metric">
            <span>平均掌握度</span>
            <strong>{{ overallMastery }}%</strong>
          </div>
          <div class="student-course-overview-metric">
            <span>当前章节</span>
            <strong>{{ activeChapter.chapterTitle || '待学习章节' }}</strong>
          </div>
        </div>
      </section>

      <section v-if="activeView === 'knowledge'" class="student-knowledge-page">
        <section
          v-for="unit in lesson.units || []"
          :key="unit.unitId"
          class="student-unit-section"
        >
          <div class="student-unit-header">
            <div class="student-unit-header-main">
              <div class="student-unit-badge">知识单元</div>
              <h2>{{ unit.unitTitle }}</h2>
              <p>共 {{ unit.chapters?.length || 0 }} 个章节，按章节逐步完成学习记录。</p>
            </div>
            <div class="student-unit-header-meta">{{ unit.chapters?.filter((chapter) => Number(chapter.progressPercent || 0) >= 100).length || 0 }}/{{ unit.chapters?.length || 0 }} 已完成</div>
          </div>

          <div class="student-chapter-grid">
            <article
              v-for="chapter in unit.chapters"
              :key="chapter.chapterId"
              class="student-chapter-card"
              :class="{ active: chapter.chapterId === activeChapter.chapterId }"
              @click="setActiveChapter(chapter)"
            >
              <div class="student-chapter-card-head">
                <div>
                  <div class="student-chapter-status" :class="getChapterStatusClass(chapter)">{{ getChapterStatusLabel(chapter) }}</div>
                  <h3>{{ chapter.chapterTitle }}</h3>
                </div>
                <div class="student-chapter-mastery-badge">
                  <span>掌握度</span>
                  <strong>{{ chapter.masteryPercent }}%</strong>
                </div>
              </div>
              <div class="student-chapter-summary">{{ chapter.summary || '可结合课件、知识点和问答记录完成本节复盘。' }}</div>
              <div class="student-chapter-points" v-if="chapter.knowledgePoints?.length">
                <span
                  v-for="point in chapter.knowledgePoints.slice(0, 3)"
                  :key="point"
                  class="student-chapter-point"
                >
                  {{ point }}
                </span>
              </div>
              <div class="student-chapter-card-footer">
                <div class="student-chapter-progress-block">
                  <div class="student-chapter-progress-text">
                    <span>学习进度</span>
                    <strong>{{ chapter.progressPercent }}%</strong>
                  </div>
                  <el-progress :percentage="chapter.progressPercent" :stroke-width="8" :show-text="false" />
                </div>
                <div class="student-chapter-footer-row">
                  <div class="student-chapter-mastery-text">掌握度 {{ chapter.masteryPercent }}%</div>
                  <el-button type="primary" @click.stop="markChapterLearned(chapter)">记录学习</el-button>
                </div>
              </div>
            </article>
          </div>
        </section>
      </section>

      <section v-else-if="activeView === 'progress'" class="student-progress-page">
        <section class="student-progress-hero">
          <div class="student-progress-hero-main">
            <div class="student-progress-chip">进度续接与节奏调整</div>
            <h2>从上次学习位置继续，按当前状态调整学习节奏。</h2>
            <p>{{ progressHintText }}</p>
            <div class="student-progress-hero-actions">
              <button type="button" class="student-secondary-action" @click="resumeLearning">
                {{ resumeLoading ? '正在续学...' : '继续学习' }}
              </button>
              <button type="button" class="student-ghost-action" @click="goToRecommendedChapter">进入推荐章节</button>
            </div>
          </div>

          <div class="student-progress-stats">
            <div class="student-progress-stat-card">
              <span>续学章节</span>
              <strong>{{ recommendedResumeChapter.chapterTitle || '待学习章节' }}</strong>
            </div>
            <div class="student-progress-stat-card">
              <span>课程总进度</span>
              <strong>{{ overallProgress }}%</strong>
            </div>
            <div class="student-progress-stat-card">
              <span>平均掌握度</span>
              <strong>{{ overallMastery }}%</strong>
            </div>
            <div class="student-progress-stat-card">
              <span>最近问答</span>
              <strong>{{ qaHistoryCount }} 条</strong>
            </div>
          </div>
        </section>

        <section class="student-progress-grid">
          <article class="student-progress-panel">
            <div class="student-progress-panel-head">
              <div>
                <div class="student-progress-panel-title">续学定位</div>
                <div class="student-progress-panel-subtitle">优先回到最近学习位置，也支持根据问答推荐锚点续学。</div>
              </div>
            </div>
            <div class="student-progress-resume-card">
              <div class="student-progress-resume-label">推荐续学章节</div>
              <strong>{{ recommendedResumeChapter.chapterTitle || '待学习章节' }}</strong>
              <p>当前锚点：{{ latestResumePoint.anchorTitle || progressState.anchorTitle || '待学习章节' }}</p>
              <div class="student-progress-resume-meta">
                <span>页码 {{ latestResumePoint.pageNo || progressState.pageNo || 1 }}</span>
                <span>当前单元 {{ currentUnit.unitTitle || '未定位' }}</span>
              </div>
              <div class="student-progress-resume-actions">
                <button type="button" class="student-secondary-action" @click="resumeLearning">
                  {{ resumeLoading ? '正在恢复...' : '恢复到该位置' }}
                </button>
                <button type="button" class="student-ghost-action" @click="goToRecommendedChapter">进入章节</button>
              </div>
            </div>
          </article>

          <article class="student-progress-panel">
            <div class="student-progress-panel-head">
              <div>
                <div class="student-progress-panel-title">节奏调整</div>
                <div class="student-progress-panel-subtitle">根据当前进度和理解状态，选择更稳或更快的学习节奏。</div>
              </div>
            </div>
            <div class="student-progress-rhythm-card">
              <div class="student-progress-rhythm-copy">{{ rhythmSuggestion }}</div>
              <div class="student-progress-rhythm-actions">
                <button
                  type="button"
                  class="student-ghost-action"
                  :disabled="adjustLoading === 'slow'"
                  @click="adjustLearningRhythm('slow')"
                >
                  {{ adjustLoading === 'slow' ? '调整中...' : '放慢节奏' }}
                </button>
                <button
                  type="button"
                  class="student-secondary-action"
                  :disabled="adjustLoading === 'fast'"
                  @click="adjustLearningRhythm('fast')"
                >
                  {{ adjustLoading === 'fast' ? '调整中...' : '加快节奏' }}
                </button>
              </div>
              <div class="student-progress-rhythm-note">{{ progressFallbackNote }}</div>
            </div>
          </article>
        </section>

        <section class="student-progress-panel">
          <div class="student-progress-panel-head">
            <div>
              <div class="student-progress-panel-title">章节完成度</div>
              <div class="student-progress-panel-subtitle">快速判断本课程当前应该继续推进还是先回看薄弱章节。</div>
            </div>
          </div>

          <div class="student-progress-chapter-list">
            <article
              v-for="chapter in chapterProgressList"
              :key="chapter.chapterId"
              class="student-progress-chapter-item"
              :class="{ active: chapter.chapterId === recommendedResumeChapter.chapterId }"
            >
              <div class="student-progress-chapter-main">
                <div class="student-progress-chapter-title">{{ chapter.chapterTitle }}</div>
                <div class="student-progress-chapter-meta">
                  <span>{{ chapter.unitTitle }}</span>
                  <span>掌握度 {{ chapter.masteryPercent }}%</span>
                </div>
              </div>
              <div class="student-progress-chapter-bar">
                <div class="student-progress-chapter-bar-fill" :style="{ width: `${chapter.progressPercent}%` }"></div>
              </div>
              <div class="student-progress-chapter-side">
                <strong>{{ chapter.progressPercent }}%</strong>
                <button type="button" class="student-progress-inline-link" @click="goToChapterById(chapter.chapterId)">
                  去学习
                </button>
              </div>
            </article>
          </div>
        </section>
      </section>

      <section v-else-if="activeView === 'ai'" class="student-ai-page" :class="{ collapsed: !aiToolsVisible }">
        <div class="student-ai-chat-card">
          <div class="student-ai-chat-header compact">
            <div class="student-ai-chat-header-main">
              <div class="student-ai-chat-title">AI实时问答</div>
            </div>
          </div>

          <div class="student-ai-chat-body">
            <div v-if="chatList.length === 0" class="student-ai-chat-empty">
              <h3>开始提问</h3>
              <p>聊天记录会自动保存在右侧历史问答中。</p>
            </div>

            <div v-else class="student-chat-list">
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
                  <div v-if="item.understandingLabel" class="student-chat-meta">
                    <span>理解程度：{{ item.understandingLabel }}</span>
                    <span>推荐回看：{{ item.anchorTitle }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="student-ai-input-area">
            <el-input
              v-model="questionText"
              type="textarea"
              :rows="5"
              resize="none"
              placeholder="输入你的问题"
            />
            <div class="student-ai-input-actions">
              <button type="button" class="student-ai-icon-button" @click="triggerVoiceUpload">上传音频</button>
              <button type="button" class="student-ai-voice-button" :disabled="voiceLoading" @click="toggleRecording">
                {{ isRecording ? '结束录音' : '语音输入' }}
              </button>
              <el-button :loading="asking" type="primary" @click="submitTextQuestion">发送问题</el-button>
            </div>
            <input
              ref="voiceInputRef"
              type="file"
              accept="audio/*"
              style="display: none"
              @change="handleVoiceFileChange"
            />
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
              <div class="student-ai-history-list">
                <button
                  v-for="session in qaSessions"
                  :key="session.sessionId"
                  type="button"
                  class="student-ai-history-item"
                  :class="{ active: session.sessionId === activeSessionId }"
                  @click="openQaSession(session.sessionId)"
                  @dblclick.stop="startSessionTitleEdit(session)"
                >
                  <span class="student-ai-history-icon">◔</span>
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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowDown, ArrowRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  adjustStudentProgress,
  getStudentLessonList,
  getStudentProgress,
  interactWithLesson,
  playStudentLesson,
  resumeStudentLesson,
  trackStudentProgress,
  verifyStudentAuth,
  voiceToText
} from '@/api/student'
import { findFrontendTestLesson, getFrontendTestLessons } from '@/mock/studentLessons'
import {
  ensurePlatformToken,
  getPlatformToken,
  getStudentLessonListCache,
  getStudentProfile,
  getStudentQaHistory,
  getStudentQaSessions,
  saveStudentLessonList,
  saveStudentProfile,
  saveStudentQaHistory,
  saveStudentQaSessions
} from '@/utils/platform'

const route = useRoute()
const voiceInputRef = ref(null)
const topbarNavRef = ref(null)
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
const voiceLoading = ref(false)
const resumeLoading = ref(false)
const adjustLoading = ref('')
const isRecording = ref(false)
const activeChapterId = ref('')
const chatList = ref([])
const qaSessions = ref([])
const activeSessionId = ref('')
const editingSessionId = ref('')
const editingSessionTitle = ref('')
const primaryNavRefs = ref({})
const navIndicator = ref({ width: 0, left: 0, opacity: 0 })
const progressFallbackNote = ref('若服务端节奏接口暂不可用，系统会自动回退为本地建议。')
const rhythmSuggestion = ref('建议先完成当前章节，再根据掌握度决定是否进入下一章。')

let mediaRecorder = null
let recordChunks = []

const primaryNavItems = [
  { label: '学习进度', value: 'progress' },
  { label: '智课讲授', value: 'knowledge' },
  { label: 'AI实时问答', value: 'ai' }
]

const lessonId = computed(() => route.params.lessonId)
const allChapters = computed(() => (lesson.value.units || []).flatMap((unit) => unit.chapters || []))
const activeChapter = computed(() => allChapters.value.find((chapter) => chapter.chapterId === activeChapterId.value) || allChapters.value[0] || {})
const currentUnit = computed(() => (
  (lesson.value.units || []).find((unit) => (unit.chapters || []).some((chapter) => chapter.chapterId === activeChapter.value.chapterId)) || {}
))
const overallProgress = computed(() => {
  if (!allChapters.value.length) return 0
  return Math.round(allChapters.value.reduce((sum, chapter) => sum + Number(chapter.progressPercent || 0), 0) / allChapters.value.length)
})
const overallMastery = computed(() => {
  if (!allChapters.value.length) return 0
  return Math.round(allChapters.value.reduce((sum, chapter) => sum + Number(chapter.masteryPercent || 0), 0) / allChapters.value.length)
})
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
const progressHintText = computed(() => {
  const chapterTitle = recommendedResumeChapter.value.chapterTitle || '当前章节'
  return `系统已定位到 ${chapterTitle}，可继续学习，也可先调整到更适合你的节奏。`
})
const chapterProgressList = computed(() => {
  return (lesson.value.units || []).flatMap((unit) => (
    (unit.chapters || []).map((chapter) => ({
      ...chapter,
      unitTitle: unit.unitTitle
    }))
  ))
})
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

function persistQaSessions() {
  const normalized = qaSessions.value
    .map((session, index) => normalizeSession(session, index))
    .sort((left, right) => Number(right.updatedAt || 0) - Number(left.updatedAt || 0))
  qaSessions.value = normalized
  saveStudentQaSessions(lessonId.value, normalized)
  const currentSession = normalized.find((session) => session.sessionId === activeSessionId.value)
  saveStudentQaHistory(lessonId.value, buildHistoryPairsFromMessages(currentSession?.messages || []))
}

function syncActiveSessionFromChatList() {
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
  persistQaSessions()
}

function loadSessionIntoChat(session) {
  activeSessionId.value = session?.sessionId || ''
  chatList.value = cloneMessages(session?.messages || [])
}

function openQaSession(sessionId) {
  if (sessionId === activeSessionId.value) return
  syncActiveSessionFromChatList()
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

function commitSessionTitleEdit(sessionId) {
  const target = qaSessions.value.find((session) => session.sessionId === sessionId)
  if (!target) {
    cancelSessionTitleEdit()
    return
  }
  target.title = createSessionTitle(editingSessionTitle.value || target.title)
  target.updatedAt = Date.now()
  persistQaSessions()
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

function setActiveChapter(chapter) {
  activeChapterId.value = chapter.chapterId
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

function applyChapterPosition(chapter) {
  if (!chapter?.chapterId) return
  activeChapterId.value = chapter.chapterId
  lesson.value.currentPage = chapter.pageNo
  lesson.value.currentKnowledgePointName = chapter.chapterTitle
  progressState.value = {
    ...progressState.value,
    pageNo: chapter.pageNo,
    anchorTitle: chapter.chapterTitle
  }
}

function goToRecommendedChapter() {
  applyChapterPosition(recommendedResumeChapter.value)
  activeView.value = 'knowledge'
}

function goToChapterById(chapterId) {
  const chapter = allChapters.value.find((item) => item.chapterId === chapterId)
  if (!chapter) return
  applyChapterPosition(chapter)
  activeView.value = 'knowledge'
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
    ElMessage.success('已恢复到最近学习位置')
  } catch {
    applyChapterPosition(recommendedResumeChapter.value)
    ElMessage.info('已根据本地缓存定位到推荐续学章节')
  } finally {
    resumeLoading.value = false
    activeView.value = 'knowledge'
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

async function markChapterLearned(chapter) {
  try {
    const res = await trackStudentProgress({
      studentId: studentProfile.value.studentId,
      lessonId: lessonId.value,
      currentTime: chapter.pageNo * 90,
      anchorId: `${lessonId.value}-A${chapter.pageNo}`,
      anchorTitle: chapter.chapterTitle,
      pageNo: chapter.pageNo,
      progressPercent: 100,
      understandingLevel: progressState.value.understandingLevel || 'partial',
      weakPoints: progressState.value.weakPoints || []
    })

    chapter.progressPercent = 100
    progressState.value = {
      ...progressState.value,
      ...res.data,
      pageNo: chapter.pageNo,
      anchorTitle: chapter.chapterTitle,
      progressPercent: overallProgress.value
    }
    lesson.value.currentPage = chapter.pageNo
    lesson.value.currentKnowledgePointName = chapter.chapterTitle
    activeChapterId.value = chapter.chapterId
    syncLessonCache()
    ElMessage.success('已记录当前章节学习进度')
  } catch (error) {
    ElMessage.error(error?.msg || '学习进度记录失败')
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
  await bootstrapStudent()

  const cachedLesson = getStudentLessonListCache().find((item) => item.lessonId === lessonId.value) || findFrontendTestLesson(lessonId.value)

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

  const targetChapter = allChapters.value.find((chapter) => chapter.pageNo === progressState.value.pageNo) || allChapters.value[0]
  activeChapterId.value = targetChapter?.chapterId || ''

  const cachedSessions = getStudentQaSessions(lessonId.value)
  if (cachedSessions.length) {
    qaSessions.value = cachedSessions.map((session, index) => normalizeSession(session, index))
  } else {
    const cachedHistory = getStudentQaHistory(lessonId.value)
    qaSessions.value = cachedHistory.length ? [buildLegacySession(cachedHistory)] : []
    if (qaSessions.value.length) {
      persistQaSessions()
    }
  }
  loadSessionIntoChat(qaSessions.value[0])

  await nextTick()
}

async function askQuestion(question, source = 'text') {
  asking.value = true
  try {
    chatList.value.push({
      id: `user-${Date.now()}`,
      role: 'user',
      content: question
    })

    const res = await interactWithLesson({
      studentId: studentProfile.value.studentId,
      lessonId: lessonId.value,
      source,
      question,
      anchorId: progressState.value.anchorId,
      anchorTitle: activeChapter.value.chapterTitle,
      pageNo: activeChapter.value.pageNo,
      context: {
        slideTitle: activeChapter.value.chapterTitle,
        slideSummary: activeChapter.value.summary,
        knowledgePoints: activeChapter.value.knowledgePoints || []
      }
    })

    chatList.value.push({
      id: `ai-${Date.now()}`,
      role: 'assistant',
      content: res.data.answer,
      relatedPoints: res.data.relatedKnowledgePoints,
      understandingLabel: res.data.understandingLabel,
      anchorTitle: res.data.resumeAnchor?.anchorTitle,
      resumePageNo: res.data.resumeAnchor?.pageNo
    })

    syncActiveSessionFromChatList()
    syncLessonCache()
    questionText.value = ''
  } finally {
    asking.value = false
  }
}

async function submitTextQuestion() {
  if (!questionText.value.trim()) {
    ElMessage.warning('请输入问题内容')
    return
  }
  await askQuestion(questionText.value.trim(), 'text')
}

function triggerVoiceUpload() {
  voiceInputRef.value?.click()
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

async function handleVoiceTextPayload(fileName, audioBase64) {
  voiceLoading.value = true
  try {
    const voiceRes = await voiceToText({
      studentId: studentProfile.value.studentId,
      lessonId: lessonId.value,
      fileName,
      audioBase64
    })
    questionText.value = voiceRes.data.text
    await askQuestion(voiceRes.data.text, 'voice')
  } finally {
    voiceLoading.value = false
  }
}

async function handleVoiceFileChange(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const audioBase64 = await fileToBase64(file)
  await handleVoiceTextPayload(file.name, audioBase64)
  event.target.value = ''
}

async function toggleRecording() {
  if (isRecording.value) {
    mediaRecorder?.stop()
    return
  }

  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
    ElMessage.warning('当前浏览器不支持实时录音，请改用上传音频')
    return
  }

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  recordChunks = []
  mediaRecorder = new MediaRecorder(stream)
  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) recordChunks.push(event.data)
  }
  mediaRecorder.onstop = async () => {
    isRecording.value = false
    const blob = new Blob(recordChunks, { type: 'audio/webm' })
    const file = new File([blob], 'voice-question.webm', { type: blob.type })
    const audioBase64 = await fileToBase64(file)
    await handleVoiceTextPayload(file.name, audioBase64)
    stream.getTracks().forEach((track) => track.stop())
  }

  mediaRecorder.start()
  isRecording.value = true
}

function toggleAiTools() {
  aiToolsVisible.value = !aiToolsVisible.value
}

onMounted(async () => {
  try {
    await loadLesson()
    await nextTick()
    updateNavIndicator()
    window.addEventListener('resize', updateNavIndicator)
  } catch (error) {
    ElMessage.error(error?.msg || '课程详情加载失败')
  }
})

watch(activeView, async () => {
  await nextTick()
  updateNavIndicator()
})

onBeforeUnmount(() => {
  mediaRecorder?.stream?.getTracks?.().forEach((track) => track.stop())
  window.removeEventListener('resize', updateNavIndicator)
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

.student-topbar-brand-mark {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: linear-gradient(135deg, #ed5b56 0%, #cf2e2a 100%);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.28);
}

.student-topbar-brand-name {
  font-size: 28px;
  font-weight: 700;
  color: #262626;
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
  justify-self: end;
  color: #33415f;
  font-size: 14px;
  font-weight: 500;
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
  padding: 116px 36px 36px;
}

.student-course-overview {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: 22px;
  margin-bottom: 24px;
  padding: 30px 32px;
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
}

.student-course-overview-tag {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(165, 190, 234, 0.38);
  color: #365ea7;
  backdrop-filter: blur(10px);
  font-size: 12px;
  font-weight: 600;
}

.student-course-overview h1 {
  margin: 18px 0 0;
  color: #17315d;
  font-size: 30px;
  line-height: 1.32;
}

.student-course-overview p {
  margin: 10px 0 0;
  color: rgba(49, 79, 133, 0.84);
  font-size: 14px;
  line-height: 1.8;
}

.student-course-overview-context {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
}

.student-course-overview-context span {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid rgba(159, 187, 233, 0.3);
  color: #35568f;
  font-size: 13px;
}

.student-course-overview-meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  align-self: end;
}

.student-course-overview-metric {
  padding: 18px 16px;
  border-radius: 24px;
  border: 1px solid rgba(156, 186, 233, 0.28);
  background: rgba(255, 255, 255, 0.62);
  backdrop-filter: blur(12px);
}

.student-course-overview-metric span {
  display: block;
  color: rgba(54, 85, 140, 0.72);
  font-size: 12px;
}

.student-course-overview-metric strong {
  display: block;
  margin-top: 10px;
  color: #16315e;
  font-size: 18px;
  line-height: 1.5;
}

.student-knowledge-page {
  display: grid;
  gap: 22px;
}

.student-progress-page {
  display: grid;
  gap: 22px;
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

.student-unit-header-main p {
  margin: 10px 0 0;
  color: #7484a4;
  font-size: 13px;
  line-height: 1.8;
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
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
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
  min-width: 88px;
  padding: 12px 14px;
  border-radius: 20px;
  background: rgba(232, 240, 255, 0.9);
  border: 1px solid rgba(207, 220, 243, 0.98);
  text-align: right;
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

.student-chapter-summary {
  margin-top: 16px;
  color: #6d7d9d;
  font-size: 13px;
  line-height: 1.8;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.student-chapter-points {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.student-chapter-point {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(241, 246, 255, 0.96);
  border: 1px solid rgba(219, 229, 245, 0.98);
  color: #58709e;
  font-size: 12px;
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

.student-chapter-progress-text,
.student-chapter-mastery-text {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #6d7a98;
  font-size: 13px;
}

.student-chapter-progress-text strong {
  color: #18325f;
}

.student-chapter-mastery-text {
  color: #6d7c99;
}

.student-chapter-footer-row {
  display: flex;
  justify-content: space-between;
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

.student-progress-hero,
.student-progress-panel {
  padding: 26px 28px;
}

.student-progress-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 22px;
  background:
    radial-gradient(circle at 18% 18%, rgba(255, 255, 255, 0.86), transparent 28%),
    linear-gradient(135deg, #e7f0ff 0%, #d9e8ff 48%, #f2f7ff 100%);
}

.student-progress-chip {
  display: inline-flex;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  color: #4868a9;
  font-size: 12px;
  font-weight: 600;
}

.student-progress-hero h2 {
  margin: 16px 0 0;
  color: #17315d;
  font-size: 28px;
  line-height: 1.35;
}

.student-progress-hero p {
  margin: 12px 0 0;
  color: #7082a4;
  font-size: 14px;
  line-height: 1.8;
}

.student-progress-hero-actions,
.student-progress-resume-actions,
.student-progress-rhythm-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 18px;
}

.student-progress-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.student-progress-stat-card {
  padding: 18px 16px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.66);
  border: 1px solid rgba(208, 222, 245, 0.96);
}

.student-progress-stat-card span {
  display: block;
  color: #7590bc;
  font-size: 12px;
}

.student-progress-stat-card strong {
  display: block;
  margin-top: 10px;
  color: #17315d;
  font-size: 18px;
  line-height: 1.5;
}

.student-progress-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 22px;
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
  min-height: 700px;
  height: 100%;
  padding: 28px;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.9);
}

.student-ai-chat-header {
  display: flex;
  align-items: center;
}

.student-ai-chat-header.compact {
  padding-bottom: 8px;
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

.student-ai-chat-body {
  flex: 1;
  min-height: 0;
  max-height: 560px;
  padding: 12px 0 20px;
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.student-ai-chat-empty {
  display: grid;
  place-items: center;
  min-height: 360px;
  padding: 40px 12px;
  background: transparent;
  text-align: center;
  color: #6b7793;
}

.student-ai-chat-empty h3 {
  margin: 0;
  color: #17315d;
  font-size: 24px;
}

.student-ai-chat-empty p {
  margin-top: 12px;
  max-width: 360px;
  color: #6f809f;
  line-height: 1.9;
}

.student-chat-list {
  display: grid;
  gap: 20px;
  align-content: start;
}

.student-chat-item {
  display: grid;
  gap: 8px;
}

.student-chat-role {
  color: #8792aa;
  font-size: 12px;
}

.student-chat-bubble {
  max-width: 86%;
  padding: 18px 20px 16px;
  border-radius: 24px;
  background: linear-gradient(180deg, #ffffff, #f7faff);
  border: 0;
  color: #24345d;
  line-height: 1.8;
  box-shadow: 0 12px 28px rgba(101, 128, 176, 0.08);
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

.student-chat-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid rgba(220, 230, 246, 0.96);
  color: #7687a6;
  font-size: 12px;
}

.student-ai-input-area {
  margin-top: auto;
  padding: 18px 20px 20px;
  border: 0;
  border-radius: 26px;
  background: linear-gradient(180deg, #eef4ff, #e9f0ff);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.student-ai-input-actions {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.student-ai-icon-button,
.student-ai-voice-button {
  border: 1px solid #d7e2f3;
  border-radius: 14px;
  background: #fff;
  color: #23355f;
  padding: 10px 16px;
  cursor: pointer;
}

.student-ai-icon-button:hover,
.student-ai-voice-button:hover {
  background: #f4f8ff;
  border-color: #c6d8f2;
}

.student-ai-voice-button {
  background: linear-gradient(135deg, #7ea1ef, #587fdc);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 12px 22px rgba(90, 124, 204, 0.2);
}

.student-ai-voice-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.student-ai-input-area :deep(.el-textarea__inner) {
  border-radius: 22px;
  border: 0;
  background: rgba(255, 255, 255, 0.86);
  color: #24345d;
  box-shadow: none;
  padding: 18px 18px 16px;
  min-height: 136px;
}

.student-ai-input-area :deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 4px rgba(151, 184, 233, 0.16);
}

.student-ai-input-actions :deep(.el-button) {
  min-height: 42px;
  padding: 0 18px;
  border-radius: 14px;
  border: 0;
  background: linear-gradient(135deg, #6d94f1, #4d78de);
  box-shadow: 0 12px 22px rgba(94, 130, 208, 0.18);
}

.student-ai-sidebar-shell {
  grid-area: sidebar;
  position: relative;
  min-height: 700px;
  height: 100%;
}

.student-ai-sidebar-card {
  display: grid;
  gap: 0;
  height: 100%;
  min-height: 700px;
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
}

.student-ai-sidebar-section.history {
  margin-top: 22px;
  padding-top: 22px;
  border-top: 1px solid #edf2f8;
  min-height: 0;
  flex: 1;
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
  gap: 14px;
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
  display: grid;
  gap: 8px;
  flex: 1;
  min-height: 0;
  max-height: none;
  overflow-y: auto;
  padding-right: 2px;
}

.student-ai-history-item {
  width: 100%;
  min-height: 50px;
  padding: 0 14px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-radius: 14px;
  border: 1px solid transparent;
  background: transparent;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}

.student-ai-history-item:hover,
.student-ai-history-item.active {
  border-color: #e2eaf7;
  background: #fff;
  box-shadow: 0 10px 22px rgba(92, 123, 180, 0.08);
}

.student-ai-history-icon {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  border: 1px solid #d9e4f6;
  color: #98a6c1;
  font-size: 11px;
  background: #fff;
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
  padding: 16px;
  border-radius: 16px;
  border: 1px dashed #dbe5f6;
  background: #fafcff;
  color: #7b8cad;
  font-size: 13px;
  line-height: 1.7;
}

@media (max-width: 1180px) {
  .student-progress-grid,
  .student-progress-hero {
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

  .student-ai-sidebar-shell,
  .student-ai-sidebar-card,
  .student-ai-chat-card {
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
    padding: 164px 20px 28px;
  }

  .student-course-overview {
    grid-template-columns: 1fr;
  }

  .student-course-overview-meta {
    grid-template-columns: 1fr;
  }

  .student-progress-chapter-item {
    grid-template-columns: 1fr;
    align-items: start;
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
    min-height: 0;
  }
}

@media (max-width: 640px) {
  .student-player-main {
    padding: 164px 16px 24px;
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

  .student-progress-stats {
    grid-template-columns: 1fr;
  }

  .student-chat-bubble {
    max-width: 100%;
  }
}
</style>
