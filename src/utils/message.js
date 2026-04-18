import { ElMessage } from 'element-plus'

const recentMessageMap = new Map()
const DEDUPE_WINDOW_MS = 2000

function canShowMessage(key) {
  const now = Date.now()
  const lastShownAt = recentMessageMap.get(key) || 0

  if (now - lastShownAt < DEDUPE_WINDOW_MS) {
    return false
  }

  recentMessageMap.set(key, now)
  return true
}

export function showErrorMessage(message) {
  const normalized = String(message || '').trim()
  if (!normalized) return
  if (!canShowMessage(`error:${normalized}`)) return

  ElMessage({
    type: 'error',
    message: normalized,
    grouping: true
  })
}
