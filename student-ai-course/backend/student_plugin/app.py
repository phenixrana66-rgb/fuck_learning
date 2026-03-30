from flask import Flask, jsonify, request
from flask_cors import CORS

from config import Config
from services.chaoxing_adapter import ChaoxingAdapter
from services.learning_service import LearningService
from services.signing import verify_signature

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, supports_credentials=True)

adapter = ChaoxingAdapter()
learning_service = LearningService(adapter)


def response(code=200, msg="success", data=None, request_id=None):
    return jsonify(
        {
            "code": code,
            "msg": msg,
            "data": data,
            "requestId": request_id or f"req-{id(data)}",
        }
    )


def request_payload():
    return request.get_json(silent=True) or {}


def require_signature():
    payload = request_payload()
    if not verify_signature(payload, app.config["STATIC_KEY"]):
        return None, response(401, "签名校验失败", None)
    return payload, None


@app.post("/auth/verify")
def auth_verify():
    payload, error = require_signature()
    if error:
        return error, 401

    token = payload.get("token") or request.headers.get("X-Platform-Token", "")
    try:
        data = adapter.verify(token)
        return response(200, "success", data)
    except PermissionError:
        return response(401, "免登 token 无效", None), 401


@app.post("/api/v1/getStudentLessonList")
def get_student_lesson_list():
    payload, error = require_signature()
    if error:
        return error, 401
    return response(200, "success", {"lessons": adapter.get_student_lessons(payload.get("studentId"))})


@app.post("/api/v1/progress/get")
def get_progress():
    payload, error = require_signature()
    if error:
        return error, 401
    return response(200, "success", adapter.get_progress(payload.get("lessonId")))


@app.post("/api/v1/progress/track")
def track_progress():
    payload, error = require_signature()
    if error:
        return error, 401

    updated = adapter.update_progress(
        payload.get("lessonId"),
        {
            "anchorId": payload.get("anchorId"),
            "anchorTitle": payload.get("anchorTitle"),
            "pageNo": payload.get("pageNo"),
            "currentTime": payload.get("currentTime"),
            "progressPercent": payload.get("progressPercent"),
            "understandingLevel": payload.get("understandingLevel"),
            "weakPoints": payload.get("weakPoints", []),
        },
    )
    return response(200, "success", updated)


@app.post("/api/v1/lesson/play")
def lesson_play():
    payload, error = require_signature()
    if error:
        return error, 401
    return response(200, "success", adapter.play_lesson(payload.get("lessonId")))


@app.post("/api/v1/qa/voiceToText")
def qa_voice_to_text():
    payload, error = require_signature()
    if error:
        return error, 401
    return response(200, "success", {"text": learning_service.voice_to_text(payload.get("fileName", "voice.webm"))})


@app.post("/api/v1/qa/interact")
def qa_interact():
    payload, error = require_signature()
    if error:
        return error, 401
    data = learning_service.interact(
        payload.get("lessonId"),
        payload.get("question", ""),
        payload.get("anchorId"),
        payload.get("pageNo"),
    )
    return response(200, "success", data)


@app.post("/api/v1/progress/adjust")
def progress_adjust():
    payload, error = require_signature()
    if error:
        return error, 401
    data = learning_service.adjust_progress(
        payload.get("lessonId"),
        payload.get("anchorId"),
        payload.get("pageNo"),
        payload.get("understandingLevel"),
        payload.get("weakPoints", []),
    )
    return response(200, "success", data)


@app.post("/api/v1/lesson/resume")
def lesson_resume():
    payload, error = require_signature()
    if error:
        return error, 401
    return response(200, "success", learning_service.resume(payload.get("lessonId"), payload.get("anchorId")))


@app.post("/api/v1/notifications/list")
def notification_list():
    payload, error = require_signature()
    if error:
        return error, 401
    return response(200, "success", {"notifications": adapter.list_notifications(payload.get("studentId"))})


@app.post("/api/v1/notifications/detail")
def notification_detail():
    payload, error = require_signature()
    if error:
        return error, 401

    data = adapter.get_notification_detail(payload.get("studentId"), payload.get("notificationId"))
    if data is None:
        return response(404, "通知不存在", None), 404
    return response(200, "success", data)


@app.post("/api/v1/notifications/read")
def notification_read():
    payload, error = require_signature()
    if error:
        return error, 401

    data = adapter.mark_notification_read(payload.get("studentId"), payload.get("notificationId"))
    if data is None:
        return response(404, "通知不存在", None), 404
    return response(200, "success", data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
