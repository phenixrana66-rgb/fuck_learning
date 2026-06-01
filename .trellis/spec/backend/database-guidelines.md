# Database Guidelines

> How backend code talks to the database in the current codebase.

---

## Source Of Truth

The effective DB access pattern is defined by:

* `backend/app/common/db.py`
* `backend/chaoxing_db/base.py`
* `backend/chaoxing_db/models/`
* representative domain services such as `backend/app/courseware/service.py`, `backend/app/lesson/service.py`, and `backend/app/student_runtime/db_learning_service.py`

Schema bootstrap SQL lives in `docs/`, especially `docs/mysql建表.sql` and `docs/migrations/`.

---

## Current Pattern

### App request handlers

Routers should accept a `Session` through `Depends(get_db)` and pass it down:

* example: `backend/app/student_runtime/router.py`
* example: `backend/app/teacher_runtime/extra_router.py`

This keeps session ownership aligned with the request lifecycle.

### Service and batch logic

Standalone workflows use `session_scope()`:

* example: `backend/app/courseware/service.py`
* example: `backend/app/script/service.py`
* example: `backend/app/lesson/service.py`

Use `session_scope()` when the function owns the transaction boundary.

### Tests

Tests commonly redirect persistence to a temporary SQLite file:

* `configure_database_url(...)`
* `reset_database_url()`

See `backend/tests/student_runtime/test_router.py` for the standard pattern.

---

## Required Patterns

* Use model classes from `backend.chaoxing_db.models`.
* Reuse `get_db()` or `session_scope()` from `backend/app/common/db.py`; do not create ad-hoc engines/sessions inside feature code.
* Keep transaction ownership explicit. Request routers pass a session in; service-owned workflows open their own session scope.
* Use `db.flush()` when later rows depend on generated IDs in the same transaction.
* Keep schema-related path generation consistent with runtime expectations, such as `/courseware-previews/<parse_id>/...` and lesson preview URLs.

---

## Forbidden Patterns

* Do not create raw SQLAlchemy engines in feature modules.
* Do not bypass `model_registry` assumptions by importing only part of the ORM graph in schema-init code.
* Do not let routers mix response formatting, DB orchestration, and model mutation if an existing service already owns that workflow.
* Do not introduce a second migration system casually. This repo currently uses checked-in SQL docs/scripts rather than Alembic.

---

## Migrations And Schema Changes

Current schema ownership is split:

* ORM definitions: `backend/chaoxing_db/models/`
* bootstrap schema SQL: `docs/mysql建表.sql`
* incremental SQL: `docs/migrations/*.sql`

If a DB schema change is required:

1. Update the ORM model(s).
2. Update or add the relevant SQL under `docs/`.
3. Update seed/test data when the new shape is needed by existing flows.
4. Run the focused backend tests that exercise the affected path.

---

## Scenario: Student QA Multimodal Image Attachments

### 1. Scope / Trigger
- Trigger: student QA now persists uploaded images across the stream route, session history, local file cache, and multimodal model calls.
- Why this needs code-spec depth: the contract spans UI payloads, FastAPI handlers, ORM rows, local static serving, and model input reconstruction.

### 2. Signatures
- Stream API: `POST /student-api/api/v1/qa/interact/stream`
- Session save API: `POST /student-api/api/v1/qa/sessions`
- Session list API: `GET /student-api/api/v1/qa/sessions`
- ORM fields:
  - `qa_messages.question_type`: `text | voice | image | mixed`
  - `qa_message_attachments(message_id, session_id, lesson_id, attachment_type, storage_provider, storage_key, file_url, file_name, mime_type, file_size, sort_no)`
- Storage helpers:
  - `normalize_qa_image_attachments(...)`
  - `store_qa_image_from_data_url(...)`
  - `load_qa_image_as_data_url(...)`

### 3. Contracts
- Stream request:
  - `question: string`
  - `attachments: Attachment[]` optional, but `question` and `attachments` cannot both be empty
- Attachment payload:
  - `attachmentType`: currently `image`
  - `fileName`: original filename used by history UI
  - `mimeType`: `image/jpeg | image/png | image/webp`
  - `fileSize`: integer bytes, max `10 * 1024 * 1024`
  - `dataUrl`: required for first browser upload
  - `url` / `storageKey`: persisted form returned by session save/list
- Session response:
  - user messages must round-trip `attachments`
  - user messages must round-trip `questionType`
  - persisted image URLs must live under `/cache/qa-images/...`
- Environment/config:
  - `qa_multimodal_model`: multimodal model selector
  - local cache root: `cache/qa-images`

### 4. Validation & Error Matrix
- More than 5 images in one request or message -> reject during attachment normalization
- Unsupported MIME type -> reject during attachment normalization
- File size above 10 MB -> reject during attachment normalization
- Empty `question` and empty `attachments` on the stream route -> return `400`
- Follow-up turns with only stored `url`/`storageKey` -> reload local file as `data:` URL before model invocation
- Sync route `/student-api/api/v1/qa/interact` -> keep text-only behavior unless a separate task expands it
- Cross-database schema support -> when the live MySQL schema uses `BIGINT UNSIGNED` but local tests use SQLite auto-increment, declare the ORM column as `Integer().with_variant(MYSQL_BIGINT(unsigned=True), "mysql")`

### 5. Good / Base / Bad Cases
- Good: user sends text plus 1-5 images, the backend persists normalized attachments, history restores thumbnails, and later turns reuse the latest images.
- Base: user sends images only, the backend injects the default image-only prompt semantics and still returns a normal assistant answer.
- Bad: backend forwards only `localhost` or static file URLs to the remote multimodal model; first-upload requests must use `dataUrl`, and follow-up requests must rehydrate stored files back into `data:` URLs.

### 6. Tests Required
- Router regression:
  - image-only stream payload succeeds
  - empty text plus empty attachments fails
- Session persistence regression:
  - save session with image attachments
  - list sessions returns normalized `attachments` and `questionType`
  - persisted storage-backed attachments can be reused in later multimodal turns
- Config regression:
  - `qa_multimodal_model` is overrideable from `config.local.py`
- Manual verification:
  - student frontend build passes after QA UI changes

### 7. Wrong vs Correct
#### Wrong
```python
# Remote multimodal models cannot fetch localhost/static URLs directly.
image_inputs = [attachment["url"] for attachment in attachments]
answer = client.chat_multimodal_completion(question, image_inputs, system_prompt)
```

#### Correct
```python
# First upload stores the browser data URL locally, then future turns
# rehydrate the stored file back into a data URL for the model call.
normalized = normalize_qa_image_attachments(attachments)
image_inputs = [
    attachment.get("dataUrl") or load_qa_image_as_data_url(attachment["storageKey"])
    for attachment in normalized
]
answer = client.chat_multimodal_completion(question, image_inputs, system_prompt)
```

---

## Scenario: Student Learning Position Sync

### 1. Scope / Trigger
- Trigger: student learning-position fixes now span `page/read` persistence, lesson progress reads, resume reads, recent-chapter reads, and same-session frontend refresh.
- Why this needs code-spec depth: the contract crosses DB rows, student runtime endpoints, and browser cache synchronization; if any reader uses a different source, "上次学习位置" immediately forks again.

### 2. Signatures
- Progress read API: `POST /student-api/api/v1/progress/get`
- Page-read write API: `POST /student-api/api/v1/progress/page/read`
- Resume API: `POST /student-api/api/v1/lesson/resume`
- Recent chapters API: `POST /student-api/api/v1/recentChapters/list`
- DB helpers:
  - `mark_page_read(...)`
  - `get_db_progress_state(...)`
  - `get_db_resume_state(...)`
  - `get_recent_chapter_visits(...)`
- ORM rows:
  - `student_page_progress`
  - `student_section_progress`
  - `student_lesson_progress`
  - `resume_records`

### 3. Contracts
- Authoritative write event:
  - a successful `page/read` call is the only durable signal that advances the student's latest learning position
- Reader contract:
  - `progress/get` and `lesson/resume` must both resolve from the latest persisted lesson progress, not from caller-supplied stale `anchorId`
  - `recentChapters/list` must reflect the same persisted lesson/section/page position family, not an unrelated exit-only cache
- Resume payload:
  - must include `lessonId`, `sectionId`, `anchorId`, `anchorTitle`, `pageNo`, and `resumeTime`
  - when the stored page is invalid, the backend must still return the nearest valid fallback location instead of an empty payload

### 4. Validation & Error Matrix
- `page/read` succeeds -> update page progress, section progress, lesson progress, and append resume/progress logs in the same transaction
- stored `last_page_no` missing or invalid for the current section -> fall back to the first valid page in that section
- stored section missing or invalid -> fall back to the first valid section in the lesson
- caller passes stale `anchorId` to `lesson/resume` -> ignore it when DB progress exists; DB progress wins
- `page/read` fails -> do not advance durable learning position anywhere else as compensation

### 5. Good / Base / Bad Cases
- Good: student reads page 6, `page/read` succeeds, then `progress/get`, `lesson/resume`, and `recentChapters/list` all resolve to the same latest section/page.
- Base: student has no progress rows yet; reads fall back to the lesson's first valid section/page.
- Bad: `page/read` writes page 6, but `lesson/resume` still uses an old `anchorId` from the client and jumps back to page 2.

### 6. Tests Required
- DB regression:
  - stale stored `last_page_no` falls back to a valid page instead of leaking the invalid number through `progress/get` / `lesson/resume`
- Router regression:
  - after successful `page/read`, `lesson/resume` returns the persisted latest location even when request `anchorId` is stale
  - after successful `page/read`, `recentChapters/list` reflects the same lesson/section/page
- Verification:
  - frontend build still passes after the same-session sync changes

### 7. Wrong vs Correct
#### Wrong
```python
# Resume trusts the caller's last anchor even when the DB has newer progress.
data = learning_service.resume(payload.get("lessonId"), payload.get("anchorId"))
```

#### Correct
```python
# Resume prefers the latest persisted lesson progress and only falls back
# to compatibility logic when DB-backed state is unavailable.
data = get_db_resume_state(db, payload.get("studentId"), payload.get("lessonId"))
if data is None:
    data = learning_service.resume(payload.get("lessonId"), payload.get("anchorId"))
```

---

## Scenario: Student QA Runtime Experiment Config

### 1. Scope / Trigger
- Trigger: teacher-side internal QA lab now writes a global runtime override for the student QA chain, backed by MySQL/SQLite, and can reset back to `config.local.py` defaults.
- Why this needs code-spec depth: the contract crosses DB schema, teacher-only control APIs, student QA orchestration reads, and the operator-facing “恢复默认” behavior.

### 2. Signatures
- DB table: `qa_runtime_configs(scope_key, qa_llm_model, qa_multimodal_model, qa_embedding_model, retrieval_enabled, retrieval_top_k, created_at, updated_at)`
- Teacher-only APIs:
  - `GET /api/v1/qa-lab/runtime-config`
  - `PUT /api/v1/qa-lab/runtime-config`
  - `POST /api/v1/qa-lab/runtime-config/reset`
  - `POST /api/v1/qa-lab/course-outline`
  - `POST /api/v1/qa-lab/compare`
- Student QA read path:
  - `answer_question(..., runtime_config=...)`

---

## Scenario: Student Chapter Pace Suggestion State

### 1. Scope / Trigger
- Trigger: chapter-internal dynamic pacing now persists active supplement/reinforce state and exposes it through section detail, QA checkpoint, practice checkpoint, and skip logging flows.
- Why this needs code-spec depth: the contract spans ORM fields, runtime service rules, two checkpoint APIs, and the chapter learning UI's cold-start/immediate-refresh behavior.

### 2. Signatures
- ORM fields on `student_section_progress`:
  - `pace_mode`
  - `pace_reason_summary`
  - `pace_trigger_source`
  - `pace_updated_at`
- Runtime helpers:
  - `apply_qa_checkpoint(...)`
  - `apply_practice_checkpoint(...)`
  - `get_active_pace_suggestion(...)`
  - `record_pace_skip(...)`
- APIs:
  - `POST /student-api/api/v1/lesson/section/detail`
  - `POST /student-api/api/v1/qa/interact`
  - `POST /student-api/api/v1/qa/interact/stream`
  - `POST /student-api/api/v1/progress/practice/checkpoint`
  - `POST /student-api/api/v1/progress/pace/skip`

### 3. Contracts
- Persist only active intervention state:
  - `pace_mode` stores `supplement | reinforce`
  - improved `continue` results clear persisted pace fields instead of creating a long-lived banner state
- Section detail contract:
  - `paceSuggestion` is the cold-start source for chapter re-entry
  - when active pacing exists, `currentPageNo` should resolve to the suggested target step, not blindly to the raw last page
- QA checkpoint contract:
  - `understandingLevel=partial -> supplement`
  - `understandingLevel=weak -> reinforce`
  - `understandingLevel=complete -> clear persisted pace state`
- Practice checkpoint contract:
  - `< 60 -> reinforce`
  - `60-79 -> supplement`
  - `>= 80 -> clear persisted pace state`
- Completion cleanup:
  - if `progress_percent == 100` and `mastery_percent >= 60`, clear active pace state unless the latest checkpoint is explicitly `weak`

### 4. Validation & Error Matrix
- missing lesson or student on pace checkpoint routes -> `404`
- missing section on pace checkpoint routes -> `404`
- practice checkpoint without a graded attempt -> `404`
- section detail with no active pacing -> `paceSuggestion: null`
- QA/practice improvement to `continue` -> clear persisted pace fields and return `paceSuggestion: null`
- pace skip without active pacing -> return success with `paceSuggestion: null`; skip is auxiliary logging, not a state transition

### 5. Good / Base / Bad Cases
- Good: QA returns `weak`, backend persists `reinforce`, section detail re-entry restores the same suggestion, and skip only logs without silently clearing the intervention.
- Base: practice returns `72`, backend emits `supplement`, updates mastery rollup, and the chapter page shows the new suggestion immediately.
- Bad: backend persists `continue` as if it were an active mode, causing a permanent chapter banner that survives even after the learner has improved.

### 6. Tests Required
- DB regression:
  - persisted QA pace suggestion appears in `get_section_detail(...)`
  - chapter completion via `mark_page_read(...)` clears active pace state
- Router regression:
  - `qa/interact` returns `paceSuggestion` for weak/partial answers
  - `progress/practice/checkpoint` returns the latest `paceSuggestion`
  - `progress/pace/skip` preserves the active suggestion while still succeeding
- Verification:
  - frontend build passes after chapter learning UI changes

### 7. Wrong vs Correct
#### Wrong
```python
# Treat continue as a durable mode and keep showing it on chapter re-entry.
section_progress.pace_mode = "continue"
section_progress.pace_reason_summary = "可以继续学习"
```

#### Correct
```python
# Persist only active interventions; improvement clears the stored pace state.
if next_mode == "continue":
    clear_pace_state(section_progress)
else:
    section_progress.pace_mode = next_mode
    section_progress.pace_reason_summary = _pace_reason_summary(next_mode, trigger_source)
```
  - `build_qa_context_bundle(..., runtime_config=...)`
  - `DashScopeClient(runtime_config=...)`

### 3. Contracts
- Runtime config response:
  - `config.qaLlmModel: string`
  - `config.qaMultimodalModel: string`
  - `config.qaEmbeddingModel: string`
  - `config.retrievalEnabled: boolean`
  - `config.retrievalTopK: 1..10`
  - `defaults.*`: same shape as `config`, sourced from `config.local.py` / `Settings`
  - `warnings: string[]`
  - `overrideActive: boolean`
  - `updatedAt: string` only when a DB override row exists
- Update request:
  - accepts only the minimal experiment fields above
  - persists a single global row under `scope_key="student_qa_global"`
- Reset request:
  - deletes the DB override row instead of writing “default values” back into the table
  - after reset, student QA must resolve config from `config.local.py` first, then code defaults

### 4. Validation & Error Matrix
- missing/invalid teacher token -> `401`
- missing `courseId` in course-outline -> `400`
- unknown `courseId` -> `404`
- missing both `question` and `attachments` in compare -> `400`
- `retrievalTopK` outside range -> clamp into `1..10`
- changed `qaEmbeddingModel` -> keep request successful, but return a warning reminding operators to rerun `qa_vector_sync_service`

### 5. Good / Base / Bad Cases
- Good: operator saves a runtime override, compare runs with retrieval on/off, and the student QA chain immediately uses the new models.
- Base: no runtime override row exists; runtime-config GET returns `overrideActive=false` and `config == defaults`.
- Bad: “恢复默认” just writes the current defaults into DB, leaving `overrideActive=true` and making future `config.local.py` edits appear ineffective.

### 6. Tests Required
- Router regression:
  - update runtime config returns `overrideActive=true`
  - reset runtime config returns `overrideActive=false` and `config == defaults`
  - compare endpoint runs both retrieval-on and retrieval-off variants
- Student QA regression:
  - `/student-api/api/v1/qa/interact` passes the DB-backed runtime config into retrieval and model client code
- Frontend verification:
  - teacher QA lab build passes after adding save/reset controls

### 7. Wrong vs Correct
#### Wrong
```python
# "Reset" still keeps a DB row alive, so config.local.py never regains control.
row.qa_llm_model = defaults.qa_llm_model
row.qa_multimodal_model = defaults.qa_multimodal_model
db.commit()
```

#### Correct
```python
# Reset removes the override row entirely so runtime config falls back to
# config.local.py and then code defaults.
row = _find_runtime_config_row(db)
if row is not None:
    db.delete(row)
    db.commit()
```

---

## Review Checklist

When reviewing DB-facing changes, check:

* Is the right session ownership pattern used?
* Is the code mutating the authoritative ORM model instead of duplicating data shape logic elsewhere?
* Are URLs/IDs persisted in the same shape expected by the frontend and tests?
* If schema changed, were the SQL docs updated too?
