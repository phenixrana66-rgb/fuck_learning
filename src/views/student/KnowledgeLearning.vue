<template>
  <div class="knowledge-chapter-page">
    <header class="knowledge-chapter-topbar">
      <button
        type="button"
        class="knowledge-chapter-back-button"
        aria-label="返回智课讲授"
        @click="goBack"
      >
        <svg viewBox="0 0 20 20" aria-hidden="true">
          <path d="M12.5 4.5L7 10l5.5 5.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>

      <div
        class="knowledge-chapter-brand"
        role="button"
        tabindex="0"
        @click="goStudentHome"
        @keydown.enter.prevent="goStudentHome"
        @keydown.space.prevent="goStudentHome"
      >
        <img class="knowledge-chapter-brand-mark" src="/chaoxing-erya-logo.svg" alt="超星尔雅" />
        <div class="knowledge-chapter-brand-name">尔雅</div>
      </div>
    </header>

    <main ref="pageMainRef" class="knowledge-chapter-main app-scrollable">
      <section class="knowledge-chapter-shell">
        <div class="knowledge-chapter-header">
          <div class="knowledge-chapter-header-main">
            <div class="knowledge-chapter-badge">章节详情</div>
            <h1>{{ currentAggregatedChapter.chapterTitle || '章节学习' }}</h1>
          </div>
          <div class="knowledge-chapter-header-meta">
            {{ completedSectionCount }}/{{ chapterSections.length || 0 }} 已完成
          </div>
        </div>

        <div v-if="!chapterSections.length" class="knowledge-chapter-empty">
          当前章节暂无可展示的课程卡片。
        </div>

        <div v-else class="knowledge-chapter-grid">
          <article
            v-for="section in chapterSections"
            :key="section.chapterId"
            class="knowledge-course-card"
            :class="{ active: String(section.sectionId || '') === currentLearningSectionId }"
          >
            <div class="knowledge-course-card-head">
              <div>
                <div class="knowledge-course-status" :class="getSectionStatusClass(section)">{{ getSectionStatusLabel(section) }}</div>
                <h3>{{ section.chapterTitle }}</h3>
              </div>
              <div class="knowledge-course-mastery-badge">
                <span>掌握度</span>
                <strong>{{ Number(section.masteryPercent || 0) }}%</strong>
              </div>
            </div>

            <div class="knowledge-course-card-footer">
              <div class="knowledge-course-progress-block">
                <div class="knowledge-course-progress-text">
                  <span>学习进度</span>
                  <strong>{{ Number(section.progressPercent || 0) }}%</strong>
                </div>
                <el-progress :percentage="Number(section.progressPercent || 0)" :stroke-width="8" :show-text="false" />
              </div>

              <div class="knowledge-course-footer-row">
                <button type="button" class="knowledge-course-action-button" @click.stop="goToSlideLearning(section)">
                  <span class="knowledge-course-action-button-core">
                    <span class="knowledge-course-action-button-text">进入学习</span>
                    <span class="knowledge-course-action-button-glow" aria-hidden="true"></span>
                  </span>
                </button>
              </div>
            </div>
          </article>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { playStudentLesson } from '@/api/student'
import { findFrontendTestLesson } from '@/mock/studentLessons'
import { getPlatformToken, getStudentLessonListCache, getStudentProfile, getStudentViewState, saveStudentLessonList, saveStudentViewState } from '@/utils/platform'
import { buildAggregatedKnowledgeUnits, getSectionsForAggregatedChapter } from '@/utils/studentKnowledge'

const route = useRoute()
const router = useRouter()
const pageMainRef = ref(null)

const fallbackProfile = {
  studentId: 'S2026001',
  studentName: '',
  collegeName: ''
}

const studentProfile = ref({
  ...fallbackProfile,
  ...getStudentProfile()
})
const lesson = ref({ units: [] })
const loading = ref(false)

const lessonId = computed(() => String(route.params.lessonId || ''))
const unitId = computed(() => String(route.params.unitId || ''))
const chapterId = computed(() => String(route.params.chapterId || ''))
const currentToken = computed(() => String(route.query.token || getPlatformToken() || ''))
const aggregatedUnits = computed(() => buildAggregatedKnowledgeUnits(lesson.value.units || []))
const currentAggregatedChapter = computed(() => {
  const targetUnit = aggregatedUnits.value.find((unit) => String(unit.unitId || '') === unitId.value)
  if (targetUnit) {
    const matchedChapter = (targetUnit.chapters || []).find((chapter) => String(chapter.chapterId || '') === chapterId.value)
    if (matchedChapter) return matchedChapter
    return targetUnit.chapters?.[0] || {}
  }
  return aggregatedUnits.value.flatMap((unit) => unit.chapters || []).find((chapter) => String(chapter.chapterId || '') === chapterId.value)
    || aggregatedUnits.value.flatMap((unit) => unit.chapters || [])[0]
    || {}
})
const chapterSections = computed(() => getSectionsForAggregatedChapter(
  lesson.value.units || [],
  unitId.value || currentAggregatedChapter.value.unitId || '',
  currentAggregatedChapter.value.chapterTitle || '',
  currentAggregatedChapter.value.chapterId || chapterId.value || ''
))
const completedSectionCount = computed(() => chapterSections.value.filter((section) => Number(section.progressPercent || 0) >= 100).length)
const currentLearningSectionId = computed(() => {
  const currentSection = chapterSections.value.find((section) => {
    const progress = Number(section?.progressPercent || 0)
    return progress > 0 && progress < 100
  })
  return String(currentSection?.sectionId || '')
})

function syncLessonCache(nextLesson) {
  if (!nextLesson?.lessonId) return
  const cache = getStudentLessonListCache()
  const hasExisting = cache.some((item) => String(item.lessonId) === String(nextLesson.lessonId))
  const updated = hasExisting
    ? cache.map((item) => (String(item.lessonId) === String(nextLesson.lessonId) ? { ...item, ...nextLesson } : item))
    : [...cache, nextLesson]
  saveStudentLessonList(updated)
}

function getFallbackLesson() {
  return getStudentLessonListCache().find((item) => String(item.lessonId) === lessonId.value)
    || findFrontendTestLesson(lessonId.value)
    || { lessonId: lessonId.value, units: [] }
}

async function loadLesson() {
  lesson.value = getFallbackLesson()
  loading.value = true
  try {
    const res = await playStudentLesson({
      studentId: studentProfile.value.studentId || fallbackProfile.studentId,
      lessonId: lessonId.value
    })
    if (res.data) {
      lesson.value = res.data
      syncLessonCache(res.data)
    }
  } catch (error) {
    if (!error?.handled) {
      ElMessage.warning(error?.msg || '章节详情已回退为本地缓存数据')
    }
  } finally {
    loading.value = false
  }
}

function captureChapterViewState() {
  const lessonViewState = getStudentViewState(lessonId.value)
  const chapterState = { ...(lessonViewState.chapterDetail || {}) }
  chapterState[currentAggregatedChapter.value.chapterId || chapterId.value || 'default'] = {
    scrollTop: pageMainRef.value?.scrollTop || 0
  }
  saveStudentViewState(lessonId.value, { chapterDetail: chapterState })
}

async function restoreChapterViewState() {
  const lessonViewState = getStudentViewState(lessonId.value)
  const stored = lessonViewState.chapterDetail?.[currentAggregatedChapter.value.chapterId || chapterId.value || 'default'] || {}
  await nextTick()
  if (pageMainRef.value && Number.isFinite(Number(stored.scrollTop))) {
    pageMainRef.value.scrollTop = Number(stored.scrollTop || 0)
  }
}

function getSectionStatusLabel(section) {
  if (String(section?.sectionId || '') === currentLearningSectionId.value) return '当前学习'
  if (Number(section?.progressPercent || 0) >= 100) return '已完成'
  if (Number(section?.progressPercent || 0) > 0) return '进行中'
  return '待学习'
}

function getSectionStatusClass(section) {
  if (String(section?.sectionId || '') === currentLearningSectionId.value) return 'is-active'
  if (Number(section?.progressPercent || 0) >= 100) return 'is-done'
  if (Number(section?.progressPercent || 0) > 0) return 'is-progress'
  return 'is-pending'
}

function goToSlideLearning(section) {
  if (!section?.sectionId) return
  captureChapterViewState()
  router.push({
    name: 'StudentSlideLearning',
    params: {
      lessonId: lessonId.value,
      sectionId: section.sectionId
    },
    query: {
      ...(currentToken.value ? { token: currentToken.value } : {}),
      ...(section.chapterId ? { chapterId: section.chapterId } : {}),
      ...(unitId.value ? { unitId: unitId.value } : {}),
      ...(currentAggregatedChapter.value.chapterId ? { knowledgeChapterId: currentAggregatedChapter.value.chapterId } : {}),
      ...(section.pageNo ? { pageNo: String(section.pageNo) } : {})
    }
  })
}

function goBack() {
  captureChapterViewState()
  const playerState = getStudentViewState(lessonId.value)?.player || {}
  saveStudentViewState(lessonId.value, {
    player: {
      ...playerState,
      activeView: 'knowledge',
      activeKnowledgeChapterId: currentAggregatedChapter.value.chapterId || playerState.activeKnowledgeChapterId || ''
    }
  })
  router.push({
    name: 'StudentPlayer',
    params: { lessonId: lessonId.value },
    query: currentToken.value ? { token: currentToken.value } : {}
  })
}

function goStudentHome() {
  router.push({
    name: 'StudentHome',
    query: currentToken.value ? { token: currentToken.value } : {}
  })
}

watch(chapterSections, (sections) => {
  if (!sections.length) {
    if (pageMainRef.value) {
      pageMainRef.value.scrollTop = 0
    }
  }
}, { immediate: true })

watch(
  () => [route.params.lessonId, route.params.unitId, route.params.chapterId],
  async ([nextLessonId, nextUnitId, nextChapterId], [prevLessonId, prevUnitId, prevChapterId] = []) => {
    if (nextLessonId === prevLessonId && nextUnitId === prevUnitId && nextChapterId === prevChapterId) return
    await loadLesson()
    await restoreChapterViewState()
  }
)

onMounted(async () => {
  await loadLesson()
  await restoreChapterViewState()
})

onActivated(async () => {
  if (!lesson.value.units?.length && !loading.value) {
    await loadLesson()
  }
  await restoreChapterViewState()
})

onDeactivated(() => {
  captureChapterViewState()
})

onBeforeUnmount(() => {
  captureChapterViewState()
})
</script>

<style scoped>
.knowledge-chapter-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #eff3fb 0%, #f7f8fc 100%);
}

.knowledge-chapter-topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 30;
  height: 84px;
  padding: 0 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1px solid #edf1f7;
  backdrop-filter: blur(14px);
}

.knowledge-chapter-back-button {
  width: 44px;
  height: 44px;
  border: 1px solid #dbe6f8;
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff, #f6f9ff);
  color: #315186;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease;
}

.knowledge-chapter-back-button:hover {
  transform: translateY(-1px);
  border-color: #c4d6f2;
  background: #f6f9ff;
}

.knowledge-chapter-back-button svg {
  width: 18px;
  height: 18px;
}

.knowledge-chapter-brand {
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
}

.knowledge-chapter-brand:focus-visible {
  outline: 2px solid rgba(82, 126, 246, 0.45);
  outline-offset: 6px;
  border-radius: 16px;
}

.knowledge-chapter-brand-mark {
  width: 40px;
  height: 40px;
  display: block;
  object-fit: contain;
  flex: 0 0 auto;
  border-radius: 10px;
}

.knowledge-chapter-brand-name {
  font-size: 26px;
  font-weight: 700;
  color: #222833;
}

.knowledge-chapter-main {
  height: calc(100vh - 84px);
  box-sizing: border-box;
  padding: 24px 28px 28px;
  margin-top: 84px;
  overflow-y: auto;
  overflow-x: hidden;
}

.knowledge-chapter-shell {
  max-width: 1332px;
  margin: 0 auto;
  padding: 28px 30px 30px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid #edf2f8;
  box-shadow: 0 16px 40px rgba(25, 43, 92, 0.05);
}

.knowledge-chapter-header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
}

.knowledge-chapter-badge {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 14px;
  border-radius: 999px;
  background: #eef4ff;
  color: #48669d;
  font-size: 12px;
  font-weight: 600;
}

.knowledge-chapter-header-main h1 {
  margin: 14px 0 0;
  color: #17315d;
  font-size: 28px;
  line-height: 1.4;
}

.knowledge-chapter-header-meta {
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

.knowledge-chapter-empty {
  margin-top: 24px;
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

.knowledge-chapter-grid {
  margin-top: 24px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  width: 100%;
}

.knowledge-course-card {
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

.knowledge-course-card:hover,
.knowledge-course-card.active {
  transform: translateY(-2px);
  border-color: #c9d9f3;
  background: linear-gradient(180deg, #ffffff, #eef5ff);
  box-shadow: 0 18px 34px rgba(92, 123, 180, 0.1);
}

.knowledge-course-card-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.knowledge-course-card-head h3 {
  margin: 10px 0 0;
  color: #172f58;
  font-size: 20px;
  line-height: 1.5;
}

.knowledge-course-status {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.knowledge-course-status.is-active {
  background: #ddebff;
  color: #2f63c7;
}

.knowledge-course-status.is-done {
  background: #e9f8ef;
  color: #2d8a54;
}

.knowledge-course-status.is-progress {
  background: #eef3ff;
  color: #4e73b7;
}

.knowledge-course-status.is-pending {
  background: #f3f6fb;
  color: #8392ad;
}

.knowledge-course-mastery-badge {
  flex: 0 0 auto;
  width: 124px;
  min-height: 148px;
  padding: 20px 16px;
  border-radius: 26px;
  background: linear-gradient(180deg, rgba(242, 247, 255, 0.98), rgba(230, 238, 252, 0.92));
  border: 1px solid rgba(207, 221, 245, 0.98);
  display: grid;
  place-items: center;
  text-align: center;
}

.knowledge-course-mastery-badge span {
  color: #6980a8;
  font-size: 13px;
}

.knowledge-course-mastery-badge strong {
  margin-top: 10px;
  color: #18335f;
  font-size: 18px;
  line-height: 1;
}

.knowledge-course-card-footer {
  display: grid;
  gap: 14px;
  margin-top: auto;
  padding-top: 18px;
}

.knowledge-course-progress-block {
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.68);
  border: 1px solid rgba(228, 236, 247, 0.96);
}

.knowledge-course-progress-text {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #6d7a98;
  font-size: 13px;
}

.knowledge-course-progress-text strong {
  color: #18325f;
}

.knowledge-course-footer-row {
  display: flex;
  justify-content: flex-end;
}

.knowledge-course-progress-block :deep(.el-progress-bar__outer) {
  background: #e8effa;
}

.knowledge-course-progress-block :deep(.el-progress-bar__inner) {
  background: linear-gradient(135deg, rgb(70, 150, 255), rgb(70, 150, 255));
}

.knowledge-course-action-button {
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

.knowledge-course-action-button::before {
  content: '';
  position: absolute;
  inset: 1px;
  border-radius: 13px;
  background: linear-gradient(135deg, rgba(90, 180, 255, 0.98), rgba(72, 158, 240, 0.98) 62%, rgba(57, 136, 224, 0.98));
}

.knowledge-course-action-button::after {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(115deg, transparent 20%, rgba(218, 245, 255, 0.44) 34%, transparent 52%),
    linear-gradient(90deg, transparent, rgba(176, 231, 255, 0.24), transparent);
  transform: translateX(-120%);
  transition: transform 0.55s ease;
}

.knowledge-course-action-button:hover {
  transform: translateY(-2px);
  box-shadow:
    0 20px 30px rgba(73, 150, 221, 0.26),
    inset 0 0 0 1px rgba(201, 238, 255, 0.34),
    inset 0 1px 0 rgba(255, 255, 255, 0.26);
  filter: saturate(1.12);
}

.knowledge-course-action-button:hover::after {
  transform: translateX(120%);
}

.knowledge-course-action-button:active {
  transform: translateY(0) scale(0.988);
}

.knowledge-course-action-button-core {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
  padding: 0 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.knowledge-course-action-button-text {
  position: relative;
  z-index: 2;
  color: #f4fbff;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-shadow: 0 0 16px rgba(217, 244, 255, 0.32);
}

.knowledge-course-action-button-glow {
  position: absolute;
  inset: 8px 10px;
  border-radius: 10px;
  background: linear-gradient(90deg, rgba(190, 238, 255, 0.1), rgba(234, 248, 255, 0.32), rgba(190, 238, 255, 0.1));
  filter: blur(9px);
  opacity: 0.7;
  transition: opacity 0.22s ease, filter 0.22s ease;
}

.knowledge-course-action-button:hover .knowledge-course-action-button-glow {
  opacity: 1;
  filter: blur(11px);
}

@media (max-width: 960px) {
  .knowledge-chapter-topbar {
    padding: 0 20px;
  }

  .knowledge-chapter-main {
    padding: 24px 20px;
  }

  .knowledge-chapter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .knowledge-chapter-header,
  .knowledge-course-footer-row {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 640px) {
  .knowledge-chapter-topbar {
    height: 76px;
    padding: 0 16px;
  }

  .knowledge-chapter-main {
    height: calc(100vh - 76px);
    padding: 20px 16px;
    margin-top: 76px;
  }

  .knowledge-chapter-shell {
    padding: 22px 18px 24px;
    border-radius: 24px;
  }

  .knowledge-chapter-header-main h1 {
    font-size: 24px;
  }

  .knowledge-chapter-grid {
    grid-template-columns: 1fr;
  }
}
</style>
