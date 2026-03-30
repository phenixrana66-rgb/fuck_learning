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

export function saveScriptResult(data) {
  localStorage.setItem('scriptResult', JSON.stringify(data || {}))
}

export function getScriptResult() {
  return JSON.parse(localStorage.getItem('scriptResult') || '{}')
}

export function saveAudioResult(data) {
  localStorage.setItem('audioResult', JSON.stringify(data || {}))
}

export function getAudioResult() {
  return JSON.parse(localStorage.getItem('audioResult') || '{}')
}
