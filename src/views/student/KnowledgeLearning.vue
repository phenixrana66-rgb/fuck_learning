<template>
  <div class="knowledge-page">
    <header class="knowledge-topbar">
      <div
        class="knowledge-brand"
        role="button"
        tabindex="0"
        @click="goStudentHome"
        @keydown.enter.prevent="goStudentHome"
        @keydown.space.prevent="goStudentHome"
      >
        <div class="knowledge-brand-mark"></div>
        <div class="knowledge-brand-name">泛雅</div>
      </div>
      <el-button class="knowledge-back-button" plain @click="goBack">返回课程详情</el-button>
    </header>

    <main class="knowledge-workspace">
      <section class="knowledge-left">
        <section class="knowledge-summary-card">
          <div class="knowledge-summary-main">
            <h1>{{ detail.sectionTitle || '章节学习' }}</h1>
          </div>
          <div class="knowledge-summary-stats">
            <div class="knowledge-summary-stat">
              <span>学习进度</span>
              <strong>{{ detail.progressPercent || 0 }}%</strong>
            </div>
            <div class="knowledge-summary-stat">
              <span>章节掌握度</span>
              <strong>{{ detail.masteryPercent || 0 }}%</strong>
            </div>
          </div>
        </section>

        <section class="ppt-card">
          <div class="ppt-card-header">
            <div>
              <div class="ppt-card-title">PPT 学习</div>
              <div class="ppt-card-subtitle">当前页 {{ activePageNo }} / {{ totalPages }}</div>
            </div>
            <button
              type="button"
              class="ppt-audio-button"
              :disabled="!detail.audioUrl || detail.audioStatus !== 'published'"
              @click="toggleSectionAudio"
            >
              {{ isAudioPlaying ? '暂停播放' : '语音播放' }}
            </button>
          </div>

          <div class="ppt-card-body">
            <aside ref="thumbnailRailRef" class="thumbnail-rail">
              <button
                v-for="page in pages"
                :key="page.lessonPageId || page.pageNo"
                :ref="(element) => setThumbnailRef(page.pageNo, element)"
                type="button"
                class="thumbnail-card"
                :class="{ active: page.pageNo === activePageNo }"
                @mousedown.prevent
                @click="setActivePage(page.pageNo)"
              >
                <div class="thumbnail-media">
                  <img :src="page.imageUrl" :alt="`第 ${page.pageNo} 页缩略图`" loading="lazy" />
                  <span class="thumbnail-page-badge">{{ page.pageNo }}</span>
                </div>
              </button>
            </aside>

            <div ref="viewerShellRef" class="viewer-shell">
              <div class="viewer-stage">
                <img
                  v-if="activePage"
                  class="viewer-slide"
                  :src="activePage.imageUrl"
                  :alt="`第 ${activePage.pageNo} 页幻灯片`"
                />
                <div v-else class="viewer-empty">暂无课件页</div>

                <div v-if="activePage" class="viewer-toolbar">
                  <button
                    type="button"
                    class="viewer-tool-button"
                    :disabled="!hasPrevPage"
                    @mousedown.prevent
                    @click="goPrevPage"
                  >
                    <svg viewBox="0 0 20 20" aria-hidden="true">
                      <path d="M12.5 4.5L7 10l5.5 5.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                    </svg>
                  </button>
                  <div class="viewer-page-indicator">{{ activePageNo }} / {{ totalPages }}</div>
                  <button
                    type="button"
                    class="viewer-tool-button"
                    :disabled="!hasNextPage"
                    @mousedown.prevent
                    @click="goNextPage"
                  >
                    <svg viewBox="0 0 20 20" aria-hidden="true">
                      <path d="M7.5 4.5L13 10l-5.5 5.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    class="viewer-tool-button"
                    @mousedown.prevent
                    @click="toggleViewerFullscreen"
                  >
                    <svg viewBox="0 0 20 20" aria-hidden="true">
                      <path d="M4.5 7V4.5H7M13 4.5h2.5V7M15.5 13v2.5H13M7 15.5H4.5V13" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
          <audio
            ref="sectionAudioRef"
            class="section-audio"
            :src="detail.audioUrl || ''"
            preload="none"
            @play="isAudioPlaying = true"
            @pause="isAudioPlaying = false"
            @ended="isAudioPlaying = false"
          ></audio>
        </section>

        <section class="guide-card">
          <div class="guide-card-head">
            <h2>教师讲稿</h2>
          </div>
          <div class="guide-card-body">
            {{ detail.scriptContent || '当前章节暂无教师讲稿。' }}
          </div>
        </section>
      </section>

      <aside class="knowledge-right">
        <section class="ai-card" :class="{ 'has-chat': chatList.length > 0 }">
          <div class="ai-card-head">
            <h2>AI 学伴</h2>
          </div>

          <template v-if="chatList.length === 0">
            <div class="ai-quick-questions">
              <button
                v-for="item in quickQuestions"
                :key="item"
                type="button"
                class="ai-chip"
                @click="fillQuestion(item)"
              >
                {{ item }}
              </button>
            </div>
            <div class="ai-welcome-spacer"></div>
          </template>

          <div v-else ref="chatScrollRef" class="ai-chat-list">
            <article
              v-for="message in chatList"
              :key="message.id"
              class="ai-message"
              :class="message.role"
            >
              <div class="ai-message-role">{{ message.role === 'user' ? '我' : 'AI 学伴' }}</div>
              <div class="ai-message-bubble">{{ message.content }}</div>
            </article>
          </div>

          <form class="ai-input-box" @submit.prevent="submitQuestion">
            <textarea
              v-model="questionText"
              class="ai-textarea"
              placeholder="输入你的问题"
              rows="3"
            ></textarea>
            <div class="ai-input-actions">
              <button type="submit" class="ai-send-button" :disabled="asking || !questionText.trim()">
                {{ asking ? '发送中...' : '发送问题' }}
              </button>
            </div>
          </form>
        </section>
      </aside>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  getStudentSectionDetail,
  interactWithLesson,
  markStudentPageRead,
  saveStudentRecentChapter
} from '@/api/student'
import { findFrontendTestLesson } from '@/mock/studentLessons'
import { getStudentProfile } from '@/utils/platform'

const router = useRouter()
const route = useRoute()

const fallbackProfile = {
  studentId: 'S2026001',
  studentName: '',
  collegeName: ''
}

const studentProfile = ref({ ...fallbackProfile, ...getStudentProfile() })
const detail = ref({
  lessonId: '',
  lessonDbId: '',
  courseName: '',
  teacherName: '',
  unitTitle: '',
  sectionId: '',
  sectionTitle: '',
  progressPercent: 0,
  masteryPercent: 0,
  aiGuideContent: '',
  scriptContent: '',
  audioUrl: '',
  audioStatus: '',
  knowledgePoints: [],
  pages: [],
  currentPageNo: 1
})
const activePageNo = ref(1)
const questionText = ref('')
const asking = ref(false)
const chatList = ref([])
const isAudioPlaying = ref(false)
const thumbnailRailRef = ref(null)
const viewerShellRef = ref(null)
const chatScrollRef = ref(null)
const sectionAudioRef = ref(null)
const thumbnailRefs = ref({})

const lessonId = computed(() => String(route.params.lessonId || ''))
const chapterId = computed(() => String(route.query.chapterId || ''))
const restorePageNo = computed(() => Number(route.query.pageNo || 0))
const sectionId = computed(() => String(route.params.sectionId || detail.value.sectionId || chapterId.value || ''))
const pages = computed(() => detail.value.pages || [])
const totalPages = computed(() => pages.value.length)
const activePage = computed(() => pages.value.find((page) => Number(page.pageNo) === Number(activePageNo.value)) || pages.value[0] || null)
const hasPrevPage = computed(() => activePageNo.value > 1)
const hasNextPage = computed(() => activePageNo.value < totalPages.value)
const quickQuestions = computed(() => {
  const title = detail.value.sectionTitle || '当前章节'
  return [
    `帮我概括《${title}》的重点`,
    `《${title}》里的核心公式之间有什么关系`,
    `《${title}》在工程里通常怎么应用`
  ]
})

function normalizeFallbackDetail() {
  const lesson = findFrontendTestLesson(lessonId.value)
  const allUnits = lesson?.units || []
  const locatedUnit = allUnits.find((unit) => (unit.chapters || []).some((chapter) => chapter.chapterId === chapterId.value))
    || allUnits.find((unit) => unit.unitTitle === '压杆稳定')
    || allUnits[0]
  const chapter = (locatedUnit?.chapters || []).find((item) => item.chapterId === chapterId.value)
    || (locatedUnit?.chapters || [])[0]

  const fallbackPages = (chapter?.learningPages || []).map((page) => ({
    lessonPageId: page.lessonPageId || `${chapter?.chapterId || 'chapter'}-P${page.pageNo}`,
    pageNo: page.pageNo,
    pageTitle: page.pageTitle || `第 ${page.pageNo} 页`,
    pageSummary: page.pageSummary || '',
    imageUrl: page.imageUrl || page.pptPageUrl || '',
    parsedContent: page.parsedContent || page.pageSummary || '',
    anchorId: '',
    anchorTitle: chapter?.chapterTitle || '',
    isRead: false
  }))

  return {
    lessonId: lesson?.lessonId || lessonId.value,
    lessonDbId: '',
    courseName: lesson?.courseName || '',
    teacherName: lesson?.teacherName || '',
    unitTitle: locatedUnit?.unitTitle || '知识学习',
    sectionId: sectionId.value || chapter?.chapterId || '',
    sectionTitle: chapter?.chapterTitle || '章节学习',
    progressPercent: Number(chapter?.progressPercent || 0),
    masteryPercent: Number(chapter?.masteryPercent || 0),
    aiGuideContent: chapter?.guideContent || chapter?.summary || '',
    scriptContent: chapter?.guideContent || chapter?.summary || '',
    audioUrl: '',
    audioStatus: 'empty',
    knowledgePoints: chapter?.knowledgePoints || [],
    pages: fallbackPages,
    currentPageNo: fallbackPages[0]?.pageNo || 1
  }
}

function setThumbnailRef(pageNo, element) {
  if (!element) {
    delete thumbnailRefs.value[pageNo]
    return
  }
  thumbnailRefs.value[pageNo] = element
}

function keepThumbnailVisible() {
  const container = thumbnailRailRef.value
  const target = thumbnailRefs.value[activePageNo.value]
  if (!container || !target) return
  const top = target.offsetTop
  const bottom = top + target.offsetHeight
  const currentTop = container.scrollTop
  const currentBottom = currentTop + container.clientHeight
  const gap = 10

  if (top - gap < currentTop) {
    container.scrollTo({ top: Math.max(0, top - gap), behavior: 'smooth' })
    return
  }
  if (bottom + gap > currentBottom) {
    container.scrollTo({ top: bottom - container.clientHeight + gap, behavior: 'smooth' })
  }
}

async function loadSectionDetail() {
  sectionAudioRef.value?.pause()
  if (sectionAudioRef.value) {
    sectionAudioRef.value.currentTime = 0
  }
  isAudioPlaying.value = false
  const fallback = normalizeFallbackDetail()
  detail.value = fallback
  activePageNo.value = restorePageNo.value || fallback.currentPageNo || 1

  if (!sectionId.value) return

  try {
    const res = await getStudentSectionDetail({
      studentId: studentProfile.value.studentId,
      lessonId: lessonId.value,
      sectionId: sectionId.value
    })
    detail.value = {
      ...fallback,
      ...(res.data || {})
    }
    const firstPageNo = Number(detail.value.pages?.[0]?.pageNo || 1)
    const targetPageNo = Number(restorePageNo.value || detail.value.currentPageNo || firstPageNo)
    const hasTargetPage = (detail.value.pages || []).some((page) => Number(page.pageNo) === targetPageNo)
    activePageNo.value = hasTargetPage ? targetPageNo : firstPageNo
  } catch (error) {
    ElMessage.warning(error?.msg || '知识学习内容加载失败，已切换为本地演示数据')
  } finally {
    await nextTick()
    keepThumbnailVisible()
  }
}

async function syncPageRead(page) {
  if (!page || page.isRead || !sectionId.value) return
  try {
    const res = await markStudentPageRead({
      studentId: studentProfile.value.studentId,
      lessonId: lessonId.value,
      sectionId: sectionId.value,
      lessonPageId: page.lessonPageId,
      pageNo: page.pageNo
    })
    page.isRead = true
    detail.value.progressPercent = res.data.progressPercent
    detail.value.masteryPercent = res.data.masteryPercent
  } catch (error) {
    console.warn(error)
  }
}

function setActivePage(pageNo) {
  if (!pageNo || pageNo === activePageNo.value) return
  activePageNo.value = Number(pageNo)
}

function goPrevPage() {
  if (!hasPrevPage.value) return
  activePageNo.value -= 1
}

function goNextPage() {
  if (!hasNextPage.value) return
  activePageNo.value += 1
}

async function toggleViewerFullscreen() {
  const target = viewerShellRef.value
  if (!target) return
  if (document.fullscreenElement === target) {
    await document.exitFullscreen()
    return
  }
  if (target.requestFullscreen) {
    await target.requestFullscreen()
  }
}

function fillQuestion(question) {
  questionText.value = question
}

async function toggleSectionAudio() {
  if (!detail.value.audioUrl || detail.value.audioStatus !== 'published') {
    ElMessage.info('当前章节暂无语音。')
    return
  }

  const audio = sectionAudioRef.value
  if (!audio) return

  try {
    if (audio.paused) {
      await audio.play()
    } else {
      audio.pause()
    }
  } catch (_error) {
    ElMessage.warning('语音播放失败，请稍后重试。')
  }
}


function persistRecentVisit() {
  if (!lessonId.value || !chapterId.value || !sectionId.value) return
  saveStudentRecentChapter({
    studentId: studentProfile.value.studentId,
    lessonId: lessonId.value,
    sectionId: sectionId.value,
    pageNo: activePageNo.value || 1
  }).catch(() => {
    console.warn('save recent chapter visit failed')
  })
}

async function submitQuestion() {
  const question = questionText.value.trim()
  if (!question || asking.value) return

  const page = activePage.value
  chatList.value.push({
    id: `user-${Date.now()}`,
    role: 'user',
    content: question
  })
  questionText.value = ''
  asking.value = true

  try {
    const res = await interactWithLesson({
      studentId: studentProfile.value.studentId,
      lessonId: lessonId.value,
      sectionId: sectionId.value,
      anchorId: page?.anchorId || '',
      question
    })
    chatList.value.push({
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: res.data.answer || '当前内容暂无更多解读。'
    })
  } catch (error) {
    ElMessage.error(error?.msg || 'AI 问答失败')
  } finally {
    asking.value = false
    await nextTick()
    chatScrollRef.value?.scrollTo({ top: chatScrollRef.value.scrollHeight, behavior: 'smooth' })
  }
}

function goBack() {
  sectionAudioRef.value?.pause()
  persistRecentVisit()
  router.push({
    name: 'StudentPlayer',
    params: { lessonId: lessonId.value },
    query: route.query.token ? { token: route.query.token } : {}
  })
}

function goStudentHome() {
  sectionAudioRef.value?.pause()
  persistRecentVisit()
  router.push({
    name: 'StudentHome',
    query: route.query.token ? { token: route.query.token } : {}
  })
}

watch(activePageNo, async () => {
  await nextTick()
  keepThumbnailVisible()
  if (activePage.value) {
    syncPageRead(activePage.value)
  }
})

onMounted(async () => {
  window.addEventListener('pagehide', persistRecentVisit)
  await loadSectionDetail()
  if (activePage.value) {
    syncPageRead(activePage.value)
  }
})

onBeforeUnmount(() => {
  sectionAudioRef.value?.pause()
  window.removeEventListener('pagehide', persistRecentVisit)
  persistRecentVisit()
})

onBeforeRouteLeave(() => {
  sectionAudioRef.value?.pause()
  persistRecentVisit()
})
</script>

<style scoped>
.knowledge-page {
  height: 100vh;
  background: #ffffff;
  color: #17305e;
  overflow: hidden;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.knowledge-page::-webkit-scrollbar {
  display: none;
}

.knowledge-topbar {
  height: 84px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.98);
  border-bottom: 1px solid #e4ebf8;
  box-shadow: 0 10px 24px rgba(17, 34, 78, 0.05);
}

.knowledge-brand {
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
}

.knowledge-brand:focus-visible {
  outline: 2px solid rgba(82, 126, 246, 0.45);
  outline-offset: 6px;
  border-radius: 16px;
}

.knowledge-brand-mark {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: linear-gradient(135deg, #ea4a3d 0%, #e73a32 100%);
}

.knowledge-brand-name {
  font-size: 22px;
  font-weight: 700;
  color: #1a2f57;
}

.knowledge-back-button {
  border-radius: 14px;
  padding: 0 16px;
  height: 38px;
  font-size: 14px;
}

.knowledge-workspace {
  height: calc(100vh - 84px);
  max-width: 1332px;
  margin: 0 auto;
  padding: 6px 14px 14px;
  display: grid;
  grid-template-columns: minmax(0, 1.48fr) minmax(320px, 0.8fr);
  gap: 14px;
  overflow: hidden;
  align-items: stretch;
  background: #ffffff;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.knowledge-workspace::-webkit-scrollbar {
  display: none;
}

.knowledge-left {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
  overscroll-behavior: contain;
  background: #ffffff;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.knowledge-left::-webkit-scrollbar {
  display: none;
}

.knowledge-summary-card,
.ppt-card,
.guide-card,
.ai-card {
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid #dbe5f7;
  border-radius: 24px;
  box-shadow: 0 16px 38px rgba(64, 92, 168, 0.08);
}

.knowledge-summary-card {
  padding: 10px 16px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  background: linear-gradient(135deg, #eff5ff 0%, #dbe9ff 100%);
}

.knowledge-summary-main h1 {
  margin: 0;
  font-size: 23px;
  line-height: 1.1;
}

.knowledge-summary-stats {
  display: flex;
  gap: 8px;
}

.knowledge-summary-stat {
  width: 164px;
  min-height: 100px;
  border-radius: 20px;
  border: 1px solid #cadeff;
  background: rgba(255, 255, 255, 0.8);
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 4px;
}

.knowledge-summary-stat span {
  font-size: 14px;
  line-height: 1;
  color: #6f86b1;
  font-weight: 600;
  width: 100%;
  text-align: left;
}

.knowledge-summary-stat strong {
  font-size: 34px;
  color: #21427a;
  width: 100%;
  text-align: right;
}

.ppt-card {
  flex: 0 0 auto;
  padding: 8px 10px 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #ffffff;
}

.ppt-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  gap: 12px;
}

.ppt-card-title {
  font-size: 21px;
  font-weight: 700;
}

.ppt-card-subtitle {
  margin-top: 2px;
  color: #6f86b1;
  font-size: 14px;
}

.ppt-audio-button {
  flex: 0 0 auto;
  height: 36px;
  padding: 0 16px;
  border: 1px solid #cad8f4;
  border-radius: 14px;
  background: linear-gradient(135deg, #f7fbff 0%, #edf4ff 100%);
  color: #33548f;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease, color 0.18s ease;
}

.ppt-audio-button:hover:not(:disabled) {
  border-color: #7e9de0;
  background: linear-gradient(135deg, #edf4ff 0%, #e5efff 100%);
}

.ppt-audio-button:disabled {
  opacity: 0.58;
  cursor: not-allowed;
}

.ppt-card-body {
  height: clamp(414px, 50vh, 576px);
  flex: 0 0 auto;
  display: grid;
  grid-template-columns: 132px minmax(0, 1fr);
  gap: 0;
  overflow: hidden;
  align-items: stretch;
  border: 3px solid #989eb0;
  border-radius: 22px;
  background: #eaf2ff;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.74);
}

.thumbnail-rail {
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overscroll-behavior: contain;
  scrollbar-width: none;
  -ms-overflow-style: none;
  border-right: 2px solid #6f7686;
  background: #eaf2ff;
}

.thumbnail-rail::-webkit-scrollbar {
  display: none;
}

.thumbnail-card {
  border: none;
  border-radius: 10px;
  background: transparent;
  padding: 0;
  display: block;
  cursor: pointer;
  transition: 0.2s ease;
}

.thumbnail-card:hover {
  transform: translateY(-1px);
}

.thumbnail-card.active .thumbnail-media {
  box-shadow: 0 0 0 3px rgba(109, 130, 244, 0.22);
}

.thumbnail-media {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 11;
  border-radius: 10px;
  background: #f7faff;
  overflow: hidden;
}

.thumbnail-card img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 10px;
  display: block;
}

.thumbnail-page-badge {
  position: absolute;
  left: 6px;
  bottom: 6px;
  min-width: 22px;
  height: 18px;
  padding: 0 6px;
  border-radius: 7px;
  background: rgba(132, 139, 171, 0.92);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
}

.viewer-shell {
  min-width: 0;
  height: 100%;
  min-height: 0;
  padding: 8px 8px 8px 12px;
  overflow: hidden;
  background: #eaf2ff;
}

.viewer-stage {
  height: 100%;
  width: 100%;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #eaf2ff;
  overflow: hidden;
  padding: 14px 14px 56px;
  box-sizing: border-box;
}

.viewer-slide {
  width: 100%;
  height: 100%;
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  object-position: center;
  display: block;
}

.viewer-empty {
  color: #7f92ba;
  font-size: 14px;
}

.viewer-toolbar {
  position: absolute;
  left: 50%;
  bottom: 10px;
  transform: translateX(-50%);
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 8px;
  border-radius: 999px;
  background: rgba(42, 46, 58, 0.92);
  box-shadow: none;
}

.viewer-tool-button {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  display: grid;
  place-items: center;
  cursor: pointer;
}

.viewer-tool-button:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.viewer-tool-button svg {
  width: 13px;
  height: 13px;
}

.viewer-page-indicator {
  min-width: 80px;
  height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 700;
}

.section-audio {
  display: none;
}

.guide-card {
  flex: 0 0 auto;
  padding: 14px 18px;
  background: #ffffff;
}

.guide-card-head h2 {
  margin: 0 0 10px;
  font-size: 21px;
}

.guide-card-body {
  color: #51698f;
  line-height: 1.75;
  font-size: 14px;
}

.knowledge-right {
  min-height: 0;
  height: 100%;
  display: flex;
  position: relative;
}

.ai-card {
  min-height: 0;
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 16px;
  overflow: hidden;
  position: sticky;
  top: 0;
  background: #ffffff;
}

.ai-card-head {
  flex: 0 0 auto;
  padding-bottom: 10px;
}

.ai-card-head h2 {
  margin: 0;
  font-size: 21px;
}

.ai-quick-questions {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  align-content: flex-start;
  margin-top: 20px;
}

.ai-welcome-spacer {
  flex: 1 1 auto;
  min-height: 24px;
}

.ai-chip {
  border: 1px solid #d3e0f8;
  border-radius: 999px;
  background: #f7faff;
  color: #3c5ea2;
  padding: 9px 13px;
  cursor: pointer;
  font-size: 13px;
}

.ai-chat-list {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  margin-top: 10px;
  padding-right: 4px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.ai-chat-list::-webkit-scrollbar {
  display: none;
}

.ai-message {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ai-message-role {
  font-size: 12px;
  color: #7c90b6;
}

.ai-message.user .ai-message-role {
  align-self: flex-end;
  text-align: right;
}

.ai-message-bubble {
  max-width: min(100%, 420px);
  border-radius: 20px;
  padding: 12px 14px;
  line-height: 1.7;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.ai-message.user .ai-message-bubble {
  align-self: flex-end;
  background: linear-gradient(135deg, #5880ef 0%, #6f8fff 100%);
  color: #fff;
}

.ai-message.assistant .ai-message-bubble {
  background: #f3f7ff;
  color: #315186;
  border: 1px solid #dde7f8;
}

.ai-input-box {
  flex: 0 0 15%;
  min-height: 120px;
  border-radius: 22px;
  border: 1px solid #dbe4f4;
  background: linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%);
  padding: 12px;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  margin-top: 0;
}

.ai-textarea {
  width: 100%;
  height: 100%;
  resize: none;
  overflow-y: auto;
  border: none;
  outline: none;
  background: transparent;
  color: #17305e;
  font-size: 14px;
  line-height: 1.6;
  min-height: 0;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.ai-textarea::-webkit-scrollbar {
  display: none;
}

.ai-textarea::placeholder {
  color: #97a7c6;
  font-size: 14px;
}

.ai-input-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-top: 8px;
}

.ai-send-button {
  height: 36px;
  padding: 0 14px;
  border: none;
  border-radius: 16px;
  background: linear-gradient(135deg, #557cf0 0%, #6c8aff 100%);
  color: #fff;
  font-weight: 700;
  cursor: pointer;
  font-size: 13px;
}

.ai-send-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 1260px) {
  .knowledge-workspace {
    grid-template-columns: 1fr;
    overflow-y: auto;
    height: calc(100vh - 84px);
  }

  .knowledge-left {
    min-height: 0;
    overflow: visible;
    padding-right: 0;
  }

  .knowledge-right {
    min-height: 680px;
  }

  .ai-card {
    position: static;
  }
}

@media (max-width: 920px) {
  .knowledge-page {
    overflow: auto;
    height: auto;
    min-height: 100vh;
  }

  .knowledge-topbar {
    padding: 0 18px;
  }

  .knowledge-workspace {
    height: auto;
    overflow: visible;
    padding: 14px;
  }

  .knowledge-left {
    overflow: visible;
  }

  .knowledge-summary-card {
    flex-direction: column;
    align-items: stretch;
  }

  .knowledge-summary-stats {
    width: 100%;
  }

  .knowledge-summary-stat {
    width: 100%;
  }

  .knowledge-summary-stat span {
    font-size: 12px;
  }

  .ppt-card-body {
    height: auto;
    min-height: 340px;
    grid-template-columns: 1fr;
  }

  .viewer-shell {
    min-height: 340px;
    padding: 10px;
  }

  .thumbnail-rail {
    max-height: 200px;
    flex-direction: row;
    overflow-x: auto;
    overflow-y: hidden;
    padding: 10px;
    border-right: 0;
    border-bottom: 2px solid #6f7686;
  }

  .thumbnail-card {
    min-width: 136px;
  }
}
</style>
