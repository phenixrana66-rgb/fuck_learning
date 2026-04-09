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

export function adjustStudentProgress(data) {
  return request({
    url: '/api/v1/progress/adjust',
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
