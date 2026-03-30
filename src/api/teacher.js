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

export function lessonParse(data) {
  return request({
    url: '/api/v1/lesson/parse',
    method: 'post',
    data
  })
}

export function generateScript(data) {
  return request({
    url: '/api/v1/lesson/generateScript',
    method: 'post',
    data
  })
}

export function generateAudio(data) {
  return request({
    url: '/api/v1/lesson/generateAudio',
    method: 'post',
    data
  })
}