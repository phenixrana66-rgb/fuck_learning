import request from './studentRequest'

export function verifyStudentAuth(data) {
  return request({
    url: '/auth/verify',
    data
  })
}

export function getStudentLessonList(data) {
  return request({
    url: '/api/v1/getStudentLessonList',
    data
  })
}

export function getStudentRecentChapters(data) {
  return request({
    url: '/api/v1/recentChapters/list',
    data
  })
}

export function saveStudentRecentChapter(data) {
  return request({
    url: '/api/v1/recentChapters/save',
    data
  })
}

export function getStudentProgress(data) {
  return request({
    url: '/api/v1/progress/get',
    data
  })
}

export function trackStudentProgress(data) {
  return request({
    url: '/api/v1/progress/track',
    data
  })
}

export function playStudentLesson(data) {
  return request({
    url: '/api/v1/lesson/play',
    data
  })
}

export function getStudentSectionDetail(data) {
  return request({
    url: '/api/v1/lesson/section/detail',
    data
  })
}

export function voiceToText(data) {
  return request({
    url: '/api/v1/qa/voiceToText',
    data
  })
}

export function interactWithLesson(data) {
  return request({
    url: '/api/v1/qa/interact',
    data
  })
}

export function getStudentQaSessions(data) {
  return request({
    url: '/api/v1/qa/sessions/list',
    data
  })
}

export function saveStudentQaSession(data) {
  return request({
    url: '/api/v1/qa/sessions/save',
    data
  })
}

export function adjustStudentProgress(data) {
  return request({
    url: '/api/v1/progress/adjust',
    data
  })
}

export function markStudentPageRead(data) {
  return request({
    url: '/api/v1/progress/page/read',
    data
  })
}

export function resumeStudentLesson(data) {
  return request({
    url: '/api/v1/lesson/resume',
    data
  })
}

export function getStudentNotifications(data) {
  return request({
    url: '/api/v1/notifications/list',
    data
  })
}

export function getStudentNotificationDetail(data) {
  return request({
    url: '/api/v1/notifications/detail',
    data
  })
}

export function markStudentNotificationRead(data) {
  return request({
    url: '/api/v1/notifications/read',
    data
  })
}
