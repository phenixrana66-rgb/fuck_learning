UNDERSTANDING_LABELS = {"weak": "未理解", "partial": "部分理解", "complete": "完全理解"}


class LearningService:
    def __init__(self, adapter):
        self.adapter = adapter

    def _find_anchor(self, lesson, anchor_id=None, page_no=None):
        anchors = lesson.get("anchors", [])
        if anchor_id:
            for anchor in anchors:
                if anchor.get("anchorId") == anchor_id:
                    return dict(anchor)
        if page_no:
            for anchor in anchors:
                if anchor.get("pageNo") == page_no:
                    return dict(anchor)
        return dict(anchors[0]) if anchors else {}

    def _find_slide(self, lesson, page_no=None):
        slides = lesson.get("slides", [])
        for slide in slides:
            if slide.get("pageNo") == page_no:
                return dict(slide)
        return dict(slides[0]) if slides else {}

    def voice_to_text(self, file_name):
        lowered = (file_name or "").lower()
        if "voice" in lowered or "record" in lowered:
            return "请结合当前章节，解释关键概念与典型应用场景。"
        return "请帮我梳理这一章节的重点内容。"

    def interact(self, lesson_id, question, anchor_id, page_no):
        lesson = self.adapter.play_lesson(lesson_id)
        anchor = self._find_anchor(lesson, anchor_id=anchor_id, page_no=page_no)
        slide = self._find_slide(lesson, page_no=anchor.get("pageNo"))
        related = slide.get("knowledgePoints", [])[:]
        question = question or ""
        if any(keyword in question for keyword in ["不会", "不懂", "没明白", "不理解"]):
            understanding = "weak"
        elif any(keyword in question for keyword in ["区别", "关系", "为什么", "如何"]):
            understanding = "partial"
        else:
            understanding = "complete"
        current_page = anchor.get("pageNo") or 1
        resume_page = max(1, current_page - 1) if understanding == "weak" else current_page
        resume_anchor = self._find_anchor(lesson, page_no=resume_page)
        answer = (
            f"当前章节是《{slide.get('title', '当前知识点')}》。建议你先掌握"
            f"{', '.join(related[:2]) or '本章重点'}，再结合课件内容理解它的典型应用。"
            f"本章核心说明是：{slide.get('summary', '本章节围绕核心概念、方法和例题展开。')}"
        )
        return {
            "answer": answer,
            "relatedKnowledgePoints": related,
            "understandingLevel": understanding,
            "understandingLabel": UNDERSTANDING_LABELS[understanding],
            "resumeAnchor": resume_anchor,
            "weakPoints": related[:2] if understanding != "complete" else [],
        }

    def adjust_progress(self, lesson_id, anchor_id, page_no, understanding_level, weak_points):
        lesson = self.adapter.play_lesson(lesson_id)
        anchor = self._find_anchor(lesson, anchor_id=anchor_id, page_no=page_no)
        if understanding_level == "complete":
            return {**anchor, "weakPoints": weak_points or []}
        current_page = anchor.get("pageNo") or 1
        target_page = max(1, current_page - 1 if understanding_level == "weak" else current_page)
        adjusted = self._find_anchor(lesson, page_no=target_page)
        slide = self._find_slide(lesson, page_no=adjusted.get("pageNo"))
        return {**adjusted, "weakPoints": weak_points or slide.get("knowledgePoints", [])[:2]}

    def resume(self, lesson_id, anchor_id):
        lesson = self.adapter.play_lesson(lesson_id)
        anchor = self._find_anchor(lesson, anchor_id=anchor_id)
        return {
            "audioUrl": lesson.get("audioUrl", ""),
            "resumeTime": anchor.get("startTime", 0),
            "anchorId": anchor.get("anchorId"),
            "anchorTitle": anchor.get("anchorTitle"),
            "pageNo": anchor.get("pageNo"),
        }
