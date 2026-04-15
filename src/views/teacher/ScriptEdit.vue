<template>
  <TeacherLayout>
    <div class="page-card">
      <div class="page-title">Script Edit</div>

      <div class="toolbar top-actions">
        <el-button :loading="restoring" @click="loadLastResult">Load Last Result</el-button>
        <el-button v-if="form.scriptId" @click="refreshFromServer">Refresh Server Copy</el-button>
      </div>

      <template v-if="hasScript">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="scriptId">{{ form.scriptId }}</el-descriptions-item>
          <el-descriptions-item label="parseId">{{ form.parseId }}</el-descriptions-item>
          <el-descriptions-item label="Style">{{ styleLabel }}</el-descriptions-item>
          <el-descriptions-item label="Sections">{{ form.scriptStructure.length }}</el-descriptions-item>
        </el-descriptions>

        <div class="toolbar">
          <el-button type="primary" :loading="saving" @click="handleSave">Save Script</el-button>
          <el-button type="success" @click="goAudioPage">Go To Audio</el-button>
        </div>
      </template>

      <el-empty
        v-else
        description="No editable script is available yet. Load the last result or generate a new one."
      >
        <el-button type="primary" :loading="restoring" @click="loadLastResult">Load Last Result</el-button>
        <el-button @click="goGeneratePage">Go To Generate</el-button>
      </el-empty>
    </div>

    <div v-if="hasScript" class="page-card">
      <div class="sub-title">Script Content</div>

      <div
        v-for="(section, index) in form.scriptStructure"
        :key="section.sectionId"
        class="section-card"
      >
        <div class="section-meta">
          <div>
            <div class="section-index">Section {{ index + 1 }}</div>
            <div class="section-name">{{ section.sectionName }}</div>
          </div>
          <div class="section-tags">
            <el-tag size="small">{{ section.sectionId }}</el-tag>
            <el-tag v-if="section.relatedPage" size="small" type="success">Page {{ section.relatedPage }}</el-tag>
            <el-tag size="small" type="warning">{{ section.duration || 0 }} sec</el-tag>
          </div>
        </div>

        <div v-if="section.keyPoints?.length" class="key-points">
          <span
            v-for="point in section.keyPoints"
            :key="point"
            class="key-point"
          >
            {{ point }}
          </span>
        </div>

        <el-input
          v-model="section.content"
          type="textarea"
          :rows="8"
          resize="vertical"
        />
      </div>
    </div>
  </TeacherLayout>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import TeacherLayout from '@/components/teacher/TeacherLayout.vue'
import { getScript, updateScript } from '@/api/teacher'
import { getScriptResult, getScriptTask, patchScriptTask, saveScriptResult } from '@/utils/platform'

const TASK_PAGE = 'script-edit'
const router = useRouter()
const cachedResult = getScriptResult()
const cachedTask = getScriptTask()

const form = reactive(createFormState(cachedResult.scriptId ? cachedResult : cachedTask))
const saving = ref(false)
const restoring = ref(false)
const bootstrapped = ref(false)

const hasScript = computed(() => Boolean(form.scriptId) && form.scriptStructure.length > 0)
const styleLabelMap = {
  standard: 'Standard',
  detailed: 'Detailed',
  concise: 'Concise'
}
const styleLabel = computed(() => styleLabelMap[form.teachingStyle] || form.teachingStyle || '-')

watch(
  form,
  () => {
    if (!bootstrapped.value) {
      return
    }
    persistDraft()
  },
  { deep: true }
)

onMounted(async () => {
  patchScriptTask({ lastPage: TASK_PAGE })
  await loadLastResult({ silent: true })
  bootstrapped.value = true
  window.addEventListener('beforeunload', persistDraft)
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onBeforeUnmount(() => {
  persistDraft()
  window.removeEventListener('beforeunload', persistDraft)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})

async function handleSave() {
  if (!hasScript.value) {
    ElMessage.warning('No script is available to save')
    return
  }

  saving.value = true
  try {
    const res = await updateScript(form.scriptId, {
      scriptStructure: cloneSections(form.scriptStructure),
      versionRemark: 'teacher-edit'
    })

    const data = res.data || {}
    const nextResult = {
      ...getScriptResult(),
      ...serializeForm(),
      version: data.version || 2,
      status: 'success',
      savedAt: data.savedAt || ''
    }
    saveScriptResult(nextResult)
    patchScriptTask({
      ...nextResult,
      status: 'success',
      lastPage: TASK_PAGE
    })
    ElMessage.success('Script saved')
  } catch (error) {
    ElMessage.error(error.msg || 'Failed to save script')
  } finally {
    saving.value = false
  }
}

async function loadLastResult(options = {}) {
  const { silent = false, forceRemote = false } = options
  const latestResult = getScriptResult()
  const latestTask = getScriptTask()

  if (!forceRemote && hasScriptStructure(latestResult)) {
    applyForm(latestResult)
    patchScriptTask({
      ...latestResult,
      status: latestTask.status || latestResult.status || 'success',
      lastPage: TASK_PAGE
    })
    if (!silent) {
      ElMessage.success('Loaded the last cached result')
    }
    return
  }

  const scriptId = latestResult.scriptId || latestTask.scriptId || form.scriptId
  if (!scriptId) {
    if (!silent) {
      ElMessage.warning('No previous script result is available')
    }
    return
  }

  restoring.value = true
  try {
    const res = await getScript(scriptId)
    const data = res.data || {}
    const mergedResult = {
      ...latestTask,
      ...latestResult,
      ...data,
      status: 'success'
    }
    applyForm(mergedResult)
    saveScriptResult(mergedResult)
    patchScriptTask({
      ...mergedResult,
      status: 'success',
      lastPage: TASK_PAGE
    })
    if (!silent) {
      ElMessage.success('Loaded the last result')
    }
  } catch (error) {
    if (!silent) {
      ElMessage.error(error.msg || 'Failed to load the last result')
    }
  } finally {
    restoring.value = false
  }
}

async function refreshFromServer() {
  await loadLastResult({ forceRemote: true })
}

function persistDraft() {
  if (!form.parseId && !form.scriptId) {
    return
  }

  const currentTask = getScriptTask()
  const currentResult = getScriptResult()
  const nextResult = {
    ...currentResult,
    ...serializeForm(),
    version: currentResult.version || currentTask.version || 1,
    status: currentTask.status || currentResult.status || 'success',
    savedAt: currentResult.savedAt || currentTask.savedAt || ''
  }
  saveScriptResult(nextResult)
  patchScriptTask({
    ...nextResult,
    lastPage: TASK_PAGE
  })
}

function handleVisibilityChange() {
  if (document.visibilityState === 'hidden') {
    persistDraft()
  }
}

function goGeneratePage() {
  router.push('/teacher/script-generate')
}

function goAudioPage() {
  router.push('/teacher/audio-generate')
}

function applyForm(source) {
  const next = createFormState(source)
  form.scriptId = next.scriptId
  form.parseId = next.parseId
  form.teachingStyle = next.teachingStyle
  form.speechSpeed = next.speechSpeed
  form.scriptStructure = next.scriptStructure
}

function createFormState(source = {}) {
  return {
    scriptId: source.scriptId || '',
    parseId: source.parseId || '',
    teachingStyle: source.teachingStyle || 'standard',
    speechSpeed: source.speechSpeed || 'normal',
    scriptStructure: cloneSections(source.scriptStructure)
  }
}

function serializeForm() {
  return {
    scriptId: form.scriptId,
    parseId: form.parseId,
    teachingStyle: form.teachingStyle,
    speechSpeed: form.speechSpeed,
    scriptStructure: cloneSections(form.scriptStructure)
  }
}

function cloneSections(sections = []) {
  return Array.isArray(sections)
    ? sections.map((section) => ({
        ...section,
        keyPoints: Array.isArray(section.keyPoints) ? [...section.keyPoints] : []
      }))
    : []
}

function hasScriptStructure(value) {
  return Array.isArray(value?.scriptStructure) && value.scriptStructure.length > 0
}
</script>

<style scoped>
.toolbar {
  margin-top: 16px;
}

.top-actions {
  margin-top: 0;
  margin-bottom: 16px;
}

.section-card {
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 16px;
  margin-top: 16px;
  background: #fff;
}

.section-meta {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.section-index {
  font-size: 12px;
  color: #909399;
}

.section-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-top: 4px;
}

.section-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.key-points {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.key-point {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  color: #3a5b7a;
  background: #eef5fb;
}
</style>
