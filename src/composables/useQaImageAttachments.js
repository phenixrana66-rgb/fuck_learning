import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'

export const QA_IMAGE_MAX_COUNT = 5
export const QA_IMAGE_MAX_SIZE_BYTES = 10 * 1024 * 1024
export const QA_IMAGE_ACCEPT = 'image/jpeg,image/png,image/webp'
export const QA_IMAGE_MIME_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp'])

function createAttachmentId(seed = '') {
  return `${seed || 'qa-image'}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function normalizeAttachment(raw = {}, index = 0) {
  const url = `${raw.url || ''}`.trim()
  const dataUrl = `${raw.dataUrl || ''}`.trim()
  const storageKey = `${raw.storageKey || ''}`.trim()
  const name = `${raw.name || `图片${index + 1}`}`.trim()
  return {
    id: raw.id || storageKey || url || createAttachmentId(name),
    type: 'image',
    name,
    mimeType: `${raw.mimeType || ''}`.trim(),
    size: Number(raw.size || 0) || 0,
    url,
    dataUrl,
    storageKey,
    storageProvider: `${raw.storageProvider || 'local'}`.trim(),
    previewUrl: url || dataUrl
  }
}

export function cloneQaImageAttachments(attachments = []) {
  return (attachments || []).map((item, index) => normalizeAttachment(item, index))
}

export function buildQaImageAttachmentPayloads(attachments = []) {
  return cloneQaImageAttachments(attachments).map((item) => {
    const payload = {
      type: 'image',
      name: item.name,
      mimeType: item.mimeType,
      size: item.size
    }
    if (item.storageKey && item.url) {
      payload.storageProvider = item.storageProvider || 'local'
      payload.storageKey = item.storageKey
      payload.url = item.url
      return payload
    }
    if (item.dataUrl) {
      payload.dataUrl = item.dataUrl
    }
    return payload
  })
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(`${reader.result || ''}`)
    reader.onerror = () => reject(reader.error || new Error('读取图片失败'))
    reader.readAsDataURL(file)
  })
}

function assertValidFile(file) {
  if (!QA_IMAGE_MIME_TYPES.has(file.type)) {
    throw new Error('仅支持 JPG、PNG、WEBP 图片')
  }
  if (file.size > QA_IMAGE_MAX_SIZE_BYTES) {
    throw new Error('单张图片大小不能超过 10MB')
  }
}

export function useQaImageAttachments() {
  const draftAttachments = ref([])
  const pickerKey = ref(0)

  const hasAttachments = computed(() => draftAttachments.value.length > 0)

  async function addFiles(fileList) {
    const files = Array.from(fileList || [])
    if (!files.length) return false
    if (draftAttachments.value.length + files.length > QA_IMAGE_MAX_COUNT) {
      ElMessage.warning(`最多上传 ${QA_IMAGE_MAX_COUNT} 张图片`)
      return false
    }
    const next = [...draftAttachments.value]
    for (const file of files) {
      try {
        assertValidFile(file)
        const dataUrl = await readFileAsDataUrl(file)
        next.push(normalizeAttachment({
          id: createAttachmentId(file.name),
          name: file.name,
          mimeType: file.type,
          size: file.size,
          dataUrl
        }, next.length))
      } catch (error) {
        ElMessage.warning(error?.message || '图片上传失败')
      }
    }
    draftAttachments.value = next
    pickerKey.value += 1
    return true
  }

  async function handleFileChange(event) {
    const files = event?.target?.files || []
    await addFiles(files)
    if (event?.target) event.target.value = ''
  }

  function removeAttachment(attachmentId) {
    draftAttachments.value = draftAttachments.value.filter((item) => item.id !== attachmentId)
  }

  function clearAttachments() {
    draftAttachments.value = []
    pickerKey.value += 1
  }

  function replaceAttachments(attachments = []) {
    draftAttachments.value = cloneQaImageAttachments(attachments)
    pickerKey.value += 1
  }

  return {
    draftAttachments,
    hasAttachments,
    pickerKey,
    addFiles,
    handleFileChange,
    removeAttachment,
    clearAttachments,
    replaceAttachments
  }
}
