import { ref } from 'vue'
import { ElMessage } from 'element-plus'

function buildStudentWsUrls(path) {
  const apiBase = import.meta.env.VITE_STUDENT_API_BASE || '/student-api'
  const normalizedPath = path.startsWith('/') ? path : `/${path}`

  if (/^https?:\/\//i.test(apiBase)) {
    const base = new URL(apiBase)
    const protocol = base.protocol === 'https:' ? 'wss:' : 'ws:'
    const pathname = base.pathname.replace(/\/$/, '')
    return [`${protocol}//${base.host}${pathname}${normalizedPath}`]
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const pathname = apiBase.startsWith('/') ? apiBase : `/${apiBase}`
  const proxyUrl = `${protocol}//${window.location.host}${pathname}${normalizedPath}`
  const urls = [proxyUrl]

  if (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost') {
    urls.push(`${protocol}//127.0.0.1:3001${pathname}${normalizedPath}`)
    urls.push(`${protocol}//localhost:3001${pathname}${normalizedPath}`)
  }

  return [...new Set(urls)]
}

function openWebSocket(url, timeoutMs = 2500) {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(url)
    let settled = false
    const timer = window.setTimeout(() => {
      finish(() => {
        try {
          socket.close()
        } catch (_error) {
          // ignore close failure
        }
        reject(new Error(`WebSocket open timeout: ${url}`))
      })
    }, timeoutMs)

    function finish(callback) {
      if (settled) return
      settled = true
      window.clearTimeout(timer)
      socket.onopen = null
      socket.onerror = null
      socket.onclose = null
      callback()
    }

    socket.onopen = () => finish(() => resolve(socket))
    socket.onerror = () => finish(() => reject(new Error(`WebSocket open failed: ${url}`)))
    socket.onclose = () => finish(() => reject(new Error(`WebSocket closed during open: ${url}`)))
  })
}

async function openStudentAsrSocket(path) {
  const urls = buildStudentWsUrls(path)
  let lastError = null
  for (const url of urls) {
    try {
      return await openWebSocket(url)
    } catch (error) {
      lastError = error
    }
  }
  throw lastError || new Error('WebSocket open failed')
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = typeof reader.result === 'string' ? reader.result.split(',', 2)[1] || '' : ''
      resolve(result)
    }
    reader.onerror = () => reject(reader.error || new Error('音频数据读取失败'))
    reader.readAsDataURL(blob)
  })
}

function pickMimeType() {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']
  if (typeof MediaRecorder === 'undefined') return ''
  return candidates.find((item) => MediaRecorder.isTypeSupported?.(item)) || ''
}

function getSpeechRecognitionCtor() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

function formatErrorMessage(message, fallback) {
  const normalized = `${message || ''}`.trim()
  return normalized || fallback
}

export function useRealtimeAsr({ getContext, onTranscript, onRecordingStart }) {
  const isRecording = ref(false)
  const voiceLoading = ref(false)
  const recordingSeconds = ref(0)

  let ws = null
  let mediaRecorder = null
  let mediaStream = null
  let speechRecognition = null
  let timerId = null
  let chunks = []
  let sendQueued = false
  let sending = false
  let stopQueued = false
  let seq = 0
  let lastDeliveredText = ''
  let closedIntentionally = false
  const mimeType = pickMimeType()

  function stopTimer() {
    if (timerId) {
      window.clearInterval(timerId)
      timerId = null
    }
  }

  function startTimer() {
    stopTimer()
    recordingSeconds.value = 0
    timerId = window.setInterval(() => {
      recordingSeconds.value += 1
    }, 1000)
  }

  function resetRuntime() {
    sendQueued = false
    sending = false
    stopQueued = false
    seq = 0
    lastDeliveredText = ''
    chunks = []
    closedIntentionally = false
    stopTimer()
    recordingSeconds.value = 0
  }

  function cleanupSocket() {
    if (!ws) return
    ws.onopen = null
    ws.onmessage = null
    ws.onerror = null
    ws.onclose = null
    try {
      ws.close()
    } catch (_error) {
      // ignore close failure
    }
    ws = null
  }

  function cleanupMedia() {
    if (speechRecognition) {
      speechRecognition.onstart = null
      speechRecognition.onresult = null
      speechRecognition.onerror = null
      speechRecognition.onend = null
      try {
        speechRecognition.stop()
      } catch (_error) {
        // ignore stop failure
      }
      speechRecognition = null
    }
    if (mediaRecorder) {
      mediaRecorder.ondataavailable = null
      mediaRecorder.onstop = null
      mediaRecorder = null
    }
    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop())
      mediaStream = null
    }
  }

  function cleanup() {
    cleanupMedia()
    cleanupSocket()
    isRecording.value = false
    voiceLoading.value = false
    resetRuntime()
  }

  async function flushAudio(final = false) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    if (sending) {
      sendQueued = true
      if (final) stopQueued = true
      return
    }
    if (!chunks.length) {
      if (final) cleanup()
      return
    }

    sending = true
    voiceLoading.value = true
    const blob = new Blob(chunks, { type: mimeType || 'audio/webm' })
    chunks = []
    const audioBase64 = await blobToBase64(blob)
    seq += 1
    ws.send(JSON.stringify({
      type: 'audio',
      seq,
      audioBase64,
      fileName: 'voice-question.webm',
      final
    }))
  }

  async function startRecording() {
    cleanup()
    resetRuntime()
    voiceLoading.value = true
    onRecordingStart?.()
    const SpeechRecognitionCtor = getSpeechRecognitionCtor()

    if (SpeechRecognitionCtor) {
      try {
        speechRecognition = new SpeechRecognitionCtor()
        speechRecognition.lang = 'zh-CN'
        speechRecognition.continuous = true
        speechRecognition.interimResults = true
        speechRecognition.maxAlternatives = 1
        speechRecognition.onstart = () => {
          isRecording.value = true
          voiceLoading.value = false
          startTimer()
        }
        speechRecognition.onresult = (event) => {
          const transcript = Array.from(event.results || [])
            .map((result) => result?.[0]?.transcript || '')
            .join('')
            .trim()
          if (transcript) {
            onTranscript?.(transcript, Boolean(event.results?.[event.results.length - 1]?.isFinal))
          }
        }
        speechRecognition.onerror = (event) => {
          if (event?.error === 'aborted') return
          ElMessage.error(formatErrorMessage(event?.message, '语音识别失败，请检查麦克风权限后重试'))
          cleanup()
        }
        speechRecognition.onend = () => {
          cleanup()
        }
        speechRecognition.start()
        return
      } catch (_error) {
        speechRecognition = null
      }
    }

    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      ElMessage.warning('当前浏览器不支持语音输入，请改用文字提问')
      cleanup()
      return
    }

    const context = getContext?.() || {}
    try {
      ws = await openStudentAsrSocket('/ws/qa/asr')
    } catch (_error) {
      ElMessage.error('实时语音识别连接失败')
      cleanup()
      return
    }

    ws.send(JSON.stringify({
      type: 'start',
      studentId: context.studentId || '',
      lessonId: context.lessonId || '',
      sectionId: context.sectionId || ''
    }))

    ws.onmessage = async (event) => {
      const payload = JSON.parse(event.data || '{}')

      if (payload.type === 'ready') {
        try {
          mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
          mediaRecorder = mimeType ? new MediaRecorder(mediaStream, { mimeType }) : new MediaRecorder(mediaStream)
          mediaRecorder.ondataavailable = async (mediaEvent) => {
            if (!mediaEvent.data?.size) return
            chunks.push(mediaEvent.data)
            if (!sending) {
              await flushAudio(false)
            } else {
              sendQueued = true
            }
          }
          mediaRecorder.onstop = async () => {
            await flushAudio(true)
          }
          mediaRecorder.start(1500)
          isRecording.value = true
          voiceLoading.value = false
          startTimer()
        } catch (_error) {
          ElMessage.error('麦克风启动失败，请检查浏览器权限')
          cleanup()
        }
        return
      }

      if (payload.type === 'error') {
        ElMessage.error(formatErrorMessage(payload.message, '语音识别失败'))
        cleanup()
        return
      }

      if (payload.type !== 'transcript') return

      const text = `${payload.text || ''}`.trim()
      if (text && text !== lastDeliveredText) {
        lastDeliveredText = text
        onTranscript?.(text, Boolean(payload.final))
      }

      sending = false

      if (sendQueued && !payload.final) {
        sendQueued = false
        await flushAudio(stopQueued)
        if (stopQueued) stopQueued = false
        return
      }

      if (payload.final) {
        cleanup()
      }
    }

    ws.onerror = () => {
      ElMessage.error('实时语音识别连接失败')
      cleanup()
    }

    ws.onclose = () => {
      if (!closedIntentionally && (voiceLoading.value || isRecording.value)) {
        ElMessage.error('实时语音识别连接失败')
      }
      cleanup()
    }
  }

  async function stopRecording() {
    if (!isRecording.value) return
    stopTimer()
    isRecording.value = false
    voiceLoading.value = true
    if (speechRecognition) {
      try {
        speechRecognition.stop()
      } catch (_error) {
        cleanup()
      }
      return
    }
    stopQueued = true
    mediaRecorder?.stop()
  }

  async function toggleRecording() {
    if (isRecording.value) {
      await stopRecording()
      return
    }
    await startRecording()
  }

  function cleanupRealtimeAsr() {
    closedIntentionally = true
    cleanup()
  }

  return {
    isRecording,
    voiceLoading,
    recordingSeconds,
    toggleRecording,
    cleanupRealtimeAsr
  }
}
