<template>
  <section
    v-if="suggestion && suggestion.paceMode && suggestion.paceMode !== 'continue'"
    class="pace-card"
    :class="[`mode-${suggestion.paceMode}`, `trigger-${suggestion.triggerSource || 'manual'}`]"
  >
    <div class="pace-card-head">
      <div>
        <div class="pace-card-kicker">{{ modeLabel }}</div>
        <h2>{{ blockTitle }}</h2>
      </div>
      <button
        v-if="suggestion.allowSkip"
        type="button"
        class="pace-skip-button"
        @click="$emit('skip')"
      >
        先跳过
      </button>
    </div>

    <p class="pace-card-summary">{{ suggestion.reasonSummary || fallbackSummary }}</p>
    <p v-if="blockDescription" class="pace-card-description">{{ blockDescription }}</p>

    <div v-if="focusPoints.length" class="pace-focus-list">
      <span
        v-for="item in focusPoints"
        :key="item"
        class="pace-focus-chip"
      >
        {{ item }}
      </span>
    </div>

    <div class="pace-card-foot">
      <button
        type="button"
        class="pace-action-button"
        @click="$emit('apply')"
      >
        {{ actionLabel }}
      </button>
      <span v-if="targetLabel" class="pace-target-label">{{ targetLabel }}</span>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  suggestion: {
    type: Object,
    default: null
  }
})

defineEmits(['apply', 'skip'])

const blockPayload = computed(() => props.suggestion?.suggestedBlockPayload || {})
const focusPoints = computed(() => blockPayload.value.focusPoints || [])
const actionLabel = computed(() => blockPayload.value.actionLabel || '按建议学习')
const blockTitle = computed(() => blockPayload.value.title || '学习节奏建议')
const blockDescription = computed(() => blockPayload.value.description || '')
const targetLabel = computed(() => {
  const pageNo = Number(blockPayload.value.targetPageNo || 0)
  if (!pageNo) return ''
  return `建议从第 ${pageNo} 页开始`
})
const modeLabel = computed(() => {
  if (props.suggestion?.paceMode === 'supplement') return '补充学习'
  if (props.suggestion?.paceMode === 'reinforce') return '强化回看'
  return '继续学习'
})
const fallbackSummary = computed(() => {
  if (props.suggestion?.paceMode === 'supplement') {
    return '先补一段过渡讲解，再继续推进当前章节。'
  }
  if (props.suggestion?.paceMode === 'reinforce') {
    return '先回看关键内容，再继续问答或练习。'
  }
  return ''
})
</script>

<style scoped>
.pace-card {
  padding: 18px 20px;
  border-radius: 24px;
  border: 1px solid #d7e3f8;
  box-shadow: 0 14px 28px rgba(38, 67, 131, 0.08);
  background:
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.9), transparent 36%),
    linear-gradient(135deg, #fff8ea 0%, #f9efe0 100%);
}

.pace-card.mode-reinforce {
  background:
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.88), transparent 36%),
    linear-gradient(135deg, #fff1ec 0%, #fde2d7 100%);
}

.pace-card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.pace-card-kicker {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #86622f;
}

.pace-card.mode-reinforce .pace-card-kicker {
  color: #9a4b39;
}

.pace-card-head h2 {
  margin: 6px 0 0;
  font-size: 22px;
  line-height: 1.15;
  color: #24436f;
}

.pace-skip-button,
.pace-action-button {
  border: 1px solid #d3c08e;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.82);
  color: #6e5327;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease, border-color 0.18s ease;
}

.pace-card.mode-reinforce .pace-skip-button,
.pace-card.mode-reinforce .pace-action-button {
  border-color: #d8a58e;
  color: #8a4637;
}

.pace-skip-button {
  min-width: 88px;
  height: 38px;
  padding: 0 16px;
}

.pace-action-button {
  min-width: 144px;
  height: 42px;
  padding: 0 18px;
}

.pace-skip-button:hover,
.pace-action-button:hover {
  transform: translateY(-1px);
  background: #ffffff;
}

.pace-card-summary,
.pace-card-description {
  margin: 14px 0 0;
  font-size: 15px;
  line-height: 1.7;
  color: #4b628e;
}

.pace-focus-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.pace-focus-chip {
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.82);
  color: #516c9c;
  font-size: 13px;
  font-weight: 700;
  border: 1px solid rgba(194, 208, 234, 0.9);
}

.pace-card-foot {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 18px;
}

.pace-target-label {
  font-size: 13px;
  color: #6f84a7;
  font-weight: 600;
}

@media (max-width: 768px) {
  .pace-card {
    padding: 16px;
  }

  .pace-card-head {
    flex-direction: column;
  }

  .pace-card-foot {
    flex-direction: column;
    align-items: stretch;
  }

  .pace-action-button,
  .pace-skip-button {
    width: 100%;
  }
}
</style>
