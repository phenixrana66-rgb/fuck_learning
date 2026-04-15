<template>
  <TeacherLayout>
    <div class="page-card">
      <div class="page-title">Script Edit</div>

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
        description="No editable script is available yet. Generate a script first."
      >
        <el-button type="primary" @click="goGeneratePage">Go To Generate</el-button>
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
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import TeacherLayout from '@/components/teacher/TeacherLayout.vue'
import { updateScript } from '@/api/teacher'
import { getScriptResult, saveScriptResult } from '@/utils/platform'

const router = useRouter()
const cachedScript = getScriptResult()

const form = reactive({
  scriptId: cachedScript.scriptId || '',
  parseId: cachedScript.parseId || '',
  teachingStyle: cachedScript.teachingStyle || 'standard',
  speechSpeed: cachedScript.speechSpeed || 'normal',
  scriptStructure: Array.isArray(cachedScript.scriptStructure)
    ? cachedScript.scriptStructure.map((section) => ({
        ...section,
        keyPoints: Array.isArray(section.keyPoints) ? [...section.keyPoints] : []
      }))
    : []
})

const saving = ref(false)
const hasScript = computed(() => Boolean(form.scriptId) && form.scriptStructure.length > 0)
const styleLabelMap = {
  standard: 'Standard',
  detailed: 'Detailed',
  concise: 'Concise'
}
const styleLabel = computed(() => styleLabelMap[form.teachingStyle] || form.teachingStyle || '-')

async function handleSave() {
  if (!hasScript.value) {
    ElMessage.warning('No script is available to save')
    return
  }

  saving.value = true
  try {
    const res = await updateScript(form.scriptId, {
      scriptStructure: form.scriptStructure,
      versionRemark: 'teacher-edit'
    })

    const data = res.data || {}
    saveScriptResult({
      ...cachedScript,
      ...form,
      version: data.version || 2,
      status: 'success',
      savedAt: data.savedAt || ''
    })
    ElMessage.success('Script saved')
  } catch (error) {
    ElMessage.error(error.msg || 'Failed to save script')
  } finally {
    saving.value = false
  }
}

function goGeneratePage() {
  router.push('/teacher/script-generate')
}

function goAudioPage() {
  router.push('/teacher/audio-generate')
}
</script>

<style scoped>
.toolbar {
  margin-top: 16px;
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
