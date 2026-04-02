from fastapi import APIRouter, Request

from backend.app.common.responses import success_response
from backend.app.common.security import verify_signature_placeholder
from backend.app.script.schemas import GenerateScriptRequest, UpdateScriptRequest
from backend.app.script.service import generate_script, get_script, update_script

router = APIRouter(tags=["script"])


@router.post("/lesson/generateScript")
def generate_script_endpoint(payload: GenerateScriptRequest, request: Request) -> dict:
    verify_signature_placeholder(payload.enc, payload.time)
    data = generate_script(payload)
    return success_response(request, data.model_dump(), msg="脚本生成成功")


@router.get("/scripts/{scriptId}")
def get_script_endpoint(scriptId: str, request: Request) -> dict:
    data = get_script(scriptId)
    return success_response(request, data.model_dump(), msg="脚本查询成功")


@router.put("/scripts/{scriptId}")
def update_script_endpoint(scriptId: str, payload: UpdateScriptRequest, request: Request) -> dict:
    verify_signature_placeholder(payload.enc, payload.time)
    data = update_script(scriptId, payload)
    return success_response(
        request,
        {
            "scriptId": data.scriptId,
            "version": data.version,
            "savedAt": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        },
        msg="脚本保存成功",
    )
