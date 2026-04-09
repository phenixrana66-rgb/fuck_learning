from datetime import datetime
from uuid import uuid4

from backend.app.qa.schemas import QAInteractRequest, VoiceToTextRequest

_QA_SESSIONS: dict[str, dict] = {}


def voice_to_text(payload: VoiceToTextRequest) -> dict:
    return {
        "text": "这是根据语音内容转写出的示例问题。",
        "confidence": 0.98,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }


def interact(payload: QAInteractRequest) -> dict:
    answer_id = _build_id("ans")
    understanding_level = "partial"
    history = [item.model_dump() for item in payload.historyQa]
    history.append(
        {
            "question": payload.questionContent,
            "answer": "系统已基于当前章节和证据片段生成回答。",
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    session = {
        "sessionId": payload.sessionId,
        "lessonId": payload.lessonId,
        "currentSectionId": payload.currentSectionId,
        "historyQa": history,
        "understandingLevel": understanding_level,
    }
    _QA_SESSIONS[payload.sessionId] = session
    return {
        "answerId": answer_id,
        "answerContent": "这是一个受控问答示例回答，重点解释当前章节的核心概念，并保持与课件证据一致。",
        "answerType": "text",
        "relatedKnowledge": {
            "knowledgeId": "know001",
            "knowledgeName": "当前章节核心知识点",
            "relatedSectionId": payload.currentSectionId,
        },
        "suggestions": [
            "要不要继续看这个概念的适用条件？",
            "需要结合一个例子继续理解吗？",
        ],
        "understandingLevel": understanding_level,
        "evidencePages": [3, 4],
        "evidenceSpans": [
            "证据片段 1：课件中对概念定义的表述。",
            "证据片段 2：课件中对应用场景的说明。",
        ],
        "relatedNodeIds": ["node-01-01"],
    }


def get_session(session_id: str) -> dict:
    session = _QA_SESSIONS.get(session_id)
    if session is None:
        session = {
            "sessionId": session_id,
            "lessonId": "lesson-demo",
            "currentSectionId": "sec001",
            "historyQa": [],
            "understandingLevel": "none",
        }
    return session


def _build_id(prefix: str) -> str:
    return f"{prefix}{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid4().hex[:6]}"
