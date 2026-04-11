const COURSE_BLUEPRINTS = [
  {
    lessonId: 'L10001',
    courseId: 'C2025001',
    courseName: '材料力学智慧课程 (15期2025春夏)',
    teacherName: '王志恒',
    category: '共享课程',
    lastStudyAt: '2026-03-29 09:10',
    units: [
      { unitTitle: '基本概念', chapters: ['轴向拉伸与压缩', '应力与应变', '材料力学性能'] },
      { unitTitle: '强度与变形', chapters: ['剪切与挤压', '扭转变形', '梁的弯曲'] },
      { unitTitle: '压杆稳定', chapters: ['压杆稳定'] }
    ]
  },
  {
    lessonId: 'L10002',
    courseId: 'C2025002',
    courseName: '电工技术l',
    teacherName: '陈思远',
    category: '在线学分课',
    lastStudyAt: '2026-03-29 09:25',
    units: [
      { unitTitle: '电路基础', chapters: ['电路模型与基本定律', '电阻电路分析', '戴维宁定理'] },
      { unitTitle: '交流电路', chapters: ['正弦交流电基础', '相量法分析', '三相交流电路'] }
    ]
  },
  {
    lessonId: 'L10003',
    courseId: 'C2025003',
    courseName: '画法几何与机械制图',
    teacherName: '周明皓',
    category: '校内学分课',
    lastStudyAt: '2026-03-29 09:40',
    units: [
      { unitTitle: '投影基础', chapters: ['点线面的投影', '基本体三视图', '截交线分析'] },
      { unitTitle: '机械制图', chapters: ['组合体读图', '尺寸标注规范', '装配图识读'] }
    ]
  },
  {
    lessonId: 'L10004',
    courseId: 'C2025004',
    courseName: '汽车构造2025',
    teacherName: '赵凯',
    category: '共享课程',
    lastStudyAt: '2026-03-29 10:05',
    units: [
      { unitTitle: '发动机系统', chapters: ['曲柄连杆机构', '配气机构', '燃油供给系统'] },
      { unitTitle: '底盘系统', chapters: ['传动系统构成', '转向系统原理', '制动系统结构'] }
    ]
  },
  {
    lessonId: 'L10005',
    courseId: 'C2025005',
    courseName: '制冷原理与设备',
    teacherName: '刘宁',
    category: '在线学分课',
    lastStudyAt: '2026-03-29 10:20',
    units: [
      { unitTitle: '制冷循环', chapters: ['蒸汽压缩式制冷原理', '制冷剂状态变化', '制冷循环热力分析'] },
      { unitTitle: '制冷设备', chapters: ['压缩机结构与分类', '冷凝器与蒸发器', '节流装置与控制'] }
    ]
  },
  {
    lessonId: 'L10006',
    courseId: 'C2025006',
    courseName: '建筑冷热源',
    teacherName: '何雨辰',
    category: '校内学分课',
    lastStudyAt: '2026-03-29 10:35',
    units: [
      { unitTitle: '冷热源概论', chapters: ['冷热源系统分类', '热泵系统原理', '冷热源方案比较'] },
      { unitTitle: '工程应用', chapters: ['锅炉房系统设计', '冷站运行控制', '节能评价方法'] }
    ]
  },
  {
    lessonId: 'L10007',
    courseId: 'C2025007',
    courseName: '自动控制原理',
    teacherName: '孙婷',
    category: '共享课程',
    lastStudyAt: '2026-03-29 10:50',
    units: [
      { unitTitle: '控制系统基础', chapters: ['控制系统组成', '传递函数建模', '典型环节特性'] },
      { unitTitle: '系统分析与校正', chapters: ['时域分析法', '频域分析法', '校正装置设计'] }
    ]
  }
]

function buildPressureStabilityPages() {
  const pageSummaries = {
    1: '理解压杆稳定平衡条件与基本受力状态。',
    2: '掌握临界载荷的定义与核心判断依据。',
    3: '理解欧拉公式的形式、假设条件与适用范围。',
    4: '认识长细比变化对压杆稳定性的直接影响。',
    5: '结合工程案例理解压杆稳定校核。'
  }

  return Array.from({ length: 65 }, (_, index) => {
    const pageNo = index + 1
    return {
      pageNo,
      pageTitle: `第 ${pageNo} 页`,
      pageSummary: pageSummaries[pageNo] || `查看压杆稳定课件第 ${pageNo} 页内容。`,
      pptPageUrl: `/lesson-previews/pressure-stability/page-${pageNo}.png`,
      parsedContent: pageSummaries[pageNo] || `本页为压杆稳定课件第 ${pageNo} 页，建议结合 AI 学习导读继续理解重点。`
    }
  })
}

function buildUnits(lessonId, unitSpecs) {
  let pageNo = 1
  return unitSpecs.map((unit, unitIndex) => ({
    unitId: `${lessonId}-U${unitIndex + 1}`,
    unitTitle: unit.unitTitle,
    chapters: unit.chapters.map((chapterTitle, chapterIndex) => {
      const chapter = {
        chapterId: `${lessonId}-U${unitIndex + 1}-C${chapterIndex + 1}`,
        chapterTitle,
        progressPercent: 0,
        masteryPercent: 0,
        pageNo,
        summary: `围绕“${chapterTitle}”展开知识讲解、课件学习与课堂习题训练。`,
        knowledgePoints: [chapterTitle, unit.unitTitle, '核心概念']
      }

      if (lessonId === 'L10001' && unit.unitTitle === '压杆稳定' && chapterTitle === '压杆稳定') {
        chapter.guideContent = '本章围绕压杆稳定的基本概念、临界载荷、欧拉公式以及工程中的稳定校核展开。建议先按页完成课件学习，再结合 AI 导读梳理关键公式与工程应用。'
        chapter.learningPages = buildPressureStabilityPages()
      }

      pageNo += 1
      return chapter
    })
  }))
}

function buildLesson(blueprint) {
  const units = buildUnits(blueprint.lessonId, blueprint.units)
  const chapters = units.flatMap((unit) => unit.chapters)
  const currentChapter = chapters[0] || {}
  return {
    lessonId: blueprint.lessonId,
    courseId: blueprint.courseId,
    courseName: blueprint.courseName,
    lessonName: blueprint.courseName,
    teacherName: blueprint.teacherName,
    category: blueprint.category,
    status: 'inProgress',
    progressPercent: 0,
    masteryPercent: 0,
    coverImage: '',
    currentPage: currentChapter.pageNo || 1,
    currentKnowledgePointName: currentChapter.chapterTitle || '待学习章节',
    currentChapter: currentChapter.chapterTitle || '待学习章节',
    questionCount: 0,
    lastStudyAt: blueprint.lastStudyAt,
    units
  }
}

export const FRONTEND_TEST_LESSONS = COURSE_BLUEPRINTS.map(buildLesson)

export function getFrontendTestLessons() {
  return JSON.parse(JSON.stringify(FRONTEND_TEST_LESSONS))
}

export function findFrontendTestLesson(lessonId) {
  return getFrontendTestLessons().find((item) => item.lessonId === lessonId) || null
}
