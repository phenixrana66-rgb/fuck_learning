<template>
  <TeacherLayout>
    <div class="page-card teacher-card model-config-summary">
      <div class="page-title">模型配置</div>
      <div class="model-config-toolbar">
        <div class="model-config-status">
          <el-tag :type="overrideActive ? 'warning' : 'success'" effect="light">
            {{ overrideActive ? '运行时覆写' : '默认配置' }}
          </el-tag>
          <span>更新时间：{{ formatDateTime(configUpdatedAt) }}</span>
        </div>
        <div class="model-config-actions">
          <el-button :loading="loading" @click="fetchConfig">刷新</el-button>
          <el-button :loading="resetting" :disabled="!overrideActive" @click="resetConfig">恢复默认</el-button>
          <el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button>
        </div>
      </div>
      <el-alert
        v-for="warning in warnings"
        :key="warning"
        type="warning"
        :title="warning"
        show-icon
        :closable="false"
        class="model-config-alert"
      />
      <Loading :visible="loading" text="正在读取模型配置..." />
      <ErrorTip v-if="errorCode" :code="errorCode" :message="errorMsg" @retry="fetchConfig" />
    </div>

    <section
      v-for="group in capabilityGroups"
      :key="group.key"
      class="model-config-section"
    >
      <div class="model-config-section-title">{{ group.title }}</div>
      <div class="model-config-grid">
        <div
          v-for="capability in group.capabilities"
          :key="capability"
          class="page-card teacher-card model-config-card"
        >
          <div class="model-config-card-header">
            <div class="sub-title">{{ capabilityLabels[capability] }}</div>
            <el-tag size="small" effect="plain">{{ form.capabilities[capability]?.provider || '-' }}</el-tag>
          </div>

          <div class="model-config-form-grid">
            <label class="model-config-field">
              <span>Provider</span>
              <el-select v-model="form.capabilities[capability].provider" filterable allow-create>
                <el-option label="DashScope" value="dashscope" />
                <el-option label="OpenAI Compatible" value="openai_compatible" />
              </el-select>
            </label>

            <label class="model-config-field">
              <span>Base URL</span>
              <el-input v-model="form.capabilities[capability].baseUrl" placeholder="https://..." />
            </label>

            <label class="model-config-field">
              <span>API Key Ref</span>
              <el-input v-model="form.capabilities[capability].apiKeyRef" placeholder="dashscope_api_key" />
            </label>

            <label class="model-config-field">
              <span>模型名称</span>
              <el-input v-model="form.capabilities[capability].model" placeholder="model-name" />
            </label>

            <label class="model-config-field">
              <span>超时秒数</span>
              <el-input-number v-model="form.capabilities[capability].timeoutSeconds" :min="1" :max="300" :step="1" />
            </label>

            <label v-if="capability === 'student_embedding'" class="model-config-field">
              <span>向量维度</span>
              <el-input-number v-model="form.capabilities[capability].settings.dimensions" :min="1" :max="4096" :step="1" />
            </label>

            <label v-if="capability === 'student_image_generation'" class="model-config-field">
              <span>图片尺寸</span>
              <el-input v-model="form.capabilities[capability].settings.size" placeholder="1024*1024" />
            </label>

            <label v-if="capability === 'student_image_generation'" class="model-config-field">
              <span>图片数量</span>
              <el-input-number v-model="form.capabilities[capability].settings.count" :min="1" :max="1" :step="1" />
            </label>

            <label v-if="capability === 'student_image_generation'" class="model-config-field">
              <span>轮询间隔秒数</span>
              <el-input-number v-model="form.capabilities[capability].settings.pollIntervalSeconds" :min="0.5" :max="30" :step="0.5" />
            </label>
          </div>
        </div>
      </div>
    </section>

    <div class="page-card teacher-card model-config-retrieval">
      <div class="model-config-card-header">
        <div>
          <div class="sub-title">学生端检索策略</div>
        </div>
        <el-tag size="small" effect="plain">student QA</el-tag>
      </div>
      <div class="model-config-form-grid model-config-form-grid--retrieval">
        <label class="model-config-field">
          <span>向量检索</span>
          <el-switch v-model="form.retrieval.retrievalEnabled" inline-prompt active-text="开" inactive-text="关" />
        </label>
        <label class="model-config-field">
          <span>Top K</span>
          <el-input-number v-model="form.retrieval.retrievalTopK" :min="1" :max="10" :step="1" />
        </label>
      </div>
    </div>
  </TeacherLayout>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import TeacherLayout from '@/components/teacher/TeacherLayout.vue'
import Loading from '@/components/teacher/Loading.vue'
import ErrorTip from '@/components/teacher/ErrorTip.vue'
import { getModelRuntimeConfig, resetModelRuntimeConfig, updateModelRuntimeConfig } from '@/api/teacher'

const capabilityGroups = [
  {
    key: 'teacher',
    title: '教师端',
    capabilities: ['teacher_script_generation', 'teacher_structure_parse']
  },
  {
    key: 'student',
    title: '学生端',
    capabilities: ['student_text_chat', 'student_vision_chat', 'student_image_generation', 'student_embedding']
  }
]

const capabilityLabels = {
  teacher_script_generation: '讲稿生成',
  teacher_structure_parse: '结构化解析',
  student_text_chat: '文本问答',
  student_vision_chat: '图片理解',
  student_image_generation: '图片生成',
  student_embedding: 'Embedding'
}

const loading = ref(false)
const saving = ref(false)
const resetting = ref(false)
const errorCode = ref('')
const errorMsg = ref('')
const warnings = ref([])
const configUpdatedAt = ref('')
const overrideActive = ref(false)
const form = ref(createEmptyPayload())

function createEmptyCapability(capability) {
  return {
    capability,
    provider: '',
    baseUrl: '',
    apiKeyRef: '',
    model: '',
    timeoutSeconds: 60,
    settings: {}
  }
}

function createEmptyPayload() {
  const capabilities = {}
  capabilityGroups.flatMap((group) => group.capabilities).forEach((capability) => {
    capabilities[capability] = createEmptyCapability(capability)
  })
  return {
    capabilities,
    retrieval: {
      retrievalEnabled: true,
      retrievalTopK: 5
    }
  }
}

function normalizeCapability(capability, payload = {}) {
  const normalized = {
    ...createEmptyCapability(capability),
    ...payload,
    model: payload.model || payload.modelName || '',
    settings: { ...(payload.settings || {}) }
  }
  if (capability === 'student_embedding' && !normalized.settings.dimensions) {
    normalized.settings.dimensions = 1024
  }
  if (capability === 'student_image_generation') {
    normalized.settings = {
      size: normalized.settings.size || '1024*1024',
      count: Number(normalized.settings.count || 1),
      pollIntervalSeconds: Number(normalized.settings.pollIntervalSeconds || 2)
    }
  }
  return normalized
}

function applyResponse(data = {}) {
  const next = createEmptyPayload()
  Object.keys(next.capabilities).forEach((capability) => {
    next.capabilities[capability] = normalizeCapability(capability, data.capabilities?.[capability] || {})
  })
  next.retrieval = {
    ...next.retrieval,
    ...(data.retrieval || {})
  }
  form.value = next
  warnings.value = data.warnings || []
  configUpdatedAt.value = data.updatedAt || ''
  overrideActive.value = Boolean(data.overrideActive)
}

async function fetchConfig() {
  loading.value = true
  errorCode.value = ''
  errorMsg.value = ''
  try {
    const res = await getModelRuntimeConfig()
    applyResponse(res.data || {})
  } catch (error) {
    errorCode.value = error.code || 500
    errorMsg.value = error.msg || '读取模型配置失败。'
  } finally {
    loading.value = false
  }
}

function buildSubmitPayload() {
  const capabilities = {}
  Object.entries(form.value.capabilities).forEach(([capability, item]) => {
    capabilities[capability] = {
      capability,
      provider: item.provider,
      baseUrl: item.baseUrl,
      apiKeyRef: item.apiKeyRef,
      model: item.model,
      timeoutSeconds: item.timeoutSeconds,
      settings: item.settings || {}
    }
  })
  return {
    capabilities,
    retrieval: form.value.retrieval
  }
}

async function saveConfig() {
  saving.value = true
  try {
    const res = await updateModelRuntimeConfig(buildSubmitPayload())
    applyResponse(res.data || {})
    ElMessage.success('模型配置已保存')
  } catch (error) {
    ElMessage.error(error.msg || '保存模型配置失败')
  } finally {
    saving.value = false
  }
}

async function resetConfig() {
  try {
    await ElMessageBox.confirm('恢复后会清除数据库中的模型配置覆写。是否继续？', '恢复默认配置', {
      confirmButtonText: '恢复默认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch (_error) {
    return
  }
  resetting.value = true
  try {
    const res = await resetModelRuntimeConfig()
    applyResponse(res.data || {})
    ElMessage.success('已恢复默认模型配置')
  } catch (error) {
    ElMessage.error(error.msg || '恢复默认配置失败')
  } finally {
    resetting.value = false
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

onMounted(() => {
  fetchConfig()
})
</script>

<style scoped>
.teacher-card {
  border-radius: 22px;
  border: 1px solid #e7eef9;
  box-shadow: 0 16px 36px rgba(53, 82, 136, 0.08);
}

.model-config-summary {
  margin-bottom: 18px;
}

.model-config-toolbar {
  margin-top: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.model-config-status,
.model-config-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.model-config-status {
  color: #6f84a9;
  font-size: 13px;
}

.model-config-alert {
  margin-top: 16px;
}

.model-config-section {
  margin-top: 18px;
}

.model-config-section-title {
  margin: 0 0 12px 4px;
  color: #203b70;
  font-size: 16px;
  font-weight: 700;
}

.model-config-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(320px, 1fr));
  gap: 16px;
}

.model-config-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.model-config-form-grid {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(2, minmax(220px, 1fr));
  gap: 16px;
}

.model-config-form-grid--retrieval {
  grid-template-columns: repeat(2, minmax(180px, 240px));
}

.model-config-field {
  display: grid;
  gap: 10px;
  color: #314d81;
  font-size: 14px;
  font-weight: 600;
}

.model-config-retrieval {
  margin-top: 18px;
}

@media (max-width: 1100px) {
  .model-config-toolbar,
  .model-config-card-header {
    flex-direction: column;
    align-items: stretch;
  }

  .model-config-grid,
  .model-config-form-grid,
  .model-config-form-grid--retrieval {
    grid-template-columns: 1fr;
  }
}
</style>
