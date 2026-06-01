<template>
  <TeacherLayout>
    <div class="page-card teacher-card qa-lab-summary-card">
      <div class="page-title">学生端 QA 实验台</div>
      <div class="qa-lab-summary">
        <div>
          <div class="qa-lab-summary-title">当前定位</div>
          <div class="qa-lab-summary-text">内部调试与运营控制台，用于验证模型切换收益和向量检索贡献。</div>
        </div>
        <div class="qa-lab-summary-actions">
          <el-select
            v-model="selectedCourseId"
            placeholder="切换课程"
            class="teacher-course-select"
            @change="handleChangeCourse"
          >
            <el-option
              v-for="item in courseList"
              :key="item.courseId"
              :label="item.courseName"
              :value="item.courseId"
            />
          </el-select>
          <el-button :loading="loading" @click="fetchPageData">刷新实验台</el-button>
        </div>
      </div>
      <div class="info-grid qa-lab-info-grid">
        <div class="info-item">
          <div class="info-label">当前课程</div>
          <div class="info-value">{{ currentCourse.courseName || '-' }}</div>
        </div>
        <div class="info-item">
          <div class="info-label">已发布课程序号</div>
          <div class="info-value">{{ selectedLessonId || '-' }}</div>
        </div>
        <div class="info-item">
          <div class="info-label">最近配置更新时间</div>
          <div class="info-value">{{ formatDateTime(configUpdatedAt) }}</div>
        </div>
      </div>
      <Loading :visible="loading" text="正在读取 QA 实验台数据..." />
      <ErrorTip v-if="errorCode" :code="errorCode" :message="errorMsg" @retry="fetchPageData" />
    </div>

    <div class="qa-lab-grid">
      <section class="page-card teacher-card qa-lab-card">
        <div class="qa-lab-card-header">
          <div>
            <div class="sub-title">运行时配置</div>
            <div class="qa-lab-card-desc">全局生效，数据库持久化；恢复后会重新回到 config.local.py 默认值。</div>
          </div>
          <div class="qa-lab-config-actions">
            <el-button :loading="resettingConfig" :disabled="!overrideActive" @click="resetRuntimeConfig">恢复默认</el-button>
            <el-button type="primary" :loading="savingConfig" @click="saveRuntimeConfig">保存配置</el-button>
          </div>
        </div>

        <el-alert
          :type="overrideActive ? 'info' : 'success'"
          :title="overrideActive ? '当前正在使用数据库中的运行时覆写。' : '当前直接使用 config.local.py / 后端默认值。'"
          show-icon
          :closable="false"
          class="qa-lab-alert"
        />

        <el-alert
          v-for="warning in configWarnings"
          :key="warning"
          type="warning"
          :title="warning"
          show-icon
          :closable="false"
          class="qa-lab-alert"
        />

        <div class="qa-lab-form-grid">
          <label class="qa-lab-field">
            <span>QA 主模型</span>
            <el-select
              v-model="runtimeForm.qaLlmModel"
              filterable
              allow-create
              default-first-option
              placeholder="输入或选择模型名"
            >
              <el-option
                v-for="item in qaModelOptions"
                :key="item"
                :label="item"
                :value="item"
              />
            </el-select>
          </label>

          <label class="qa-lab-field">
            <span>多模态模型</span>
            <el-select
              v-model="runtimeForm.qaMultimodalModel"
              filterable
              allow-create
              default-first-option
              placeholder="输入或选择模型名"
            >
              <el-option
                v-for="item in multimodalOptions"
                :key="item"
                :label="item"
                :value="item"
              />
            </el-select>
          </label>

          <label class="qa-lab-field">
            <span>Embedding 模型</span>
            <el-select
              v-model="runtimeForm.qaEmbeddingModel"
              filterable
              allow-create
              default-first-option
              placeholder="输入或选择模型名"
            >
              <el-option
                v-for="item in embeddingOptions"
                :key="item"
                :label="item"
                :value="item"
              />
            </el-select>
          </label>

          <label class="qa-lab-field">
            <span>向量检索</span>
            <el-switch v-model="runtimeForm.retrievalEnabled" inline-prompt active-text="开" inactive-text="关" />
          </label>

          <label class="qa-lab-field">
            <span>Top K</span>
            <el-input-number v-model="runtimeForm.retrievalTopK" :min="1" :max="10" :step="1" />
          </label>
        </div>
      </section>

      <section class="page-card teacher-card qa-lab-card">
        <div class="qa-lab-card-header">
          <div>
            <div class="sub-title">对比实验</div>
            <div class="qa-lab-card-desc">同一问题自动双跑，对比检索开启与关闭时的答案、命中上下文和耗时。</div>
          </div>
          <el-button type="success" :loading="runningCompare" @click="runCompareExperiment">开始对比</el-button>
        </div>

        <div class="qa-lab-form-grid qa-lab-form-grid--experiment">
          <label class="qa-lab-field">
            <span>课程序号</span>
            <el-select v-model="selectedLessonId" placeholder="选择课程序号" @change="handleLessonChange">
              <el-option
                v-for="item in lessonOptions"
                :key="item.lessonId"
                :label="`${item.lessonName} (${item.lessonId})`"
                :value="item.lessonId"
              />
            </el-select>
          </label>

          <label class="qa-lab-field">
            <span>章节</span>
            <el-select v-model="selectedSectionId" placeholder="选择章节" @change="handleSectionChange">
              <el-option
                v-for="item in sectionOptions"
                :key="item.sectionId"
                :label="item.sectionName"
                :value="item.sectionId"
              />
            </el-select>
          </label>

          <label class="qa-lab-field">
            <span>页码</span>
            <el-select v-model="selectedPageNo" clearable placeholder="可选，优先定位到当前页">
              <el-option
                v-for="item in pageOptions"
                :key="item.pageNo"
                :label="item.pageTitle ? `第 ${item.pageNo} 页 - ${item.pageTitle}` : `第 ${item.pageNo} 页`"
                :value="item.pageNo"
              />
            </el-select>
          </label>
        </div>

        <label class="qa-lab-field qa-lab-field--textarea">
          <span>测试问题</span>
          <el-input
            v-model="question"
            type="textarea"
            :rows="4"
            maxlength="600"
            show-word-limit
            placeholder="输入要对比的问题。也可以只上传图片，走多模态问答。"
          />
        </label>

        <div class="qa-lab-upload">
          <div class="qa-lab-upload-header">
            <span>图片附件（可选）</span>
            <span class="qa-lab-upload-tip">支持 JPG / PNG / WEBP，最多 5 张。</span>
          </div>
          <div class="qa-lab-upload-actions">
            <input
              :key="pickerKey"
              class="qa-lab-file-input"
              type="file"
              :accept="QA_IMAGE_ACCEPT"
              multiple
              @change="handleFileChange"
            />
            <el-button text type="danger" :disabled="!draftAttachments.length" @click="clearAttachments">清空图片</el-button>
          </div>
          <div v-if="draftAttachments.length" class="qa-lab-attachment-grid">
            <div v-for="attachment in draftAttachments" :key="attachment.id" class="qa-lab-attachment-card">
              <img :src="attachment.previewUrl || attachment.url || attachment.dataUrl" :alt="attachment.name || '提问图片'" loading="lazy" />
              <div class="qa-lab-attachment-meta">
                <span>{{ attachment.name }}</span>
                <button type="button" @click="removeAttachment(attachment.id)">移除</button>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>

    <div v-if="compareResults.length" class="qa-lab-results">
      <div
        v-for="item in compareResults"
        :key="item.variantKey"
        class="page-card teacher-card qa-lab-result-card"
      >
        <div class="qa-lab-result-header">
          <div>
            <div class="sub-title">{{ item.label }}</div>
            <div class="qa-lab-card-desc">
              模型：{{ item.result?.debug?.runtimeConfig?.actualModel || '-' }} |
              Embedding：{{ item.result?.debug?.runtimeConfig?.qaEmbeddingModel || '-' }}
            </div>
          </div>
          <div class="qa-lab-result-tags">
            <el-tag :type="item.result?.debug?.runtimeConfig?.retrievalEnabled ? 'success' : 'info'">
              {{ item.result?.debug?.runtimeConfig?.retrievalEnabled ? '检索开启' : '检索关闭' }}
            </el-tag>
            <el-tag type="warning">耗时 {{ item.result?.debug?.latencyMs ?? 0 }} ms</el-tag>
          </div>
        </div>

        <div class="qa-lab-answer-block">
          <div class="qa-lab-answer-label">答案</div>
          <div class="qa-lab-answer-text">{{ item.result?.answer || '暂无回答' }}</div>
        </div>

        <div class="qa-lab-chip-row">
          <el-tag
            v-for="point in item.result?.relatedKnowledgePoints || []"
            :key="`${item.variantKey}-${point}`"
            effect="plain"
          >
            {{ point }}
          </el-tag>
        </div>

        <div class="qa-lab-detail-block">
          <div class="qa-lab-answer-label">FAQ 命中</div>
          <div v-if="item.result?.debug?.faqCandidates?.length" class="qa-lab-detail-list">
            <div
              v-for="faq in item.result.debug.faqCandidates"
              :key="`${item.variantKey}-faq-${faq.faqId}`"
              class="qa-lab-detail-item"
            >
              <div class="qa-lab-detail-title">
                <span>{{ faq.question }}</span>
                <el-tag size="small" effect="plain">{{ faq.source }}</el-tag>
              </div>
              <div class="qa-lab-detail-text">{{ faq.answer }}</div>
            </div>
          </div>
          <div v-else class="qa-lab-empty-line">本次没有命中 FAQ。</div>
        </div>

        <div class="qa-lab-detail-block">
          <div class="qa-lab-answer-label">上下文命中</div>
          <div v-if="item.result?.debug?.contextChunks?.length" class="qa-lab-detail-list">
            <div
              v-for="chunk in item.result.debug.contextChunks"
              :key="`${item.variantKey}-${chunk.chunkId}`"
              class="qa-lab-detail-item"
            >
              <div class="qa-lab-detail-title">
                <span>{{ formatChunkLabel(chunk) }}</span>
              </div>
              <div class="qa-lab-detail-text">{{ compactText(chunk.chunkText) }}</div>
            </div>
          </div>
          <div v-else class="qa-lab-empty-line">本次没有额外上下文 chunk。</div>
        </div>
      </div>
    </div>
  </TeacherLayout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import TeacherLayout from '@/components/teacher/TeacherLayout.vue'
import Loading from '@/components/teacher/Loading.vue'
import ErrorTip from '@/components/teacher/ErrorTip.vue'
import {
  getQaLabCourseOutline,
  getQaLabRuntimeConfig,
  resetQaLabRuntimeConfig,
  runQaLabCompare,
  updateQaLabRuntimeConfig
} from '@/api/teacher'
import { buildQaImageAttachmentPayloads, QA_IMAGE_ACCEPT, useQaImageAttachments } from '@/composables/useQaImageAttachments'
import { getCourseList, getCurrentCourse, saveCurrentCourse } from '@/utils/platform'

const initialCourseList = getCourseList()
const initialCourse = getCurrentCourse() || initialCourseList[0] || {}

const courseList = ref(initialCourseList)
const currentCourse = ref(initialCourse)
const selectedCourseId = ref(initialCourse.courseId || '')

const loading = ref(false)
const savingConfig = ref(false)
const resettingConfig = ref(false)
const runningCompare = ref(false)
const errorCode = ref('')
const errorMsg = ref('')
const configUpdatedAt = ref('')
const configWarnings = ref([])
const overrideActive = ref(false)

const runtimeForm = ref(createEmptyConfig())
const runtimeDefaults = ref(createEmptyConfig())
const outlineData = ref({ lessons: [] })

const selectedLessonId = ref('')
const selectedSectionId = ref('')
const selectedPageNo = ref(null)
const question = ref('')
const compareResults = ref([])

const {
  draftAttachments,
  pickerKey,
  handleFileChange,
  removeAttachment,
  clearAttachments
} = useQaImageAttachments()

const lessonOptions = computed(() => outlineData.value.lessons || [])
const selectedLesson = computed(() => lessonOptions.value.find((item) => item.lessonId === selectedLessonId.value) || null)
const sectionOptions = computed(() => selectedLesson.value?.sections || [])
const selectedSection = computed(() => sectionOptions.value.find((item) => item.sectionId === selectedSectionId.value) || null)
const pageOptions = computed(() => selectedSection.value?.pages || [])

const qaModelOptions = computed(() => buildModelOptions([
  runtimeForm.value.qaLlmModel,
  runtimeDefaults.value.qaLlmModel,
  'qwen-max',
  'qwen-plus',
  'qwen-turbo'
]))

const multimodalOptions = computed(() => buildModelOptions([
  runtimeForm.value.qaMultimodalModel,
  runtimeDefaults.value.qaMultimodalModel,
  'qwen3.5-plus'
]))

const embeddingOptions = computed(() => buildModelOptions([
  runtimeForm.value.qaEmbeddingModel,
  runtimeDefaults.value.qaEmbeddingModel,
  'text-embedding-v4'
]))

function createEmptyConfig() {
  return {
    qaLlmModel: '',
    qaMultimodalModel: '',
    qaEmbeddingModel: '',
    retrievalEnabled: true,
    retrievalTopK: 5
  }
}

function buildModelOptions(values = []) {
  return [...new Set(values.map((item) => `${item || ''}`.trim()).filter(Boolean))]
}

async function fetchRuntimeConfig() {
  const res = await getQaLabRuntimeConfig()
  runtimeForm.value = { ...createEmptyConfig(), ...(res.data?.config || {}) }
  runtimeDefaults.value = { ...createEmptyConfig(), ...(res.data?.defaults || {}) }
  configWarnings.value = res.data?.warnings || []
  configUpdatedAt.value = res.data?.updatedAt || ''
  overrideActive.value = Boolean(res.data?.overrideActive)
}

async function fetchOutline() {
  if (!currentCourse.value.courseId) {
    outlineData.value = { lessons: [] }
    selectedLessonId.value = ''
    selectedSectionId.value = ''
    selectedPageNo.value = null
    return
  }
  const res = await getQaLabCourseOutline({ courseId: currentCourse.value.courseId })
  outlineData.value = res.data || { lessons: [] }
  syncSelections()
}

async function fetchPageData() {
  loading.value = true
  errorCode.value = ''
  errorMsg.value = ''
  try {
    await Promise.all([fetchRuntimeConfig(), fetchOutline()])
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || '读取 QA 实验台数据失败。'
  } finally {
    loading.value = false
  }
}

function syncSelections() {
  const lessons = lessonOptions.value
  if (!lessons.length) {
    selectedLessonId.value = ''
    selectedSectionId.value = ''
    selectedPageNo.value = null
    return
  }
  if (!lessons.some((item) => item.lessonId === selectedLessonId.value)) {
    selectedLessonId.value = lessons[0].lessonId
  }
  const sections = selectedLesson.value?.sections || []
  if (!sections.some((item) => item.sectionId === selectedSectionId.value)) {
    selectedSectionId.value = sections[0]?.sectionId || ''
  }
  const pages = selectedSection.value?.pages || []
  if (selectedPageNo.value && !pages.some((item) => item.pageNo === selectedPageNo.value)) {
    selectedPageNo.value = null
  }
}

function handleChangeCourse(courseId) {
  const target = courseList.value.find((item) => String(item.courseId) === String(courseId))
  if (!target) return
  currentCourse.value = target
  selectedCourseId.value = target.courseId
  saveCurrentCourse(target)
  compareResults.value = []
  fetchPageData()
}

function handleLessonChange() {
  const sections = selectedLesson.value?.sections || []
  selectedSectionId.value = sections[0]?.sectionId || ''
  selectedPageNo.value = null
}

function handleSectionChange() {
  selectedPageNo.value = null
}

async function saveRuntimeConfig() {
  savingConfig.value = true
  try {
    const res = await updateQaLabRuntimeConfig(runtimeForm.value)
    runtimeForm.value = { ...createEmptyConfig(), ...(res.data?.config || {}) }
    runtimeDefaults.value = { ...createEmptyConfig(), ...(res.data?.defaults || {}) }
    configWarnings.value = res.data?.warnings || []
    configUpdatedAt.value = res.data?.updatedAt || ''
    overrideActive.value = Boolean(res.data?.overrideActive)
    ElMessage.success('QA 运行时配置已保存')
  } catch (error) {
    ElMessage.error(error.msg || '保存 QA 运行时配置失败')
  } finally {
    savingConfig.value = false
  }
}

async function resetRuntimeConfig() {
  try {
    await ElMessageBox.confirm(
      '恢复后会清除数据库中的 QA 运行时覆写，学生端 QA 将重新使用 config.local.py 的默认配置。是否继续？',
      '恢复默认配置',
      {
        confirmButtonText: '恢复默认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
  } catch (_error) {
    return
  }

  resettingConfig.value = true
  try {
    const res = await resetQaLabRuntimeConfig()
    runtimeForm.value = { ...createEmptyConfig(), ...(res.data?.config || {}) }
    runtimeDefaults.value = { ...createEmptyConfig(), ...(res.data?.defaults || {}) }
    configWarnings.value = res.data?.warnings || []
    configUpdatedAt.value = res.data?.updatedAt || ''
    overrideActive.value = Boolean(res.data?.overrideActive)
    ElMessage.success('已恢复为 config.local.py 默认配置')
  } catch (error) {
    ElMessage.error(error.msg || '恢复默认配置失败')
  } finally {
    resettingConfig.value = false
  }
}

async function runCompareExperiment() {
  runningCompare.value = true
  try {
    const payload = {
      courseId: currentCourse.value.courseId || '',
      lessonId: selectedLessonId.value,
      sectionId: selectedSectionId.value,
      pageNo: selectedPageNo.value || undefined,
      question: question.value,
      attachments: buildQaImageAttachmentPayloads(draftAttachments.value)
    }
    const res = await runQaLabCompare(payload)
    compareResults.value = res.data?.results || []
  } catch (error) {
    ElMessage.error(error.msg || '执行 QA 对比实验失败')
  } finally {
    runningCompare.value = false
  }
}

function formatDateTime(value) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString('zh-CN', { hour12: false })
  } catch (_error) {
    return value
  }
}

function compactText(value) {
  const normalized = `${value || ''}`.replace(/\s+/g, ' ').trim()
  if (normalized.length <= 180) return normalized
  return `${normalized.slice(0, 180)}...`
}

function formatChunkLabel(chunk) {
  const source = {
    page_content: 'PPT 页面',
    chapter_context: '章节上下文',
    ppt_outline: '整份 PPT',
    knowledge_point: '知识点',
    section_summary: '章节摘要'
  }[chunk.sourceType] || chunk.sourceType || '上下文'
  if (chunk.pageNo) {
    return `${source} · 第 ${chunk.pageNo} 页`
  }
  return source
}

onMounted(() => {
  fetchPageData()
})
</script>

<style scoped>
.teacher-card {
  border-radius: 22px;
  border: 1px solid #e7eef9;
  box-shadow: 0 16px 36px rgba(53, 82, 136, 0.08);
}

.qa-lab-summary-card {
  margin-bottom: 18px;
}

.qa-lab-summary {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-top: 14px;
}

.qa-lab-summary-title {
  color: #203b70;
  font-size: 16px;
  font-weight: 700;
}

.qa-lab-summary-text {
  margin-top: 8px;
  color: #6f84a9;
  line-height: 1.7;
}

.qa-lab-summary-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.qa-lab-info-grid {
  margin-top: 18px;
}

.qa-lab-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(320px, 1fr));
  gap: 16px;
}

.qa-lab-card {
  min-height: 100%;
}

.qa-lab-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.qa-lab-card-desc {
  margin-top: 8px;
  color: #7f90af;
  font-size: 13px;
  line-height: 1.7;
}

.qa-lab-config-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.qa-lab-alert {
  margin-top: 16px;
}

.qa-lab-form-grid {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(2, minmax(220px, 1fr));
  gap: 16px;
}

.qa-lab-form-grid--experiment {
  grid-template-columns: repeat(3, minmax(180px, 1fr));
}

.qa-lab-field {
  display: grid;
  gap: 10px;
  color: #314d81;
  font-size: 14px;
  font-weight: 600;
}

.qa-lab-field--textarea {
  margin-top: 18px;
}

.qa-lab-upload {
  margin-top: 18px;
  border-radius: 18px;
  border: 1px dashed #d8e2f4;
  background: #f9fbff;
  padding: 16px;
}

.qa-lab-upload-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #2f4d83;
  font-weight: 600;
}

.qa-lab-upload-tip {
  color: #8c9bbb;
  font-size: 12px;
  font-weight: 400;
}

.qa-lab-upload-actions {
  margin-top: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.qa-lab-file-input {
  max-width: 100%;
}

.qa-lab-attachment-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}

.qa-lab-attachment-card {
  overflow: hidden;
  border-radius: 16px;
  border: 1px solid #dce6f7;
  background: #fff;
}

.qa-lab-attachment-card img {
  width: 100%;
  height: 116px;
  object-fit: cover;
  display: block;
  background: #eef4ff;
}

.qa-lab-attachment-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  color: #4a618d;
  font-size: 12px;
}

.qa-lab-attachment-meta button {
  border: 0;
  background: transparent;
  color: #d04848;
  cursor: pointer;
}

.qa-lab-results {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(2, minmax(320px, 1fr));
  gap: 16px;
}

.qa-lab-result-card {
  min-height: 100%;
}

.qa-lab-result-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.qa-lab-result-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.qa-lab-answer-block,
.qa-lab-detail-block {
  margin-top: 18px;
}

.qa-lab-answer-label {
  color: #203b70;
  font-size: 14px;
  font-weight: 700;
}

.qa-lab-answer-text {
  margin-top: 10px;
  color: #435a82;
  line-height: 1.8;
  white-space: pre-wrap;
}

.qa-lab-chip-row {
  margin-top: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.qa-lab-detail-list {
  margin-top: 10px;
  display: grid;
  gap: 10px;
}

.qa-lab-detail-item {
  border-radius: 16px;
  background: #f8fbff;
  border: 1px solid #e6eefb;
  padding: 12px 14px;
}

.qa-lab-detail-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #27457c;
  font-size: 13px;
  font-weight: 700;
}

.qa-lab-detail-text {
  margin-top: 8px;
  color: #5b7097;
  font-size: 13px;
  line-height: 1.7;
}

.qa-lab-empty-line {
  margin-top: 10px;
  color: #8a9ab7;
  font-size: 13px;
}

@media (max-width: 1100px) {
  .qa-lab-grid,
  .qa-lab-results {
    grid-template-columns: 1fr;
  }

  .qa-lab-summary,
  .qa-lab-card-header,
  .qa-lab-result-header {
    flex-direction: column;
  }

  .qa-lab-form-grid,
  .qa-lab-form-grid--experiment {
    grid-template-columns: 1fr;
  }
}
</style>
