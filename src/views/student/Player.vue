<template>
  <div class="student-player-page">
    <header class="student-player-topbar">
      <div class="student-topbar-brand">
        <div class="student-topbar-brand-mark"></div>
        <div class="student-topbar-brand-name">泛雅</div>
      </div>

      <nav class="student-topbar-nav">
        <button
          v-for="item in navItems"
          :key="item.value"
          type="button"
          class="student-topbar-nav-item"
          :class="{ active: activeView === item.value }"
          @click="activeView = item.value"
        >
          {{ item.label }}
        </button>
      </nav>

      <div class="student-topbar-user">
        <el-avatar :size="42">{{ (studentProfile.studentName || fallbackProfile.studentName).slice(0, 1) }}</el-avatar>
        <span>{{ studentProfile.studentName || fallbackProfile.studentName }}</span>
        <el-icon><ArrowDown /></el-icon>
      </div>
    </header>

    <main class="student-player-main">
      <section class="student-course-overview">
        <div>
          <div class="student-course-overview-tag">课程详情</div>
          <h1>{{ lesson.courseName || lesson.lessonName }}</h1>
          <p>{{ lesson.teacherName }} · 章节学习进度会同步回写，并用于计算首页课程平均进度。</p>
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
        <div class="student-knowledge-directory">
          <div class="student-directory-chip">知识学习</div>
          <div class="student-directory-title">知识模块页</div>
          <div class="student-directory-subtitle">按知识单元查看章节结构，当前章节的学习进度与掌握度均支持从 0% 开始逐步累计。</div>
        </div>

        <section
          v-for="unit in lesson.units || []"
          :key="unit.unitId"
          class="student-unit-section"
        >
          <div class="student-unit-header">
            <div>
              <div class="student-unit-badge">知识单元</div>
              <h2>{{ unit.unitTitle }}</h2>
            </div>
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
                <h3>{{ chapter.chapterTitle }}</h3>
                <div class="student-chapter-circle">{{ chapter.masteryPercent }}%</div>
              </div>
              <div class="student-chapter-card-footer">
                <div class="student-chapter-progress-text">
                  <span>学习进度</span>
                  <strong>{{ chapter.progressPercent }}%</strong>
                </div>
                <el-progress :percentage="chapter.progressPercent" :stroke-width="8" :show-text="false" />
                <div class="student-chapter-mastery-text">掌握度 {{ chapter.masteryPercent }}%</div>
                <el-button type="primary" plain @click.stop="markChapterLearned(chapter)">记录学习</el-button>
              </div>
            </article>
          </div>
        </section>
      </section>

      <section v-else-if="activeView === 'ai'" class="student-ai-page" :class="{ collapsed: !aiToolsVisible }">
        <div class="student-ai-chat-card">
          <div class="student-ai-chat-header">
            <div>
              <div class="student-ai-chat-title">AI学伴</div>
              <div class="student-ai-chat-subtitle">{{ lesson.aiWelcome || 'Hi，左睿涛同学，围绕当前章节开始提问吧。' }}</div>
            </div>
            <button type="button" class="student-ai-tools-toggle mobile-only" @click="toggleAiTools">
              {{ aiToolsVisible ? '隐藏工具' : '显示工具' }}
            </button>
          </div>

          <div class="student-ai-chat-body">
            <div v-if="chatList.length === 0" class="student-ai-chat-empty">
              <h3>{{ lesson.aiPrompt || '可以输入文字问题，也可以直接使用语音输入。' }}</h3>
              <p>当前已定位到章节：{{ activeChapter.chapterTitle || '待学习章节' }}。你可以让 AI 帮你解释概念、梳理解题步骤或总结重点。</p>
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
                  <div>{{ item.content }}</div>
                  <div v-if="item.relatedPoints?.length" class="student-chat-points">
                    <el-tag v-for="point in item.relatedPoints" :key="point" size="small" effect="plain">{{ point }}</el-tag>
                  </div>
                  <div v-if="item.understandingLabel" class="student-chat-meta">
                    理解程度：{{ item.understandingLabel }} · 推荐回看：{{ item.anchorTitle }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="student-ai-input-area">
            <el-input
              v-model="questionText"
              type="textarea"
              :rows="4"
              resize="none"
              placeholder="请输入你的问题，或点击语音输入直接提问。"
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

        <aside v-if="aiToolsVisible" class="student-ai-tools-card">
          <div class="student-ai-tools-header">
            <div>
              <div class="student-ai-tools-title">AI工具</div>
              <div class="student-ai-tools-subtitle">首次进入默认展开，可随时收起。</div>
            </div>
            <button type="button" class="student-ai-tools-toggle" @click="toggleAiTools">隐藏</button>
          </div>

          <div class="student-ai-tools-list">
            <div v-for="tool in lesson.aiTools || []" :key="tool.id" class="student-ai-tool-item">
              <div>
                <div class="student-ai-tool-name">{{ tool.name }}</div>
                <div class="student-ai-tool-desc">{{ tool.desc }}</div>
              </div>
              <el-icon><ArrowRight /></el-icon>
            </div>
          </div>
        </aside>

        <button v-else type="button" class="student-ai-tools-reopen" @click="toggleAiTools">显示 AI 工具</button>
      </section>

      <section v-else class="student-placeholder-page">
        <div class="student-placeholder-card">
          <h2>{{ currentNavLabel }}</h2>
          <p>该功能区已预留入口，当前版本先保留静态占位，后续可按真实业务继续接入。</p>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowDown, ArrowRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  getStudentLessonList,
  getStudentProgress,
  interactWithLesson,
  playStudentLesson,
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
  saveStudentLessonList,
  saveStudentProfile,
  saveStudentQaHistory
} from '@/utils/platform'

const route = useRoute()
const voiceInputRef = ref(null)
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
const activeView = ref('knowledge')
const aiToolsVisible = ref(true)
const questionText = ref('')
const asking = ref(false)
const voiceLoading = ref(false)
const isRecording = ref(false)
const activeChapterId = ref('')
const chatList = ref([])

let mediaRecorder = null
let recordChunks = []

const navItems = [
  { label: '知识学习', value: 'knowledge' },
  { label: 'AI 互动室', value: 'ai' },
  { label: '知识图谱', value: 'graph' },
  { label: '问题图谱', value: 'questionGraph' },
  { label: '任务·作业·考试', value: 'task' },
  { label: '成绩分析', value: 'score' }
]

const lessonId = computed(() => route.params.lessonId)
const allChapters = computed(() => (lesson.value.units || []).flatMap((unit) => unit.chapters || []))
const activeChapter = computed(() => allChapters.value.find((chapter) => chapter.chapterId === activeChapterId.value) || allChapters.value[0] || {})
const currentNavLabel = computed(() => navItems.find((item) => item.value === activeView.value)?.label || '')
const overallProgress = computed(() => {
  if (!allChapters.value.length) return 0
  return Math.round(allChapters.value.reduce((sum, chapter) => sum + Number(chapter.progressPercent || 0), 0) / allChapters.value.length)
})
const overallMastery = computed(() => {
  if (!allChapters.value.length) return 0
  return Math.round(allChapters.value.reduce((sum, chapter) => sum + Number(chapter.masteryPercent || 0), 0) / allChapters.value.length)
})

function buildCachedConversation(history) {
  return history.flatMap((item, index) => ([
    { id: `history-q-${index}`, role: 'user', content: item.question },
    {
      id: item.id || `history-a-${index}`,
      role: 'assistant',
      content: item.answer,
      anchorTitle: item.anchorTitle,
      understandingLabel: item.understandingLabel,
      relatedPoints: item.relatedPoints || []
    }
  ]))
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
      { id: 'tool-1', name: 'AI陪练', desc: '围绕当前章节做概念追问、例题拆解和重点复盘。' },
      { id: 'tool-2', name: 'AI阅读助手', desc: '辅助梳理课件重点、术语定义和章节摘要。' },
      { id: 'tool-3', name: 'AI写作助手', desc: '帮助整理实验报告、课程摘要和学习反思。' },
      { id: 'tool-4', name: 'AI文档问答', desc: '基于课程资料快速定位相关知识内容。' },
      { id: 'tool-5', name: 'AI科研趋势', desc: '延展相关领域的新技术、新案例和工程应用。' }
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
      questionCount: getStudentQaHistory(lesson.value.lessonId).length
    }
  })
  saveStudentLessonList(updated)
}

function setActiveChapter(chapter) {
  activeChapterId.value = chapter.chapterId
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

  const cachedHistory = getStudentQaHistory(lessonId.value)
  chatList.value = buildCachedConversation(cachedHistory)

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
      anchorTitle: res.data.resumeAnchor.anchorTitle
    })

    const historyPairs = []
    for (let index = 0; index < chatList.value.length; index += 2) {
      const questionItem = chatList.value[index]
      const answerItem = chatList.value[index + 1]
      if (!questionItem || !answerItem) continue
      historyPairs.push({
        id: answerItem.id,
        question: questionItem.content,
        answer: answerItem.content,
        anchorTitle: answerItem.anchorTitle,
        understandingLabel: answerItem.understandingLabel,
        relatedPoints: answerItem.relatedPoints || []
      })
    }
    saveStudentQaHistory(lessonId.value, historyPairs)
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
  } catch (error) {
    ElMessage.error(error?.msg || '课程详情加载失败')
  }
})

onBeforeUnmount(() => {
  mediaRecorder?.stream?.getTracks?.().forEach((track) => track.stop())
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

.student-topbar-nav {
  display: flex;
  justify-content: center;
  gap: 22px;
  min-width: 0;
}

.student-topbar-nav-item {
  border: 0;
  background: transparent;
  color: #4f5b75;
  font-size: 15px;
  padding: 10px 4px;
  cursor: pointer;
  position: relative;
  white-space: nowrap;
}

.student-topbar-nav-item.active {
  color: #1c2a52;
  font-weight: 600;
}

.student-topbar-nav-item.active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -10px;
  height: 3px;
  border-radius: 999px;
  background: #3d63f0;
}

.student-topbar-user {
  justify-self: end;
  color: #33415f;
  font-size: 14px;
  font-weight: 500;
}

.student-player-main {
  padding: 116px 36px 36px;
}

.student-course-overview {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: 22px;
  margin-bottom: 24px;
  padding: 26px 28px;
  border-radius: 28px;
  background: linear-gradient(135deg, rgba(42, 162, 128, 0.96), rgba(69, 182, 149, 0.92));
  color: #fff;
}

.student-course-overview-tag {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  font-size: 12px;
}

.student-course-overview h1 {
  margin: 18px 0 0;
  font-size: 26px;
  line-height: 1.4;
}

.student-course-overview p {
  margin: 10px 0 0;
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
}

.student-course-overview-meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  align-self: end;
}

.student-course-overview-metric {
  padding: 16px 14px;
  border-radius: 22px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.07);
}

.student-course-overview-metric span {
  display: block;
  color: rgba(255, 255, 255, 0.8);
  font-size: 12px;
}

.student-course-overview-metric strong {
  display: block;
  margin-top: 10px;
  font-size: 18px;
  line-height: 1.5;
}

.student-knowledge-directory,
.student-unit-section,
.student-ai-chat-card,
.student-ai-tools-card,
.student-placeholder-card {
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid #edf2f8;
  box-shadow: 0 16px 40px rgba(25, 43, 92, 0.05);
}

.student-knowledge-directory {
  padding: 28px;
  margin-bottom: 24px;
}

.student-directory-chip,
.student-unit-badge {
  display: inline-flex;
  padding: 7px 12px;
  border-radius: 999px;
  background: linear-gradient(135deg, #44b3ff, #7cd5ff);
  color: #fff;
  font-size: 12px;
}

.student-unit-badge {
  background: linear-gradient(135deg, #21c87a, #2ce0b5);
}

.student-directory-title {
  margin-top: 16px;
  color: #3d63f0;
  font-size: 24px;
  font-weight: 700;
}

.student-directory-subtitle {
  margin-top: 10px;
  color: #7c88a3;
  font-size: 13px;
  line-height: 1.8;
}

.student-unit-section {
  padding: 28px;
  margin-bottom: 22px;
}

.student-unit-header h2 {
  margin: 14px 0 0;
  color: #16284e;
  font-size: 24px;
}

.student-chapter-grid {
  margin-top: 24px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 18px;
}

.student-chapter-card {
  padding: 20px;
  border-radius: 24px;
  background: #f9fbff;
  border: 1px solid #e6edf8;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.student-chapter-card:hover,
.student-chapter-card.active {
  transform: translateY(-2px);
  border-color: #cfdcf4;
  box-shadow: 0 16px 34px rgba(37, 61, 114, 0.08);
}

.student-chapter-card-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.student-chapter-card-head h3 {
  margin: 0;
  color: #172852;
  font-size: 20px;
  line-height: 1.6;
}

.student-chapter-circle {
  flex-shrink: 0;
  width: 58px;
  height: 58px;
  border-radius: 999px;
  border: 4px solid #dfe6f5;
  color: #4d5d7d;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
}

.student-chapter-card-footer {
  margin-top: 20px;
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
  color: #1d2c56;
}

.student-chapter-mastery-text {
  margin: 12px 0 18px;
}

.student-ai-page {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 22px;
  align-items: start;
}

.student-ai-page.collapsed {
  grid-template-columns: 1fr auto;
}

.student-ai-chat-card {
  min-height: 640px;
  padding: 24px;
  display: flex;
  flex-direction: column;
}

.student-ai-chat-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-start;
  padding-bottom: 20px;
  border-bottom: 1px solid #edf2f8;
}

.student-ai-chat-title,
.student-ai-tools-title {
  color: #16284e;
  font-size: 28px;
  font-weight: 700;
}

.student-ai-chat-subtitle,
.student-ai-tools-subtitle {
  margin-top: 8px;
  color: #7e89a1;
  font-size: 14px;
  line-height: 1.8;
}

.student-ai-chat-body {
  flex: 1;
  padding: 24px 0;
}

.student-ai-chat-empty {
  display: grid;
  place-items: center;
  min-height: 300px;
  text-align: center;
  color: #6b7793;
}

.student-ai-chat-empty h3 {
  margin: 0;
  color: #1a2b57;
  font-size: 22px;
}

.student-ai-chat-empty p {
  margin-top: 12px;
  max-width: 620px;
  line-height: 1.9;
}

.student-chat-list {
  display: grid;
  gap: 16px;
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
  max-width: 82%;
  padding: 16px 18px;
  border-radius: 20px;
  background: #f5f8ff;
  border: 1px solid #e6edf8;
  color: #24345d;
  line-height: 1.8;
}

.student-chat-item.is-user {
  justify-items: end;
}

.student-chat-item.is-user .student-chat-bubble {
  background: #eff7f3;
  border-color: #d6eadf;
}

.student-chat-points {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.student-chat-meta {
  margin-top: 10px;
  color: #7b87a0;
  font-size: 12px;
}

.student-ai-input-area {
  padding-top: 18px;
  border-top: 1px solid #edf2f8;
}

.student-ai-input-actions {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.student-ai-icon-button,
.student-ai-voice-button,
.student-ai-tools-toggle,
.student-ai-tools-reopen {
  border: 1px solid #d8e1f1;
  border-radius: 14px;
  background: #fff;
  color: #23355f;
  padding: 10px 16px;
  cursor: pointer;
}

.student-ai-voice-button {
  background: linear-gradient(135deg, #5d7cff, #3d63f0);
  border-color: transparent;
  color: #fff;
}

.student-ai-voice-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.student-ai-tools-card {
  padding: 24px;
}

.student-ai-tools-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding-bottom: 20px;
  border-bottom: 1px solid #edf2f8;
}

.student-ai-tools-list {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}

.student-ai-tool-item {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid #e6edf8;
  background: #fbfcff;
}

.student-ai-tool-name {
  color: #1b2c56;
  font-size: 18px;
  font-weight: 600;
}

.student-ai-tool-desc {
  margin-top: 6px;
  color: #7c88a3;
  font-size: 13px;
  line-height: 1.7;
}

.student-ai-tools-reopen {
  align-self: start;
}

.student-placeholder-card {
  padding: 40px;
}

.student-placeholder-card h2 {
  margin: 0;
  color: #1b2c56;
  font-size: 26px;
}

.student-placeholder-card p {
  margin: 14px 0 0;
  color: #7c88a3;
  line-height: 1.9;
}

.mobile-only {
  display: none;
}

@media (max-width: 1180px) {
  .student-ai-page,
  .student-ai-page.collapsed {
    grid-template-columns: 1fr;
  }

  .student-ai-tools-reopen {
    width: fit-content;
  }
}

@media (max-width: 960px) {
  .student-player-topbar {
    grid-template-columns: 1fr;
    height: auto;
    gap: 16px;
    padding: 18px 20px;
  }

  .student-topbar-nav {
    justify-content: flex-start;
    overflow: auto;
    padding-bottom: 6px;
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

  .mobile-only {
    display: inline-flex;
  }
}
</style>
