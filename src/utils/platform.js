const SCRIPT_TASK_KEY = 'scriptTask'
const SCRIPT_RESULT_KEY = 'scriptResult'

function readJsonStorage(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch (error) {
    return fallback
  }
}

function writeJsonStorage(key, value) {
  localStorage.setItem(key, JSON.stringify(value ?? {}))
}

function hasScriptStructure(value) {
  return Array.isArray(value?.scriptStructure) && value.scriptStructure.length > 0
}

function extractScriptResult(task) {
  if (!task || (!task.scriptId && !hasScriptStructure(task))) {
    return {}
  }

  return {
    scriptId: task.scriptId || '',
    parseId: task.parseId || '',
    teachingStyle: task.teachingStyle || 'standard',
    speechSpeed: task.speechSpeed || 'normal',
    customOpening: task.customOpening || '',
    scriptStructure: hasScriptStructure(task) ? task.scriptStructure : [],
    version: task.version || 1,
    status: task.status || '',
    savedAt: task.savedAt || '',
    editUrl: task.editUrl || '',
    audioGenerateUrl: task.audioGenerateUrl || ''
  }
}

export function getQueryParams() {
  const url = new URL(window.location.href)
  const params = {}
  url.searchParams.forEach((value, key) => {
    params[key] = value
  })
  return params
}

export function getPlatformToken() {
  const query = getQueryParams()
  return query.token || sessionStorage.getItem('platformToken') || ''
}

export function savePlatformToken(token) {
  if (token) {
    sessionStorage.setItem('platformToken', token)
  }
}

export function ensurePlatformToken(fallbackToken = '') {
  const currentToken = getPlatformToken()
  if (currentToken) {
    return currentToken
  }

  if (fallbackToken) {
    savePlatformToken(fallbackToken)
    return fallbackToken
  }

  return ''
}

export function saveTeacherProfile(profile) {
  localStorage.setItem('teacherProfile', JSON.stringify(profile || {}))
}

export function getTeacherProfile() {
  return JSON.parse(localStorage.getItem('teacherProfile') || '{}')
}

export function saveCourseList(list) {
  localStorage.setItem('courseList', JSON.stringify(list || []))
}

export function getCourseList() {
  return JSON.parse(localStorage.getItem('courseList') || '[]')
}

export function saveCurrentCourse(course) {
  localStorage.setItem('currentCourse', JSON.stringify(course || {}))
}

export function getCurrentCourse() {
  return JSON.parse(localStorage.getItem('currentCourse') || '{}')
}

export function saveParseResult(data) {
  localStorage.setItem('parseResult', JSON.stringify(data || {}))
}

export function getParseResult() {
  return JSON.parse(localStorage.getItem('parseResult') || '{}')
}

export function saveScriptTask(data) {
  writeJsonStorage(SCRIPT_TASK_KEY, data || {})
}

export function getScriptTask() {
  return readJsonStorage(SCRIPT_TASK_KEY, {})
}

export function patchScriptTask(patch) {
  const next = {
    ...getScriptTask(),
    ...(patch || {}),
    updatedAt: new Date().toISOString()
  }
  saveScriptTask(next)
  return next
}

export function clearScriptTask() {
  localStorage.removeItem(SCRIPT_TASK_KEY)
}

export function saveScriptResult(data) {
  const next = data || {}
  writeJsonStorage(SCRIPT_RESULT_KEY, next)

  if (Object.keys(next).length) {
    patchScriptTask({
      parseId: next.parseId || '',
      teachingStyle: next.teachingStyle || 'standard',
      speechSpeed: next.speechSpeed || 'normal',
      customOpening: next.customOpening || '',
      scriptId: next.scriptId || '',
      scriptStructure: hasScriptStructure(next) ? next.scriptStructure : [],
      version: next.version || 1,
      status: next.status || 'success',
      savedAt: next.savedAt || '',
      editUrl: next.editUrl || '',
      audioGenerateUrl: next.audioGenerateUrl || ''
    })
  }
}

export function getScriptResult() {
  const cached = readJsonStorage(SCRIPT_RESULT_KEY, {})
  if (Object.keys(cached).length) {
    return cached
  }

  const restored = extractScriptResult(getScriptTask())
  return Object.keys(restored).length ? restored : {}
}

export function saveAudioResult(data) {
  localStorage.setItem('audioResult', JSON.stringify(data || {}))
}

export function getAudioResult() {
  return JSON.parse(localStorage.getItem('audioResult') || '{}')
}

export function saveStudentProfile(profile) {
  localStorage.setItem('studentProfile', JSON.stringify(profile || {}))
}

export function getStudentProfile() {
  return JSON.parse(localStorage.getItem('studentProfile') || '{}')
}

export function saveStudentLessonList(list) {
  localStorage.setItem('studentLessonList', JSON.stringify(list || []))
}

export function getStudentLessonListCache() {
  return JSON.parse(localStorage.getItem('studentLessonList') || '[]')
}

export function saveStudentProgressCache(lessonId, progress) {
  const cache = JSON.parse(localStorage.getItem('studentProgressCache') || '{}')
  cache[lessonId] = progress || {}
  localStorage.setItem('studentProgressCache', JSON.stringify(cache))
}

export function getStudentProgressCache(lessonId) {
  const cache = JSON.parse(localStorage.getItem('studentProgressCache') || '{}')
  return cache[lessonId] || {}
}

export function saveStudentQaHistory(lessonId, history) {
  const cache = JSON.parse(localStorage.getItem('studentQaHistory') || '{}')
  cache[lessonId] = history || []
  localStorage.setItem('studentQaHistory', JSON.stringify(cache))
}

export function getStudentQaHistory(lessonId) {
  const cache = JSON.parse(localStorage.getItem('studentQaHistory') || '{}')
  return cache[lessonId] || []
}

export function saveStudentQaSessions(lessonId, sessions) {
  const cache = JSON.parse(localStorage.getItem('studentQaSessions') || '{}')
  cache[lessonId] = sessions || []
  localStorage.setItem('studentQaSessions', JSON.stringify(cache))
}

export function getStudentQaSessions(lessonId) {
  const cache = JSON.parse(localStorage.getItem('studentQaSessions') || '{}')
  return cache[lessonId] || []
}

export function saveStudentRecentChapterVisit(visit) {
  if (!visit?.lessonId || !visit?.chapterId) return
  const list = JSON.parse(localStorage.getItem('studentRecentChapterVisits') || '[]')
  const normalized = Array.isArray(list) ? list : []
  const filtered = normalized.filter((item) => !(item.lessonId === visit.lessonId && item.chapterId === visit.chapterId))
  filtered.unshift(visit)
  localStorage.setItem('studentRecentChapterVisits', JSON.stringify(filtered.slice(0, 3)))
}

export function getStudentRecentChapterVisits() {
  const list = JSON.parse(localStorage.getItem('studentRecentChapterVisits') || '[]')
  return Array.isArray(list) ? list : []
}
