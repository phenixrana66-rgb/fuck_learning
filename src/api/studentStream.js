import { buildSignedPayload } from '@/utils/sign'
import { getStudentPlatformToken } from '@/utils/platform'

function buildStudentApiUrl(path) {
  const apiBase = import.meta.env.VITE_STUDENT_API_BASE || '/student-api'
  const normalizedPath = path.startsWith('/') ? path : `/${path}`

  if (/^https?:\/\//i.test(apiBase)) {
    return `${apiBase.replace(/\/$/, '')}${normalizedPath}`
  }

  return `${apiBase.startsWith('/') ? apiBase : `/${apiBase}`}${normalizedPath}`
}

function createAbortError() {
  const error = new Error('请求已终止')
  error.name = 'AbortError'
  return error
}

function parseEventBlock(block, onEvent) {
  const lines = block
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)

  const dataLines = lines
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trim())

  if (!dataLines.length) return
  onEvent(JSON.parse(dataLines.join('\n')))
}

function normalizeStreamText(text) {
  return `${text || ''}`.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
}

function consumeEventBlocks(buffer, onEvent) {
  let nextBuffer = buffer
  let splitIndex = nextBuffer.indexOf('\n\n')

  while (splitIndex >= 0) {
    const block = nextBuffer.slice(0, splitIndex)
    nextBuffer = nextBuffer.slice(splitIndex + 2)
    parseEventBlock(block, onEvent)
    splitIndex = nextBuffer.indexOf('\n\n')
  }

  return nextBuffer
}

function dispatchStreamEvent(event, { onStart, onDelta, onDone, setDonePayload }) {
  if (event.type === 'start') {
    onStart?.(event)
    return
  }
  if (event.type === 'delta') {
    onDelta?.(event.delta || '')
    return
  }
  if (event.type === 'done') {
    const payload = event.data || null
    setDonePayload(payload)
    onDone?.(payload)
    return
  }
  if (event.type === 'error') {
    throw new Error(event.message || 'AI 问答失败')
  }
}

export async function streamLessonInteraction(payload, handlers = {}) {
  const { signal, onStart, onDelta, onDone } = handlers
  const token = getStudentPlatformToken()
  const response = await fetch(buildStudentApiUrl('/api/v1/qa/interact/stream'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json; charset=UTF-8',
      ...(token
        ? {
            Authorization: `Bearer ${token}`,
            'X-Platform-Token': token
          }
        : {})
    },
    body: JSON.stringify(buildSignedPayload(payload || {})),
    signal
  })

  if (!response.ok) {
    let message = 'AI 问答失败'
    try {
      const data = await response.json()
      message = data?.msg || message
    } catch (_error) {
      if (response.status === 401) message = '免登鉴权失败，请重新进入页面'
    }
    throw new Error(message)
  }

  if (!response.body) {
    throw new Error('AI 流式响应不可用')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let donePayload = null

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break

      buffer += normalizeStreamText(decoder.decode(value, { stream: true }))
      buffer = consumeEventBlocks(buffer, (event) => {
        dispatchStreamEvent(event, {
          onStart,
          onDelta,
          onDone,
          setDonePayload: (payload) => {
            donePayload = payload
          }
        })
      })
    }

    const tail = normalizeStreamText(buffer + decoder.decode())
    if (tail.trim()) {
      consumeEventBlocks(`${tail}\n\n`, (event) => {
        dispatchStreamEvent(event, {
          onStart,
          onDelta,
          onDone,
          setDonePayload: (payload) => {
            donePayload = payload
          }
        })
      })
    }

    return donePayload
  } catch (error) {
    if (signal?.aborted) {
      throw createAbortError()
    }
    throw error
  } finally {
    try {
      reader.releaseLock()
    } catch (_error) {
      // ignore release errors
    }
  }
}
