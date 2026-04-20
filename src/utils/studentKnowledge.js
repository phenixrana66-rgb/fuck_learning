function toSafeNumber(value) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function stripKnownSlideExtension(value) {
  return String(value || '').trim().replace(/\.(pptx|ppt|pdf)$/i, '').trim()
}

function getRawSlideName(section) {
  return stripKnownSlideExtension(section?.slideName || '')
}

function toChineseNumber(value) {
  const safeValue = Math.max(1, Number(value || 1))
  const digits = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九']
  if (safeValue < 10) return digits[safeValue]
  if (safeValue < 20) return `十${safeValue % 10 === 0 ? '' : digits[safeValue % 10]}`
  if (safeValue < 100) {
    const tens = Math.floor(safeValue / 10)
    const ones = safeValue % 10
    return `${digits[tens]}十${ones === 0 ? '' : digits[ones]}`
  }
  return String(safeValue)
}

function buildFallbackChapterTitle(index) {
  return `第${toChineseNumber(index)}章`
}

export function buildAggregatedChapterId(unitId, chapterKey) {
  return `${String(unitId || '')}::${String(chapterKey || '').trim()}`
}

function buildAggregatedUnitState(unit) {
  const rawSections = Array.isArray(unit?.chapters) ? unit.chapters : []
  const unitId = String(unit?.unitId || '')
  const unitTitle = unit?.unitTitle || ''
  const grouped = new Map()

  rawSections.forEach((section, index) => {
    const rawSlideName = getRawSlideName(section)
    const uniqueKey = rawSlideName
      ? `slide:${rawSlideName}`
      : `generated:${String(section?.sectionId || index + 1)}`
    const pageNo = toSafeNumber(section?.pageNo)
    const progressPercent = toSafeNumber(section?.progressPercent)
    const masteryPercent = toSafeNumber(section?.masteryPercent)
    const sectionId = String(section?.sectionId || '')
    const existing = grouped.get(uniqueKey)

    if (!existing) {
      grouped.set(uniqueKey, {
        uniqueKey,
        unitId,
        unitTitle,
        rawSlideName,
        hasExplicitSlideName: Boolean(rawSlideName),
        sections: [section],
        progressPercentSum: progressPercent,
        masteryPercentSum: masteryPercent,
        sectionCount: 1,
        firstPageNo: pageNo,
        representSectionId: sectionId
      })
      return
    }

    existing.sections.push(section)
    existing.progressPercentSum += progressPercent
    existing.masteryPercentSum += masteryPercent
    existing.sectionCount += 1

    const existingPageNo = toSafeNumber(existing.firstPageNo)
    const shouldReplaceRepresentative = pageNo < existingPageNo
      || (pageNo === existingPageNo && sectionId && (!existing.representSectionId || sectionId < existing.representSectionId))

    if (shouldReplaceRepresentative) {
      existing.firstPageNo = pageNo
      existing.representSectionId = sectionId
    }
  })

  const sortedBuckets = [...grouped.values()].sort((left, right) => {
    const pageDiff = toSafeNumber(left.firstPageNo) - toSafeNumber(right.firstPageNo)
    if (pageDiff !== 0) return pageDiff
    return String(left.rawSlideName || '').localeCompare(String(right.rawSlideName || ''), 'zh-CN')
  })

  const chapters = sortedBuckets.map((bucket, index) => {
    const chapterTitle = bucket.hasExplicitSlideName ? bucket.rawSlideName : buildFallbackChapterTitle(index + 1)
    const chapterKey = bucket.hasExplicitSlideName
      ? chapterTitle
      : `generated-${index + 1}-${bucket.representSectionId || index + 1}`
    return {
      chapterId: buildAggregatedChapterId(unitId, chapterKey),
      unitId: bucket.unitId,
      unitTitle: bucket.unitTitle,
      chapterTitle,
      isGeneratedTitle: !bucket.hasExplicitSlideName,
      progressPercent: Math.round(bucket.progressPercentSum / bucket.sectionCount),
      masteryPercent: Math.round(bucket.masteryPercentSum / bucket.sectionCount),
      firstPageNo: bucket.firstPageNo,
      sectionCount: bucket.sectionCount,
      representSectionId: bucket.representSectionId,
      sections: bucket.sections
    }
  })

  const sectionChapterMap = new Map()
  chapters.forEach((chapter) => {
    chapter.sections.forEach((section) => {
      sectionChapterMap.set(String(section?.sectionId || ''), chapter)
    })
  })

  return {
    unitId,
    unitTitle,
    chapters,
    sectionChapterMap
  }
}

export function buildAggregatedUnitChapters(unit) {
  return buildAggregatedUnitState(unit).chapters.map((chapter) => ({
    chapterId: chapter.chapterId,
    unitId: chapter.unitId,
    unitTitle: chapter.unitTitle,
    chapterTitle: chapter.chapterTitle,
    isGeneratedTitle: chapter.isGeneratedTitle,
    progressPercent: chapter.progressPercent,
    masteryPercent: chapter.masteryPercent,
    firstPageNo: chapter.firstPageNo,
    sectionCount: chapter.sectionCount,
    representSectionId: chapter.representSectionId
  }))
}

export function buildAggregatedKnowledgeUnits(units) {
  return (Array.isArray(units) ? units : []).map((unit) => ({
    unitId: unit?.unitId || '',
    unitTitle: unit?.unitTitle || '',
    chapters: buildAggregatedUnitChapters(unit)
  }))
}

export function getSectionsForAggregatedChapter(units, unitId, chapterTitle, chapterId = '') {
  const targetUnit = (Array.isArray(units) ? units : []).find((unit) => String(unit?.unitId || '') === String(unitId || ''))
  if (!targetUnit) return []

  const state = buildAggregatedUnitState(targetUnit)
  const matchedChapter = state.chapters.find((chapter) => {
    if (chapterId) return chapter.chapterId === String(chapterId)
    return chapter.chapterTitle === String(chapterTitle || '').trim()
  })

  return [...(matchedChapter?.sections || [])].sort((left, right) => {
    const pageDiff = toSafeNumber(left?.pageNo) - toSafeNumber(right?.pageNo)
    if (pageDiff !== 0) return pageDiff
    return String(left?.sectionId || '').localeCompare(String(right?.sectionId || ''), 'zh-CN')
  })
}

export function findAggregatedChapterForSection(units, sectionId) {
  for (const unit of Array.isArray(units) ? units : []) {
    const state = buildAggregatedUnitState(unit)
    const matchedChapter = state.sectionChapterMap.get(String(sectionId || ''))
    if (!matchedChapter) continue

    return {
      unitId: matchedChapter.unitId,
      chapterId: matchedChapter.chapterId,
      chapterTitle: matchedChapter.chapterTitle
    }
  }
  return null
}
