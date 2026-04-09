from copy import deepcopy

from mock_data import get_default_progress, get_notifications, get_player, get_student, MOCK_PLAYERS


class ChaoxingAdapter:
    def __init__(self):
        self._student = get_student()
        self._players = {lesson_id: get_player(lesson_id) for lesson_id in MOCK_PLAYERS.keys()}
        self._progress = {lesson_id: get_default_progress(lesson_id) for lesson_id in self._players.keys()}
        self._notifications = get_notifications()

    def _flatten_chapters(self, lesson_id):
        lesson = self._players[lesson_id]
        return [chapter for unit in lesson.get("units", []) for chapter in unit.get("chapters", [])]

    def _average_progress(self, lesson_id):
        chapters = self._flatten_chapters(lesson_id)
        if not chapters:
            return 0
        return round(sum(chapter.get("progressPercent", 0) for chapter in chapters) / len(chapters))

    def _find_chapter(self, lesson_id, page_no=None, chapter_id=None):
        for chapter in self._flatten_chapters(lesson_id):
            if chapter_id and chapter.get("chapterId") == chapter_id:
                return chapter
            if page_no and chapter.get("pageNo") == page_no:
                return chapter
        chapters = self._flatten_chapters(lesson_id)
        return chapters[0] if chapters else None

    def _sync_player_meta(self, lesson_id):
        player = self._players[lesson_id]
        progress = self._average_progress(lesson_id)
        page_no = self._progress.get(lesson_id, {}).get("pageNo", 1)
        current_chapter = self._find_chapter(lesson_id, page_no=page_no)
        player["progressPercent"] = progress
        player["currentPage"] = current_chapter.get("pageNo", 1) if current_chapter else 1
        player["currentKnowledgePointName"] = current_chapter.get("chapterTitle", "") if current_chapter else ""
        return player

    def _serialize_lesson(self, lesson_id):
        player = self._sync_player_meta(lesson_id)
        return {
            "lessonId": player["lessonId"],
            "courseId": player["courseId"],
            "courseName": player["courseName"],
            "lessonName": player["lessonName"],
            "teacherName": player["teacherName"],
            "category": player["category"],
            "status": "completed" if player["progressPercent"] >= 100 else "inProgress",
            "progressPercent": player["progressPercent"],
            "masteryPercent": 0,
            "coverImage": player.get("coverImage", ""),
            "currentPage": player.get("currentPage", 1),
            "currentKnowledgePointName": player.get("currentKnowledgePointName", ""),
            "currentChapter": player.get("currentKnowledgePointName", ""),
            "questionCount": player.get("questionCount", 0),
            "lastStudyAt": player.get("lastStudyAt", "2026-03-29 10:00"),
            "units": deepcopy(player.get("units", [])),
        }

    def verify(self, token):
        if token not in {"student_demo_token_001", "test_student_token_001"}:
            raise PermissionError("invalid token")
        return {
            "student": deepcopy(self._student),
            "lessons": self.get_student_lessons(self._student["studentId"]),
        }

    def get_student_lessons(self, student_id):
        return [self._serialize_lesson(lesson_id) for lesson_id in self._players.keys()]

    def get_progress(self, lesson_id):
        progress = deepcopy(self._progress.get(lesson_id, get_default_progress(lesson_id)))
        progress["progressPercent"] = self._average_progress(lesson_id)
        return progress

    def play_lesson(self, lesson_id):
        player = deepcopy(self._players.get(lesson_id, next(iter(self._players.values()))))
        player["progressPercent"] = self._average_progress(player["lessonId"])
        return player

    def update_progress(self, lesson_id, payload):
        if lesson_id not in self._players:
            return deepcopy(payload)

        current = self._progress.get(lesson_id, get_default_progress(lesson_id))
        current.update(payload)
        self._progress[lesson_id] = current

        page_no = payload.get("pageNo") or current.get("pageNo") or 1
        chapter = self._find_chapter(lesson_id, page_no=page_no)
        if chapter is not None:
            chapter["progressPercent"] = max(0, min(100, int(payload.get("progressPercent", chapter.get("progressPercent", 0)))))

        player = self._sync_player_meta(lesson_id)
        current["progressPercent"] = player["progressPercent"]
        current["anchorTitle"] = player["currentKnowledgePointName"]
        return deepcopy(current)

    def list_notifications(self, student_id):
        return [
            {
                "id": item["id"],
                "title": item["title"],
                "summary": item["summary"],
                "createdAt": item["createdAt"],
                "type": item["type"],
                "read": item["read"],
            }
            for item in deepcopy(self._notifications)
        ]

    def get_notification_detail(self, student_id, notification_id):
        for item in self._notifications:
            if item["id"] == notification_id:
                return deepcopy(item)
        return None

    def mark_notification_read(self, student_id, notification_id):
        for item in self._notifications:
            if item["id"] == notification_id:
                item["read"] = True
                return {"notificationId": notification_id, "read": True}
        return None