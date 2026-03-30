from copy import deepcopy


MOCK_STUDENT = {
    "studentId": "S2026001",
    "userName": "左睿涛",
    "studentName": "左睿涛",
    "schoolName": "河海大学",
    "collegeName": "计算机与软件学院",
    "majorName": "软件工程",
    "className": "AI 智课实验班",
    "studyDays": 0,
}


COMMON_AI_TOOLS = [
    {"id": "tool-1", "name": "AI陪练", "desc": "围绕当前章节做概念追问、例题拆解和重点复盘。"},
    {"id": "tool-2", "name": "AI阅读助手", "desc": "辅助梳理课件重点、术语定义和章节摘要。"},
    {"id": "tool-3", "name": "AI写作助手", "desc": "帮助整理实验报告、课程摘要和学习反思。"},
    {"id": "tool-4", "name": "AI文档问答", "desc": "基于课程资料快速定位相关知识内容。"},
    {"id": "tool-5", "name": "AI科研趋势", "desc": "延展相关领域的新技术、新案例和工程应用。"},
]


COURSE_BLUEPRINTS = [
    {
        "lessonId": "L10001",
        "courseId": "C2025001",
        "courseName": "材料力学智慧课程 (15期2025春夏)",
        "teacherName": "王志恒",
        "category": "共享课程",
        "lastStudyAt": "2026-03-29 09:10",
        "units": [
            ("基本概念", ["轴向拉伸与压缩", "应力与应变", "材料力学性能"]),
            ("强度与变形", ["剪切与挤压", "扭转变形", "梁的弯曲"]),
        ],
    },
    {
        "lessonId": "L10002",
        "courseId": "C2025002",
        "courseName": "电工技术l",
        "teacherName": "陈思远",
        "category": "在线学分课",
        "lastStudyAt": "2026-03-29 09:25",
        "units": [
            ("电路基础", ["电路模型与基本定律", "电阻电路分析", "戴维宁定理"]),
            ("交流电路", ["正弦交流电基础", "相量法分析", "三相交流电路"]),
        ],
    },
    {
        "lessonId": "L10003",
        "courseId": "C2025003",
        "courseName": "画法几何与机械制图",
        "teacherName": "周明皓",
        "category": "校内学分课",
        "lastStudyAt": "2026-03-29 09:40",
        "units": [
            ("投影基础", ["点线面的投影", "基本体三视图", "截交线分析"]),
            ("机械制图", ["组合体读图", "尺寸标注规范", "装配图识读"]),
        ],
    },
    {
        "lessonId": "L10004",
        "courseId": "C2025004",
        "courseName": "汽车构造2025",
        "teacherName": "赵凯",
        "category": "共享课程",
        "lastStudyAt": "2026-03-29 10:05",
        "units": [
            ("发动机系统", ["曲柄连杆机构", "配气机构", "燃油供给系统"]),
            ("底盘系统", ["传动系统构成", "转向系统原理", "制动系统结构"]),
        ],
    },
    {
        "lessonId": "L10005",
        "courseId": "C2025005",
        "courseName": "制冷原理与设备",
        "teacherName": "刘宁",
        "category": "在线学分课",
        "lastStudyAt": "2026-03-29 10:20",
        "units": [
            ("制冷循环", ["蒸汽压缩式制冷原理", "制冷剂状态变化", "制冷循环热力分析"]),
            ("制冷设备", ["压缩机结构与分类", "冷凝器与蒸发器", "节流装置与控制"]),
        ],
    },
    {
        "lessonId": "L10006",
        "courseId": "C2025006",
        "courseName": "建筑冷热源",
        "teacherName": "何雨辰",
        "category": "校内学分课",
        "lastStudyAt": "2026-03-29 10:35",
        "units": [
            ("冷热源概论", ["冷热源系统分类", "热泵系统原理", "冷热源方案比较"]),
            ("工程应用", ["锅炉房系统设计", "冷站运行控制", "节能评价方法"]),
        ],
    },
    {
        "lessonId": "L10007",
        "courseId": "C2025007",
        "courseName": "自动控制原理",
        "teacherName": "孙婷",
        "category": "共享课程",
        "lastStudyAt": "2026-03-29 10:50",
        "units": [
            ("控制系统基础", ["控制系统组成", "传递函数建模", "典型环节特性"]),
            ("系统分析与校正", ["时域分析法", "频域分析法", "校正装置设计"]),
        ],
    },
]


MOCK_NOTIFICATIONS = [
    {
        "id": "N10001",
        "title": "课程测试数据已初始化",
        "summary": "7 门课程的章节、进度与掌握度测试数据已经准备完成。",
        "content": "当前学生端已经注入 7 门课程的测试数据。首页课程进度初始均为 0%，后续会根据各章节学习进度的平均值自动计算课程总进度。",
        "createdAt": "2026-03-29 11:20",
        "type": "课程通知",
        "read": False,
    },
    {
        "id": "N10002",
        "title": "AI 互动室入口已开放",
        "summary": "进入课程详情页后，可在顶部功能切换区进入 AI 互动室。",
        "content": "课程详情页支持顶部功能切换。进入“AI 互动室”后，可使用文字输入、语音提问，并按需收起右侧 AI 工具栏。",
        "createdAt": "2026-03-29 10:58",
        "type": "学习提醒",
        "read": False,
    },
    {
        "id": "N10003",
        "title": "课程封面图片区已预留",
        "summary": "课程封面图区域已经留空，便于后续替换真实本地图片。",
        "content": "首页课程卡片和课程详情页的图片展示位都已保留为空白占位。当前不会自动填充默认图片，方便后续直接替换为课程实图。",
        "createdAt": "2026-03-29 10:36",
        "type": "资源说明",
        "read": False,
    },
    {
        "id": "N10004",
        "title": "知识学习页已切换为模块化布局",
        "summary": "知识学习页采用知识单元与章节卡片的模块化排布。",
        "content": "课程详情页默认进入“知识学习”。每个知识单元下展示具体章节卡片，卡片内包含章节名、学习进度和掌握度。当前初始值均为 0%。",
        "createdAt": "2026-03-29 09:42",
        "type": "系统更新",
        "read": False,
    },
]


def _build_units(unit_specs, lesson_id):
    units = []
    page_no = 1
    for unit_index, (unit_title, chapters) in enumerate(unit_specs, start=1):
        chapter_items = []
        for chapter_index, chapter_title in enumerate(chapters, start=1):
            chapter_items.append(
                {
                    "chapterId": f"{lesson_id}-U{unit_index}-C{chapter_index}",
                    "chapterTitle": chapter_title,
                    "progressPercent": 0,
                    "masteryPercent": 0,
                    "pageNo": page_no,
                    "summary": f"围绕“{chapter_title}”展开知识讲解、课件学习与课堂习题训练。",
                    "knowledgePoints": [chapter_title, unit_title, "核心概念"],
                }
            )
            page_no += 1
        units.append(
            {
                "unitId": f"{lesson_id}-U{unit_index}",
                "unitTitle": unit_title,
                "chapters": chapter_items,
            }
        )
    return units


def _flatten_chapters(units):
    return [chapter for unit in units for chapter in unit["chapters"]]


def _average_progress(units):
    chapters = _flatten_chapters(units)
    if not chapters:
        return 0
    return round(sum(chapter["progressPercent"] for chapter in chapters) / len(chapters))


def _build_player(blueprint):
    units = _build_units(blueprint["units"], blueprint["lessonId"])
    chapters = _flatten_chapters(units)
    slides = [
        {
            "pageNo": chapter["pageNo"],
            "title": chapter["chapterTitle"],
            "summary": chapter["summary"],
            "knowledgePoints": chapter["knowledgePoints"],
        }
        for chapter in chapters
    ]
    anchors = [
        {
            "anchorId": f"{blueprint['lessonId']}-A{index}",
            "anchorTitle": chapter["chapterTitle"],
            "pageNo": chapter["pageNo"],
            "startTime": (index - 1) * 90,
        }
        for index, chapter in enumerate(chapters, start=1)
    ]
    return {
        "lessonId": blueprint["lessonId"],
        "courseId": blueprint["courseId"],
        "courseName": blueprint["courseName"],
        "lessonName": blueprint["courseName"],
        "teacherName": blueprint["teacherName"],
        "category": blueprint["category"],
        "coverImage": "",
        "units": units,
        "slides": slides,
        "anchors": anchors,
        "progressPercent": _average_progress(units),
        "masteryPercent": 0,
        "currentPage": 1,
        "currentKnowledgePointName": chapters[0]["chapterTitle"],
        "questionCount": 0,
        "lastStudyAt": blueprint["lastStudyAt"],
        "audioUrl": "https://www.w3schools.com/html/horse.mp3",
        "duration": max(len(chapters), 1) * 90,
        "aiWelcome": f"Hi，左睿涛同学，围绕《{blueprint['courseName']}》开始提问吧。",
        "aiPrompt": "可以输入文字问题，也可以直接使用语音输入。",
        "aiTools": deepcopy(COMMON_AI_TOOLS),
    }


MOCK_PLAYERS = {
    blueprint["lessonId"]: _build_player(blueprint)
    for blueprint in COURSE_BLUEPRINTS
}


DEFAULT_PROGRESS = {
    lesson_id: {
        "anchorId": player["anchors"][0]["anchorId"],
        "anchorTitle": player["anchors"][0]["anchorTitle"],
        "pageNo": 1,
        "currentTime": 0,
        "progressPercent": 0,
        "understandingLevel": "partial",
        "weakPoints": [],
    }
    for lesson_id, player in MOCK_PLAYERS.items()
}


def _build_lesson_summary(player):
    chapters = _flatten_chapters(player["units"])
    current_chapter = next(
        (chapter for chapter in chapters if chapter["pageNo"] == player.get("currentPage", 1)),
        chapters[0],
    )
    progress = _average_progress(player["units"])
    return {
        "lessonId": player["lessonId"],
        "courseId": player["courseId"],
        "courseName": player["courseName"],
        "lessonName": player["lessonName"],
        "teacherName": player["teacherName"],
        "category": player["category"],
        "status": "completed" if progress >= 100 else "inProgress",
        "progressPercent": progress,
        "masteryPercent": 0,
        "coverImage": player.get("coverImage", ""),
        "currentPage": current_chapter["pageNo"],
        "currentKnowledgePointName": current_chapter["chapterTitle"],
        "currentChapter": current_chapter["chapterTitle"],
        "questionCount": player.get("questionCount", 0),
        "lastStudyAt": player.get("lastStudyAt", "2026-03-29 10:00"),
        "units": deepcopy(player["units"]),
    }


def get_student():
    return deepcopy(MOCK_STUDENT)


def get_lessons():
    return [_build_lesson_summary(player) for player in deepcopy(list(MOCK_PLAYERS.values()))]


def get_player(lesson_id):
    fallback = next(iter(MOCK_PLAYERS.values()))
    return deepcopy(MOCK_PLAYERS.get(lesson_id, fallback))


def get_default_progress(lesson_id):
    fallback_key = next(iter(DEFAULT_PROGRESS.keys()))
    return deepcopy(DEFAULT_PROGRESS.get(lesson_id, DEFAULT_PROGRESS[fallback_key]))


def get_notifications():
    return deepcopy(MOCK_NOTIFICATIONS)
