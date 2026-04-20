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
        <img class="knowledge-brand-mark" src="/chaoxing-erya-logo.svg" alt="超星尔雅" />
        <div class="knowledge-brand-name">尔雅</div>
      </div>
      <el-button class="knowledge-back-button" plain @click="goBack">返回课程详情</el-button>
    </header>

    <main class="knowledge-workspace">
      <section ref="knowledgeLeftRef" class="knowledge-left app-scrollable">
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
              <div class="ppt-card-title">课件学习</div>
              <div class="ppt-card-subtitle">当前页 {{ activePageNo }} / {{ totalPages }}</div>
            </div>
            <button
              type="button"
              class="ppt-audio-button"
              :disabled="!canPlaySectionAudio"
              @click="toggleSectionAudio"
            >
              {{ audioActionLabel }}
            </button>
          </div>

          <div class="ppt-audio-panel" :class="{ disabled: !canPlaySectionAudio }">
            <div class="ppt-audio-meta">
              <span class="ppt-audio-status">{{ audioStatusLabel }}</span>
              <span v-if="audioError" class="ppt-audio-error">{{ audioError }}</span>
            </div>
            <div class="ppt-audio-progress-row">
              <span class="ppt-audio-time">{{ audioCurrentLabel }}</span>
              <input
                class="ppt-audio-slider"
                type="range"
                min="0"
                :max="audioSliderMax"
                :value="Math.min(audioCurrentTime, audioSliderMax)"
                :disabled="!canPlaySectionAudio"
                step="0.1"
                aria-label="章节音频播放进度"
                @input="handleAudioSeekInput"
                @change="handleAudioSeekChange"
              />
              <span class="ppt-audio-time">{{ audioDurationLabel }}</span>
            </div>
          </div>

          <div class="ppt-card-body">
            <aside ref="thumbnailRailRef" class="thumbnail-rail app-scrollable">
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
                  <img v-if="page.imageUrl" :src="page.imageUrl" :alt="`第 ${page.pageNo} 页缩略图`" loading="lazy" />
                  <div v-else class="thumbnail-fallback">
                    <strong>{{ page.pageNo }}</strong>
                    <span>{{ page.pageTitle || `第 ${page.pageNo} 页` }}</span>
                  </div>
                  <span class="thumbnail-page-badge">{{ page.pageNo }}</span>
                </div>
              </button>
            </aside>

            <div ref="viewerShellRef" class="viewer-shell">
              <div class="viewer-stage">
                <img
                  v-if="activePage?.imageUrl"
                  class="viewer-slide"
                  :src="activePage.imageUrl"
                  :alt="`第 ${activePage.pageNo} 页幻灯片`"
                />
                <div v-else-if="activePage" class="viewer-image-missing">
                  <div class="viewer-image-missing-title">{{ activePage.pageTitle || `第 ${activePage.pageNo} 页` }}</div>
                  <div class="viewer-image-missing-desc">当前页缺少 PPT 预览图，请先检查发布链路是否写入了图片地址。</div>
                </div>
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
            @loadedmetadata="handleAudioLoadedMetadata"
            @timeupdate="handleAudioTimeUpdate"
            @canplay="handleAudioCanPlay"
            @waiting="handleAudioWaiting"
            @play="handleAudioPlay"
            @pause="handleAudioPause"
            @ended="handleAudioEnded"
            @error="handleAudioError"
          ></audio>

          <div class="ppt-card-footer">
            <button
              type="button"
              class="ppt-next-section-button"
              :disabled="!nextChapter"
              @click="goNextSection"
            >
              {{ nextChapter ? '下一节' : '已是最后一节' }}
            </button>
          </div>
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
        <section class="ai-card" :class="{ 'has-chat': chatList.length > 0 }" @click="pauseSectionAudioIfPlaying">
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

          <div v-else ref="chatScrollRef" class="ai-chat-list app-scrollable">
            <article
              v-for="message in chatList"
              :key="message.id"
              class="ai-message"
              :class="message.role"
            >
              <div class="ai-message-role">{{ message.role === 'user' ? '我' : 'AI 学伴' }}</div>
              <div class="ai-message-bubble">{{ message.content }}</div>
            </article>
            <article v-if="asking && !assistantStreamingStarted" class="ai-message assistant pending">
              <div class="ai-message-role">AI 学伴</div>
              <div class="ai-message-loading">
                <span class="ai-inline-loading" aria-hidden="true"></span>
              </div>
            </article>
          </div>

          <form class="ai-input-box" @submit.prevent="submitQuestion">
            <textarea
              v-model="questionText"
              class="ai-textarea app-scrollable"
              placeholder="输入你的问题"
              rows="3"
              @keydown.enter.exact.prevent="submitQuestion"
            ></textarea>
            <div class="ai-input-actions">
              <div v-if="isRecording" class="ai-voice-status">
                <span class="ai-voice-timer">{{ formatRecordingDuration(recordingSeconds) }}</span>
                <button
                  type="button"
                  class="ai-icon-button voice stop"
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
                class="ai-icon-button voice"
                :class="{ loading: voiceLoading }"
                :disabled="voiceLoading"
                :aria-label="voiceLoading ? '语音识别中' : '语音输入'"
                @click="!voiceLoading ? toggleRecording() : undefined"
              >
                <span v-if="voiceLoading" class="ai-inline-loading" aria-hidden="true"></span>
                <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 3.5a2.5 2.5 0 0 1 2.5 2.5v5a2.5 2.5 0 0 1-5 0V6A2.5 2.5 0 0 1 12 3.5Z" />
                  <path d="M7.5 10.5a4.5 4.5 0 0 0 9 0" />
                  <path d="M12 15v5" />
                  <path d="M9 20.5h6" />
                </svg>
              </button>
              <button
                type="button"
                class="ai-icon-button send"
                :class="{ 'is-stop': asking }"
                :disabled="!asking && !questionText.trim()"
                :aria-label="asking ? '终止回答' : '发送问题'"
                @click.prevent="asking ? stopStreamingAnswer() : submitQuestion()"
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
          </form>
        </section>
      </aside>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useRealtimeAsr } from '@/composables/useRealtimeAsr'
import { streamLessonInteraction } from '@/api/studentStream'
import {
  getStudentSectionDetail,
  markStudentPageRead,
  saveStudentRecentChapter
} from '@/api/student'
import { findFrontendTestLesson } from '@/mock/studentLessons'
import { getStudentLessonListCache, getStudentProfile, getStudentViewState, saveStudentViewState } from '@/utils/platform'
import { findAggregatedChapterForSection } from '@/utils/studentKnowledge'

const router = useRouter()
const route = useRoute()
const knowledgeLeftRef = ref(null)

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
const activeAnswerController = ref(null)
const voiceDraftPrefix = ref('')
const assistantStreamingStarted = ref(false)
const isAudioPlaying = ref(false)
const audioCurrentTime = ref(0)
const audioDuration = ref(0)
const audioPending = ref(false)
const audioError = ref('')
const audioShouldNotifyError = ref(false)
const audioSeeking = ref(false)
const thumbnailRailRef = ref(null)
const viewerShellRef = ref(null)
const chatScrollRef = ref(null)
const sectionAudioRef = ref(null)
const thumbnailRefs = ref({})
const hasLoadedDetail = ref(false)
const hasActivatedOnce = ref(false)
const isKnowledgeViewActive = ref(false)
let sectionDetailLoadSeq = 0

const routeLessonId = computed(() => String(route.params.lessonId || ''))
const routeSectionId = computed(() => String(route.params.sectionId || ''))
const isSlideRoute = computed(() => route.name === 'StudentSlideLearning')
const lessonId = computed(() => routeLessonId.value || String(detail.value.lessonId || ''))
const chapterId = computed(() => String(route.query.chapterId || ''))
const routeUnitId = computed(() => String(route.query.unitId || ''))
const knowledgeChapterId = computed(() => String(route.query.knowledgeChapterId || ''))
const restorePageNo = computed(() => Number(route.query.pageNo || 0))
const sectionId = computed(() => routeSectionId.value || String(detail.value.sectionId || ''))
const pages = computed(() => detail.value.pages || [])
const totalPages = computed(() => pages.value.length)
const activePage = computed(() => pages.value.find((page) => Number(page.pageNo) === Number(activePageNo.value)) || pages.value[0] || null)
const hasPrevPage = computed(() => activePageNo.value > 1)
const hasNextPage = computed(() => activePageNo.value < totalPages.value)
const lessonUnits = computed(() => {
  const cachedLesson = getStudentLessonListCache().find((item) => String(item.lessonId) === String(lessonId.value))
    || findFrontendTestLesson(lessonId.value)
  return cachedLesson?.units || []
})
const lessonChapters = computed(() => lessonUnits.value.flatMap((unit) => unit.chapters || []))
const currentChapterIndex = computed(() => lessonChapters.value.findIndex((chapter) => {
  if (chapterId.value && String(chapter.chapterId || '') === chapterId.value) return true
  if (sectionId.value && String(chapter.sectionId || '') === sectionId.value) return true
  return String(chapter.chapterTitle || '') === String(detail.value.sectionTitle || '')
}))
const nextChapter = computed(() => {
  if (currentChapterIndex.value < 0) return null
  return lessonChapters.value[currentChapterIndex.value + 1] || null
})
const canPlaySectionAudio = computed(() => Boolean(detail.value.audioUrl) && detail.value.audioStatus === 'published')
const audioSliderMax = computed(() => Math.max(Number(audioDuration.value || 0), 1))
const audioCurrentLabel = computed(() => formatAudioTime(audioCurrentTime.value))
const audioDurationLabel = computed(() => formatAudioTime(audioDuration.value))
const audioActionLabel = computed(() => (isAudioPlaying.value ? '暂停播放' : '语音播放'))
const audioStatusLabel = computed(() => {
  if (!detail.value.audioUrl) return '当前章节暂无讲解音频'
  if (detail.value.audioStatus && detail.value.audioStatus !== 'published') return '讲解音频待发布'
  if (audioError.value) return '音频播放异常'
  if (audioPending.value) return '音频加载中...'
  if (isAudioPlaying.value) return '正在播放讲解音频'
  if (audioCurrentTime.value > 0) return '已暂停，可继续播放'
  return '讲解音频已就绪'
})
const quickQuestions = computed(() => {
  const title = detail.value.sectionTitle || '当前章节'
  return [
    `帮我概括《${title}》的重点`,
    `《${title}》里的核心公式之间有什么关系`,
    `《${title}》在工程里通常怎么应用`
  ]
})
const { isRecording, voiceLoading, recordingSeconds, toggleRecording, cleanupRealtimeAsr } = useRealtimeAsr({
  getContext: () => ({
    studentId: studentProfile.value.studentId,
    lessonId: lessonId.value,
    sectionId: sectionId.value || detail.value.sectionId || ''
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

function formatAudioTime(totalSeconds) {
  const safeSeconds = Math.max(0, Math.floor(Number(totalSeconds || 0)))
  const hours = Math.floor(safeSeconds / 3600)
  const minutes = Math.floor((safeSeconds % 3600) / 60)
  const seconds = safeSeconds % 60
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
  }
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

function resetSectionAudioState() {
  audioCurrentTime.value = 0
  audioDuration.value = 0
  audioPending.value = false
  audioError.value = ''
  audioShouldNotifyError.value = false
  audioSeeking.value = false
  isAudioPlaying.value = false
}

function stopSectionAudio() {
  const audio = sectionAudioRef.value
  if (audio) {
    audio.pause()
    audio.currentTime = 0
  }
  resetSectionAudioState()
}

function pauseSectionAudioIfPlaying() {
  const audio = sectionAudioRef.value
  if (!audio || audio.paused) return
  audioShouldNotifyError.value = false
  audio.pause()
}

function handleAudioLoadedMetadata() {
  const audio = sectionAudioRef.value
  if (!audio) return
  audioDuration.value = Number.isFinite(audio.duration) ? audio.duration : 0
  audioCurrentTime.value = Number.isFinite(audio.currentTime) ? audio.currentTime : 0
}

function handleAudioTimeUpdate() {
  const audio = sectionAudioRef.value
  if (!audio || audioSeeking.value) return
  audioCurrentTime.value = Number.isFinite(audio.currentTime) ? audio.currentTime : 0
  if (Number.isFinite(audio.duration)) {
    audioDuration.value = audio.duration
  }
}

function handleAudioCanPlay() {
  audioPending.value = false
  audioError.value = ''
}

function handleAudioWaiting() {
  audioPending.value = true
}

function handleAudioPlay() {
  isAudioPlaying.value = true
  audioPending.value = false
  audioError.value = ''
}

function handleAudioPause() {
  isAudioPlaying.value = false
  audioPending.value = false
  audioShouldNotifyError.value = false
}

function handleAudioEnded() {
  isAudioPlaying.value = false
  audioPending.value = false
  audioCurrentTime.value = audioDuration.value
  audioShouldNotifyError.value = false
}

function resolveAudioErrorMessage() {
  const code = sectionAudioRef.value?.error?.code
  if (code === 2) {
    return '讲解音频加载失败，请稍后重试。'
  }
  if (code === 3) {
    return '讲解音频解析失败，请稍后重试。'
  }
  if (code === 4) {
    return '讲解音频地址不可用，请联系老师重新发布。'
  }
  return '讲解音频暂时无法播放，请稍后重试。'
}

function handleAudioError() {
  const shouldSurfaceError = audioShouldNotifyError.value
    || Boolean(audioPending.value)
    || Boolean(isAudioPlaying.value)
  isAudioPlaying.value = false
  audioPending.value = false
  if (!detail.value.audioUrl) {
    audioError.value = ''
    audioShouldNotifyError.value = false
    return
  }
  if (!shouldSurfaceError) {
    audioError.value = ''
    audioShouldNotifyError.value = false
    return
  }
  const message = resolveAudioErrorMessage()
  audioError.value = message
  if (audioShouldNotifyError.value) {
    ElMessage.warning(message)
  }
  audioShouldNotifyError.value = false
}

function handleAudioSeekInput(event) {
  audioSeeking.value = true
  audioCurrentTime.value = Number(event?.target?.value || 0)
}

function handleAudioSeekChange(event) {
  const audio = sectionAudioRef.value
  const nextTime = Number(event?.target?.value || 0)
  if (audio) {
    audio.currentTime = nextTime
  }
  audioCurrentTime.value = nextTime
  audioSeeking.value = false
}

function normalizeFallbackDetail() {
  const lesson = findFrontendTestLesson(lessonId.value)
  const allUnits = lesson?.units || []
  const locatedUnit = allUnits.find((unit) => (unit.chapters || []).some((chapter) => chapter.sectionId === sectionId.value))
    || allUnits.find((unit) => (unit.chapters || []).some((chapter) => chapter.chapterId === chapterId.value))
    || allUnits[0]
  const chapter = (locatedUnit?.chapters || []).find((item) => item.sectionId === sectionId.value)
    || (locatedUnit?.chapters || []).find((item) => item.chapterId === chapterId.value)
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
    sectionId: sectionId.value || '',
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

function captureKnowledgeViewState() {
  const lessonViewState = getStudentViewState(lessonId.value)
  const knowledgeState = { ...(lessonViewState.knowledge || {}) }
  knowledgeState[sectionId.value || chapterId.value || 'default'] = {
    activePageNo: activePageNo.value,
    scrollTop: knowledgeLeftRef.value?.scrollTop || 0
  }
  saveStudentViewState(lessonId.value, { knowledge: knowledgeState })
}

function handleKnowledgeScroll() {
  captureKnowledgeViewState()
}

async function restoreKnowledgeViewState() {
  const lessonViewState = getStudentViewState(lessonId.value)
  const stored = lessonViewState.knowledge?.[sectionId.value || chapterId.value || 'default'] || {}
  if (stored.activePageNo && !restorePageNo.value) {
    activePageNo.value = Number(stored.activePageNo)
  }
  await nextTick()
  if (knowledgeLeftRef.value && Number.isFinite(Number(stored.scrollTop))) {
    knowledgeLeftRef.value.scrollTop = Number(stored.scrollTop || 0)
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

function canLoadSectionDetail(targetLessonId = routeLessonId.value, targetSectionId = routeSectionId.value) {
  return isKnowledgeViewActive.value && isSlideRoute.value && Boolean(targetLessonId) && Boolean(targetSectionId)
}

async function loadSectionDetail() {
  const targetLessonId = routeLessonId.value
  const targetSectionId = routeSectionId.value
  if (!canLoadSectionDetail(targetLessonId, targetSectionId)) return
  const loadSeq = ++sectionDetailLoadSeq
  stopSectionAudio()
  const fallback = normalizeFallbackDetail()
  detail.value = fallback
  activePageNo.value = restorePageNo.value || fallback.currentPageNo || 1

  try {
    const res = await getStudentSectionDetail({
      studentId: studentProfile.value.studentId,
      lessonId: targetLessonId,
      sectionId: targetSectionId
    })
    if (
      loadSeq !== sectionDetailLoadSeq
      || !canLoadSectionDetail(targetLessonId, targetSectionId)
      || targetLessonId !== routeLessonId.value
      || targetSectionId !== routeSectionId.value
    ) {
      return
    }
    detail.value = {
      ...fallback,
      ...(res.data || {})
    }
    if (detail.value.audioUrl) {
      detail.value.audioStatus = detail.value.audioStatus || 'published'
    } else {
      detail.value.audioStatus = 'empty'
    }
    const firstPageNo = Number(detail.value.pages?.[0]?.pageNo || 1)
    const targetPageNo = Number(restorePageNo.value || detail.value.currentPageNo || firstPageNo)
    const hasTargetPage = (detail.value.pages || []).some((page) => Number(page.pageNo) === targetPageNo)
    activePageNo.value = hasTargetPage ? targetPageNo : firstPageNo
  } catch (error) {
    if (!error?.handled) {
      ElMessage.warning(error?.msg || '知识学习内容加载失败，已切换为本地演示数据')
    }
  } finally {
    hasLoadedDetail.value = true
    await nextTick()
    keepThumbnailVisible()
    await restoreKnowledgeViewState()
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

async function goNextSection() {
  if (!nextChapter.value) return
  persistRecentVisit()
  const aggregatedChapter = findAggregatedChapterForSection(lessonUnits.value, nextChapter.value.sectionId || '')
  await router.push({
    name: 'StudentSlideLearning',
    params: {
      lessonId: lessonId.value,
      sectionId: nextChapter.value.sectionId || sectionId.value || ''
    },
    query: {
      ...(route.query.token ? { token: route.query.token } : {}),
      ...(nextChapter.value.chapterId ? { chapterId: nextChapter.value.chapterId } : {}),
      ...(aggregatedChapter?.unitId ? { unitId: aggregatedChapter.unitId } : {}),
      ...(aggregatedChapter?.chapterId ? { knowledgeChapterId: aggregatedChapter.chapterId } : {}),
      pageNo: String(nextChapter.value.pageNo || 1)
    }
  })
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
  if (!canPlaySectionAudio.value) {
    ElMessage.info('当前章节暂无语音。')
    return
  }

  const audio = sectionAudioRef.value
  if (!audio) return

  try {
    if (audio.paused) {
      audioPending.value = true
      audioError.value = ''
      audioShouldNotifyError.value = true
      await audio.play()
    } else {
      audioShouldNotifyError.value = false
      audio.pause()
    }
  } catch (error) {
    audioPending.value = false
    audioShouldNotifyError.value = false
    if (error?.name === 'AbortError') return
    if (!audio.error) {
      const message = resolveAudioErrorMessage()
      audioError.value = message
      ElMessage.warning(message)
    }
  }
}


function persistRecentVisit() {
  if (!lessonId.value || !sectionId.value) return
  captureKnowledgeViewState()
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
  const assistantMessage = {
    id: `assistant-${Date.now()}`,
    role: 'assistant',
    content: ''
  }
  let assistantInserted = false
  chatList.value.push({
    id: `user-${Date.now()}`,
    role: 'user',
    content: question
  })
  questionText.value = ''
  asking.value = true
  assistantStreamingStarted.value = false
  const controller = new AbortController()
  activeAnswerController.value = controller

  function ensureAssistantVisible() {
    if (assistantInserted) return
    assistantInserted = true
    chatList.value.push(assistantMessage)
  }

  try {
    const donePayload = await streamLessonInteraction({
      studentId: studentProfile.value.studentId,
      lessonId: lessonId.value,
      sectionId: sectionId.value,
      anchorId: page?.anchorId || '',
      pageNo: page?.pageNo || activePageNo.value,
      question
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
  } catch (error) {
    if (error?.name === 'AbortError') {
      assistantStreamingStarted.value = true
      ensureAssistantVisible()
      assistantMessage.content = assistantMessage.content || '已终止本次回答。'
    } else {
      ElMessage.error(error?.message || error?.msg || 'AI 问答失败')
    }
  } finally {
    asking.value = false
    assistantStreamingStarted.value = false
    activeAnswerController.value = null
    await nextTick()
    chatScrollRef.value?.scrollTo({ top: chatScrollRef.value.scrollHeight, behavior: 'smooth' })
  }
}

function stopStreamingAnswer() {
  activeAnswerController.value?.abort()
}

function goBack() {
  stopSectionAudio()
  persistRecentVisit()
  const aggregatedChapter = (
    routeUnitId.value && knowledgeChapterId.value
      ? {
          unitId: routeUnitId.value,
          chapterId: knowledgeChapterId.value
        }
      : findAggregatedChapterForSection(lessonUnits.value, sectionId.value || detail.value.sectionId || '')
  )
  if (aggregatedChapter?.unitId && aggregatedChapter?.chapterId) {
    router.push({
      name: 'StudentKnowledgeLearning',
      params: {
        lessonId: lessonId.value,
        unitId: aggregatedChapter.unitId,
        chapterId: aggregatedChapter.chapterId
      },
      query: route.query.token ? { token: route.query.token } : {}
    })
    return
  }
  router.push({
    name: 'StudentPlayer',
    params: { lessonId: lessonId.value },
    query: route.query.token ? { token: route.query.token } : {}
  })
}

function goStudentHome() {
  stopSectionAudio()
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
  captureKnowledgeViewState()
})

onMounted(async () => {
  isKnowledgeViewActive.value = true
  window.addEventListener('pagehide', persistRecentVisit)
  knowledgeLeftRef.value?.addEventListener('scroll', handleKnowledgeScroll, { passive: true })
  await loadSectionDetail()
  if (activePage.value) {
    syncPageRead(activePage.value)
  }
  hasActivatedOnce.value = true
})

onActivated(async () => {
  isKnowledgeViewActive.value = true
  if (!hasActivatedOnce.value) return
  if (!hasLoadedDetail.value) {
    await loadSectionDetail()
  } else {
    await restoreKnowledgeViewState()
    await nextTick()
    keepThumbnailVisible()
  }
  knowledgeLeftRef.value?.addEventListener('scroll', handleKnowledgeScroll, { passive: true })
})

watch(
  () => [route.params.lessonId, route.params.sectionId, route.query.pageNo],
  async ([nextLessonId, nextSectionId, nextPageNo], [prevLessonId, prevSectionId, prevPageNo] = []) => {
    if (nextLessonId === prevLessonId && nextSectionId === prevSectionId && nextPageNo === prevPageNo) return
    if (!isKnowledgeViewActive.value || !isSlideRoute.value || !nextLessonId || !nextSectionId) return
    hasLoadedDetail.value = false
    await loadSectionDetail()
  }
)

onBeforeUnmount(() => {
  isKnowledgeViewActive.value = false
  activeAnswerController.value?.abort()
  cleanupRealtimeAsr()
  stopSectionAudio()
  window.removeEventListener('pagehide', persistRecentVisit)
  knowledgeLeftRef.value?.removeEventListener('scroll', handleKnowledgeScroll)
  persistRecentVisit()
})

onDeactivated(() => {
  isKnowledgeViewActive.value = false
  knowledgeLeftRef.value?.removeEventListener('scroll', handleKnowledgeScroll)
  captureKnowledgeViewState()
})

onBeforeRouteLeave(() => {
  isKnowledgeViewActive.value = false
  activeAnswerController.value?.abort()
  cleanupRealtimeAsr()
  stopSectionAudio()
  persistRecentVisit()
})
</script>

<style scoped>
.knowledge-page {
  height: 100vh;
  background: #ffffff;
  color: #17305e;
  overflow: hidden;
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
  width: 40px;
  height: 40px;
  display: block;
  object-fit: contain;
  flex: 0 0 auto;
  border-radius: 10px;
}

.knowledge-brand-name {
  font-size: 26px;
  font-weight: 700;
  color: #222833;
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

.ppt-card-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
  padding: 0 6px 4px;
}

.ppt-next-section-button {
  min-width: 124px;
  height: 42px;
  padding: 0 20px;
  border: 1px solid #cad8f4;
  border-radius: 14px;
  background: linear-gradient(135deg, #f7fbff 0%, #edf4ff 100%);
  color: #365b97;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease, opacity 0.18s ease;
}

.ppt-next-section-button:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: #7e9de0;
  background: linear-gradient(135deg, #edf4ff 0%, #e5efff 100%);
}

.ppt-next-section-button:disabled {
  opacity: 0.56;
  cursor: not-allowed;
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

.ppt-audio-panel {
  margin-bottom: 8px;
  padding: 12px 14px;
  border: 1px solid #d9e5fb;
  border-radius: 18px;
  background: linear-gradient(180deg, #fbfdff 0%, #f1f6ff 100%);
}

.ppt-audio-panel.disabled {
  opacity: 0.8;
}

.ppt-audio-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.ppt-audio-status,
.ppt-audio-error,
.ppt-audio-time {
  font-size: 13px;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.ppt-audio-status {
  color: #49679d;
  font-weight: 600;
}

.ppt-audio-error {
  color: #c45656;
}

.ppt-audio-progress-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
}

.ppt-audio-time {
  color: #7086b0;
}

.ppt-audio-slider {
  width: 100%;
  height: 4px;
  margin: 0;
  border-radius: 999px;
  appearance: none;
  background: linear-gradient(90deg, #7ba1ff 0%, #9cb9ff 100%);
  outline: none;
  cursor: pointer;
}

.ppt-audio-slider::-webkit-slider-runnable-track {
  height: 4px;
  border-radius: 999px;
  background: linear-gradient(90deg, #7ba1ff 0%, #9cb9ff 100%);
}

.ppt-audio-slider::-webkit-slider-thumb {
  width: 16px;
  height: 16px;
  margin-top: -6px;
  border: 2px solid #ffffff;
  border-radius: 999px;
  appearance: none;
  background: #3d6ce4;
  box-shadow: 0 6px 14px rgba(61, 108, 228, 0.24);
}

.ppt-audio-slider::-moz-range-track {
  height: 4px;
  border-radius: 999px;
  background: linear-gradient(90deg, #7ba1ff 0%, #9cb9ff 100%);
}

.ppt-audio-slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border: 2px solid #ffffff;
  border-radius: 999px;
  background: #3d6ce4;
  box-shadow: 0 6px 14px rgba(61, 108, 228, 0.24);
}

.ppt-audio-slider:disabled {
  cursor: not-allowed;
  opacity: 0.45;
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
  border-right: 2px solid #6f7686;
  background: #eaf2ff;
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

.thumbnail-fallback {
  width: 100%;
  height: 100%;
  padding: 10px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
  color: #4f6591;
  background: linear-gradient(180deg, #f9fbff 0%, #edf3ff 100%);
}

.thumbnail-fallback strong {
  font-size: 18px;
}

.thumbnail-fallback span {
  font-size: 12px;
  line-height: 1.4;
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

.viewer-image-missing {
  width: 100%;
  height: 100%;
  padding: 28px 30px;
  border-radius: 24px;
  background: linear-gradient(180deg, #ffffff 0%, #f5f8ff 100%);
  color: #23406f;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.viewer-image-missing-title {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.3;
}

.viewer-image-missing-desc {
  max-width: 420px;
  margin-top: 12px;
  color: #5d739d;
  font-size: 14px;
  line-height: 1.7;
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
}

.ai-textarea::placeholder {
  color: #97a7c6;
  font-size: 14px;
}

.ai-input-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 8px;
}

.ai-voice-status {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.ai-voice-timer {
  color: #7c8dac;
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}

.ai-icon-button {
  width: 44px;
  height: 44px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #d8e2f3;
  background: rgba(255, 255, 255, 0.96);
  color: #5f6a80;
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.ai-icon-button svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.ai-icon-button.voice {
  box-shadow: 0 8px 18px rgba(140, 158, 196, 0.14);
}

.ai-icon-button.voice.loading {
  background: rgba(255, 255, 255, 0.82);
}

.ai-icon-button.voice.stop {
  color: #11161c;
}

.ai-icon-button.voice.stop {
  color: #11161c;
}


.ai-icon-button.send {
  border-color: #101418;
  background: #101418;
  color: #fff;
}

.ai-icon-button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.ai-icon-button.voice:hover:not(:disabled) {
  background: #f6f9ff;
  border-color: #c6d6ef;
}

.ai-icon-button.send:hover:not(:disabled) {
  background: #1c232d;
  border-color: #1c232d;
}

.ai-icon-button.send.is-stop {
  border-color: #101418;
  background: #101418;
}

.ai-icon-button.send.is-stop:hover:not(:disabled) {
  background: #1c232d;
  border-color: #1c232d;
}

.ai-icon-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ai-inline-loading {
  width: 18px;
  height: 18px;
  display: inline-block;
  border-radius: 999px;
  border: 2px solid rgba(157, 169, 193, 0.28);
  border-top-color: #c7cedd;
  animation: ai-loading-spin 0.9s linear infinite;
}

.ai-message.pending {
  align-items: flex-start;
}

.ai-message-loading {
  padding: 8px 0;
}

@keyframes ai-loading-spin {
  to {
    transform: rotate(360deg);
  }
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

  .ppt-card-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .ppt-audio-button {
    width: 100%;
  }

  .ppt-audio-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .ppt-audio-progress-row {
    display: grid;
    grid-template-columns: 1fr;
    gap: 8px;
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
