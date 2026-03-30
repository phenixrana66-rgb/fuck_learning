import CryptoJS from 'crypto-js'

/**
 * 将对象按 key 升序扁平拼接
 * 规则：key=value&key2=value2...
 */
function sortAndJoin(params = {}) {
  const keys = Object.keys(params)
    .filter((key) => params[key] !== undefined && params[key] !== null && params[key] !== '')
    .sort()

  return keys
    .map((key) => {
      const value = typeof params[key] === 'object'
        ? JSON.stringify(params[key])
        : String(params[key])
      return `${key}=${value}`
    })
    .join('&')
}

/**
 * 生成 enc 签名
 * 规则：sortedParams + staticKey + time
 */
export function generateEnc(params = {}, time) {
  const staticKey = import.meta.env.VITE_STATIC_KEY || ''
  const sortedStr = sortAndJoin(params)
  const raw = `${sortedStr}${staticKey}${time}`
  return CryptoJS.MD5(raw).toString()
}

export function buildSignedPayload(payload = {}) {
  const time = Date.now().toString()
  const enc = generateEnc(payload, time)
  return {
    ...payload,
    time,
    enc
  }
}