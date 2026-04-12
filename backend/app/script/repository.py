from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select

from backend.app.common.db import session_scope
from backend.app.script.models import ScriptEntity
from backend.app.script.schemas import ScriptDetail


def save_script(script: ScriptDetail) -> ScriptDetail:
    now = datetime.now(UTC)
    with session_scope() as session:
        entity = session.get(ScriptEntity, script.scriptId)
        if entity is None:
            entity = ScriptEntity(script_id=script.scriptId, created_at=now)
            session.add(entity)

        entity.parse_id = script.parseId
        entity.teaching_style = script.teachingStyle
        entity.speech_speed = script.speechSpeed
        entity.script_structure_json = [section.model_dump(mode="json") for section in script.scriptStructure]
        entity.version = script.version
        entity.updated_at = now
    return script


def load_script(script_id: str) -> ScriptDetail | None:
    with session_scope() as session:
        entity = session.get(ScriptEntity, script_id)
        return _entity_to_script(entity) if entity else None


def load_all_scripts() -> dict[str, ScriptDetail]:
    with session_scope() as session:
        entities = session.scalars(select(ScriptEntity)).all()
        scripts = [_entity_to_script(entity) for entity in entities]
        return {script.scriptId: script for script in scripts}


def clear_script_records() -> None:
    with session_scope() as session:
        session.execute(delete(ScriptEntity))


def _entity_to_script(entity: ScriptEntity) -> ScriptDetail:
    return ScriptDetail.model_validate(
        {
            "scriptId": entity.script_id,
            "parseId": entity.parse_id,
            "teachingStyle": entity.teaching_style,
            "speechSpeed": entity.speech_speed,
            "scriptStructure": entity.script_structure_json or [],
            "version": entity.version,
        }
    )
