function toSafeNumber(value) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

export function getSectionSlideName(section) {
  const slideName = String(section?.slideName || '').trim()
  if (slideName) return slideName
  const fallbackTitle = String(section?.chapterTitle || '').trim()
  return fallbackTitle || '未命名幻灯片'
}

export function buildAggregatedChapterId(unitId, slideName) {
  return `${String(unitId || '')}::${String(slideName || '').trim()}`
}

export function buildAggregatedUnitChapters(unit) {
  const grouped = new Map()
  const rawSections = Array.isArray(unit?.chapters) ? unit.chapters : []
  const unitId = String(unit?.unitId || '')
  const unitTitle = unit?.unitTitle || ''

  rawSections.forEach((section) => {
    const slideName = getSectionSlideName(section)
    const chapterId = buildAggregatedChapterId(unitId, slideName)
    const pageNo = toSafeNumber(section?.pageNo)
    const progressPercent = toSafeNumber(section?.progressPercent)
    const masteryPercent = toSafeNumber(section?.masteryPercent)
    const sectionId = String(section?.sectionId || '')
    const existing = grouped.get(chapterId)

    if (!existing) {
      grouped.set(chapterId, {
        chapterId,
        unitId,
        unitTitle,
        chapterTitle: slideName,
        progressPercentSum: progressPercent,
        masteryPercentSum: masteryPercent,
        sectionCount: 1,
        firstPageNo: pageNo,
        representSectionId: sectionId
      })
      return
    }

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

  return [...grouped.values()]
    .map((item) => ({
      chapterId: item.chapterId,
      unitId: item.unitId,
      unitTitle: item.unitTitle,
      chapterTitle: item.chapterTitle,
      progressPercent: Math.round(item.progressPercentSum / item.sectionCount),
      masteryPercent: Math.round(item.masteryPercentSum / item.sectionCount),
      firstPageNo: item.firstPageNo,
      sectionCount: item.sectionCount,
      representSectionId: item.representSectionId
    }))
    .sort((left, right) => {
      const pageDiff = toSafeNumber(left.firstPageNo) - toSafeNumber(right.firstPageNo)
      if (pageDiff !== 0) return pageDiff
      return String(left.chapterTitle || '').localeCompare(String(right.chapterTitle || ''), 'zh-CN')
    })
}

export function buildAggregatedKnowledgeUnits(units) {
  return (Array.isArray(units) ? units : []).map((unit) => ({
    unitId: unit?.unitId || '',
    unitTitle: unit?.unitTitle || '',
    chapters: buildAggregatedUnitChapters(unit)
  }))
}

export function getSectionsForAggregatedChapter(units, unitId, chapterTitle) {
  const normalizedTitle = String(chapterTitle || '').trim()
  const targetUnit = (Array.isArray(units) ? units : []).find((unit) => String(unit?.unitId || '') === String(unitId || ''))
  const rawSections = Array.isArray(targetUnit?.chapters) ? targetUnit.chapters : []

  return rawSections
    .filter((section) => getSectionSlideName(section) === normalizedTitle)
    .sort((left, right) => {
      const pageDiff = toSafeNumber(left?.pageNo) - toSafeNumber(right?.pageNo)
      if (pageDiff !== 0) return pageDiff
      return String(left?.sectionId || '').localeCompare(String(right?.sectionId || ''), 'zh-CN')
    })
}

export function findAggregatedChapterForSection(units, sectionId) {
  for (const unit of Array.isArray(units) ? units : []) {
    const matchedSection = (Array.isArray(unit?.chapters) ? unit.chapters : []).find(
      (section) => String(section?.sectionId || '') === String(sectionId || '')
    )
    if (!matchedSection) continue

    const slideName = getSectionSlideName(matchedSection)
    return {
      unitId: unit?.unitId || '',
      chapterId: buildAggregatedChapterId(unit?.unitId || '', slideName),
      chapterTitle: slideName
    }
  }
  return null
}
