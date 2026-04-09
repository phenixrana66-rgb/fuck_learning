import CryptoJS from 'crypto-js'

function normalizeValue(value) {
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }

  return String(value)
}

function sortAndJoin(params = {}) {
  return Object.keys(params)
    .filter((key) => params[key] !== undefined && params[key] !== null && params[key] !== '')
    .sort()
    .map((key) => `${key}=${normalizeValue(params[key])}`)
    .join('&')
}

export function generateEnc(params = {}, time) {
  const staticKey = import.meta.env.VITE_STATIC_KEY || 'chaoxing-ai-static-key'
  const sortedStr = sortAndJoin(params)
  return CryptoJS.MD5(`${sortedStr}${staticKey}${time}`).toString()
}

export function buildSignedPayload(payload = {}) {
  const time = Date.now().toString()
  return {
    ...payload,
    time,
    enc: generateEnc(payload, time)
  }
}
