import request from './request'

export function syncUser(data) {
  return request({
    url: '/api/v1/platform/syncUser',
    method: 'post',
    data
  })
}

export function syncCourse(data) {
  return request({
    url: '/api/v1/platform/syncCourse',
    method: 'post',
    data
  })
}

export function createCourse(data) {
  return request({
    url: '/api/v1/platform/createCourse',
    method: 'post',
    data
  })
}

export function lessonParse(data) {
  return request({
    url: '/api/v1/lesson/parse',
    method: 'post',
    data
  })
}

export function getParseStatusAPI(parseId) {
  return request({
    url: `/api/v1/lesson/parse/${parseId}`,
    method: 'get'
  })
}

export function generateScript(data) {
  return request({
    url: '/api/v1/lesson/generateScript',
    method: 'post',
    data,
    timeout: 0
  })
}

export function getScript(scriptId) {
  return request({
    url: `/api/v1/scripts/${scriptId}`,
    method: 'get'
  })
}

export function updateScript(scriptId, data) {
  return request({
    url: `/api/v1/scripts/${scriptId}`,
    method: 'put',
    data
  })
}

export function generateAudio(data) {
  return request({
    url: '/api/v1/lesson/generateAudio',
    method: 'post',
    data,
    timeout: 0
  })
}

export function publishLesson(data) {
  return request({
    url: '/api/v1/lesson/publish',
    method: 'post',
    data
  })
}

export function saveScript(data) {
  return request({
    url: '/api/v1/lesson/saveScript',
    method: 'post',
    data
  })
}

export function getLessonStatus(data) {
  return request({
    url: '/api/v1/lesson/status',
    method: 'post',
    data
  })
}

export function getCoursewareAssets(params) {
  return request({
    url: '/api/v1/lesson/courseware/assets',
    method: 'get',
    params
  })
}

export function getParseScripts(parseId) {
  return request({
    url: `/api/v1/lesson/parse/${parseId}/scripts`,
    method: 'get'
  })
}

export function getScriptAudios(scriptId) {
  return request({
    url: `/api/v1/lesson/scripts/${scriptId}/audios`,
    method: 'get'
  })
}

export function getQaLabRuntimeConfig() {
  return request({
    url: '/api/v1/qa-lab/runtime-config',
    method: 'get'
  })
}

export function updateQaLabRuntimeConfig(data) {
  return request({
    url: '/api/v1/qa-lab/runtime-config',
    method: 'put',
    data
  })
}

export function resetQaLabRuntimeConfig(data = {}) {
  return request({
    url: '/api/v1/qa-lab/runtime-config/reset',
    method: 'post',
    data
  })
}

export function getQaLabCourseOutline(data) {
  return request({
    url: '/api/v1/qa-lab/course-outline',
    method: 'post',
    data
  })
}

export function runQaLabCompare(data) {
  return request({
    url: '/api/v1/qa-lab/compare',
    method: 'post',
    data,
    timeout: 120000
  })
}
