# 配置教师端和学生端 LLM 模型参数

## Goal

将当前分散在 `config.local.py` / 代码默认值中的 LLM 配置，改造成教师端与学生端可分别配置、可持久化、可在运行时生效的模型配置能力。教师端拆分为讲稿生成与 PPT 结构化解析两套 OpenAI-compatible 文本交互配置；学生端 QA 覆盖文本问答、图片理解、多模态问答、图片生成、Embedding 向量模型等能力，避免一个模型配置同时承担不兼容的调用协议和能力边界。

## What I Already Know

* 用户明确提出当前有多个 LLM 入口：教师端讲稿生成、教师端结构化解析、学生端 QA 问答。
* 教师端讲稿生成和结构化解析都只需要文本交互能力，但需要分别配置 `baseURL`、`apiKeyRef`、模型名称；真实 API key 不进入业务数据库。
* 学生端涉及多模态交互：文本交互、图片交互、图片生成，以及向量模型；用户倾向确认这些能力是否需要单独模型配置。
* 当前后端 `backend/app/common/config.py` 已有教师端全局配置：`llm_api_base_url`、`llm_api_key`、`llm_model`、`llm_timeout_seconds`。
* 当前教师端 `backend/app/script/llm_client.py` 使用上述 `llm_*` 配置调用 OpenAI-compatible `/chat/completions` 生成讲稿。
* 当前 `backend/app/parser/llm_client.py` 也复用同一组 `llm_*` 配置做 PPT 结构化解析；用户已确认结构化解析需要单独配置，不应继续和讲稿生成强绑定同一组运行时参数。
* 当前学生端 QA 已有 `qa_runtime_configs` 表和 QA 实验台，可持久化 `qa_llm_model`、`qa_multimodal_model`、`qa_embedding_model`、`retrieval_enabled`、`retrieval_top_k`。
* 当前学生端 QA 模型客户端 `backend/app/student_runtime/qa_dashscope_client.py` 仍强绑定 DashScope：`dashscope_api_key`、`dashscope_base_url` 来自全局 settings；运行时配置主要只覆盖模型名。
* 当前学生端图片生成使用 `settings.qa_image_generation_model`，暂未纳入 `qa_runtime_configs` 运行时配置。
* 当前示例配置 `config.example.py` 已暴露学生端默认项：`qa_llm_provider`、`qa_llm_model`、`qa_multimodal_model`、`qa_embedding_model`、`qa_image_generation_model`、`dashscope_api_key`、`dashscope_base_url` 等。

## Recommended MVP Scope

MVP 推荐拆分为两组可配置入口：

* 教师端讲稿生成 LLM 配置：面向 OpenAI-compatible 文本模型，包含 `baseUrl`、`apiKeyRef`、`model`、`timeoutSeconds`。默认继续读取 `config.local.py`，保存后持久化覆盖讲稿生成调用。
* 教师端结构化解析 LLM 配置：面向 OpenAI-compatible 文本模型，包含 `baseUrl`、`apiKeyRef`、`model`、`timeoutSeconds`。默认可沿用现有 `llm_*` 配置值作为初始值，但保存后独立覆盖 PPT 结构化解析调用。
* 学生端 QA 能力配置：按能力拆分为文本对话、视觉/图片理解、图片生成、Embedding。每类能力至少包含 `provider`、`baseUrl`、`apiKeyRef`、`model`，Embedding 额外包含 `dimensions`，图片生成额外保留 `size`、`count`、`timeoutSeconds`、`pollIntervalSeconds`。
* 学生端 provider 支持一步到位做多供应商插件式扩展：运行时按能力选择 provider adapter，不再把 QA 客户端强绑定到 DashScope。
* 首批 provider 范围锁定为 DashScope + OpenAI-compatible。DashScope 保持现有文本、视觉、图片生成、Embedding 能力；OpenAI-compatible 至少跑通文本问答、视觉理解、Embedding，图片生成不在首批 OpenAI-compatible 必达范围内。
* 配置作用域先收敛为全局一套运行时配置，不按学校、课程或教师覆盖；后续如需多租户配置，再在已有全局配置模型上扩展 scope 层级。
* 前端新增独立“模型配置”页面，集中管理教师端讲稿生成、教师端结构化解析、学生端 QA 各能力配置；现有 QA 实验台继续专注 QA compare、课程上下文验证和检索调试。

这样设计的原因：

* 文本对话、视觉理解、图片生成、Embedding 往往不是同一个模型，也不一定走同一个 endpoint。
* DashScope 图片生成当前走异步任务接口，和 OpenAI-compatible chat/completions 的调用协议不同，不能只靠一个 `model` 字段表达。
* Embedding 模型变化会影响既有向量数据有效性，必须和聊天模型分开配置并提示重新同步向量。
* API key 引用名/baseURL 有可能复用同一个供应商，也有可能分别指向不同供应商；字段层面支持单独覆盖更稳妥，UI 可以提供“同供应商复用”来减少填写成本。
* 运行时配置可持久化 `provider/baseUrl/apiKeyRef/model/timeout/settings` 等非密钥字段；真实 API key 本身不进入业务数据库。
* 运行时配置只保存 `apiKeyRef`，例如 `dashscope_api_key`、`openai_compat_api_key_a`；真实密钥只从 `config.local.py` / 环境变量解析，不写入业务数据库、不返回前端、不进入日志。
* 非密钥模型配置需要入库用于页面保存和运行时生效；真实 API key 不入库。
* 非密钥配置入库采用 capability 多行模型：一行一个能力，首批 capability 包含 `teacher_script_generation`、`teacher_structure_parse`、`student_text_chat`、`student_vision_chat`、`student_image_generation`、`student_embedding`。
* 旧 `qa_runtime_configs` 直接迁移到新的 capability-row 表；迁移完成后运行时读写只走新表，不长期保留双读路径。
* 供应商能力和协议差异会继续增长；本任务直接建立 provider adapter 边界，避免后续每新增一个模型供应商都改动 QA 主流程。

## Requirements

* 教师端提供两个可持久化的 LLM 配置能力：讲稿生成配置、结构化解析配置。
* 教师端两套配置默认值来自 `config.local.py` / `Settings`，保存后分别覆盖对应调用，不互相影响。
* 教师端和学生端模型配置作用域均为全局；保存后对所有教师/学生请求生效。
* 教师端 UI 文案需要明确两套配置的使用场景：讲稿生成用于 `backend/app/script/llm_client.py`，结构化解析用于 `backend/app/parser/llm_client.py`。
* 前端新增独立教师端路由/菜单入口用于模型配置，不把教师端讲稿生成、结构化解析配置塞进现有 QA 实验台。
* 学生端 QA 运行时配置扩展为能力分组：
  * 文本问答配置：`provider`、`baseUrl`、`apiKeyRef`、`model`、`timeoutSeconds`。
  * 图片/多模态理解配置：`provider`、`baseUrl`、`apiKeyRef`、`model`、`timeoutSeconds`。
  * 图片生成配置：`provider`、`baseUrl`、`apiKeyRef`、`model`、`size`、`count`、`timeoutSeconds`、`pollIntervalSeconds`。
  * Embedding 配置：`provider`、`baseUrl`、`apiKeyRef`、`model`、`dimensions`、`timeoutSeconds`。
* 学生端已有 QA 实验台继续作为运行时配置入口，保存后学生 QA、QA compare、向量检索相关调用立即读取最新有效配置。
* 学生端模型配置从 QA 实验台迁移到独立“模型配置”页；QA 实验台仍可读取当前有效配置用于展示/compare，但不再承担完整配置编辑职责。
* 学生端模型调用层需要抽象 provider adapter，按能力至少定义文本对话、视觉理解、图片生成、Embedding 的统一内部接口。
* MVP 需要保留现有 DashScope 行为作为一个 provider adapter，并实现 OpenAI-compatible 文本/视觉/Embedding adapter。图片生成首批只要求 DashScope adapter 跑通，但接口边界必须允许后续接入其他异步或同步图片生成供应商。
* provider 不支持某项能力时，后端需要返回明确错误，而不是静默降级到其他模型。
* 保留“恢复默认”能力：恢复后回到 `config.local.py` / `Settings` 默认值，而不是代码硬编码值。
* 运行时配置接口只接受和返回 API key 引用名，不接受真实 API key；后端根据引用名从 settings 中解析真实密钥。
* 前端保存模型配置时，后端只持久化非密钥字段和 `apiKeyRef`；任何形似真实密钥的字段都应拒绝或忽略。
* 持久化表建议使用 `scope_key + capability` 唯一约束；全局作用域使用稳定 `scope_key`，每行保存 `provider`、`base_url`、`api_key_ref`、`model_name`、`timeout_seconds`、`settings_json` 等字段。
* 旧字段迁移映射：`qa_llm_model` -> `student_text_chat.model_name`，`qa_multimodal_model` -> `student_vision_chat.model_name`，`qa_embedding_model` -> `student_embedding.model_name`。
* `retrieval_enabled` 和 `retrieval_top_k` 继续作为学生 QA 独立运行时检索配置持久化，不并入 `student_embedding.settingsJson`；Embedding capability 只表达向量化模型和参数。
* 未配置或引用不存在的 API key 时，后端需要返回明确错误，指出缺失的 `apiKeyRef`。
* 配置变更需要提供校验：必填项不能为空，URL 格式需要基础校验，数值项限制范围。
* Embedding 模型或维度变化时继续给出重新执行向量同步的警告。
* 数据库、SQL 文档、ORM 模型、后端服务、前端 API wrapper、教师端配置 UI 需要保持字段一致。

## Acceptance Criteria

* [ ] 教师端可以查看默认讲稿生成 LLM 配置，保存 `baseUrl/apiKeyRef/model/timeoutSeconds` 后，讲稿生成实际使用保存后的配置。
* [ ] 教师端可以查看默认结构化解析 LLM 配置，保存 `baseUrl/apiKeyRef/model/timeoutSeconds` 后，PPT 结构化解析实际使用保存后的配置。
* [ ] 教师端恢复默认后，讲稿生成和结构化解析分别回到 `config.local.py` / `Settings` 默认配置。
* [ ] 配置保存后作为全局配置生效，不需要学校、课程或教师维度参数。
* [ ] 教师端新增独立“模型配置”页面/菜单入口，集中编辑教师端与学生端模型配置。
* [ ] QA 实验台保留 compare 和调试能力，但不再承载完整模型配置编辑表单。
* [ ] 学生端 QA 实验台可以分别编辑文本问答、图片理解、图片生成、Embedding 配置。
* [ ] 学生端 QA 调用通过 provider adapter 分发，不再由 QA 主流程直接依赖 DashScope 专有客户端。
* [ ] 学生端纯文本 QA 使用文本问答配置。
* [ ] 学生端带图片 QA 使用图片/多模态理解配置。
* [ ] 学生端图片生成模式使用图片生成配置。
* [ ] 学生端检索和向量同步相关 embedding 调用使用 Embedding 配置。
* [ ] DashScope 作为一个 provider adapter 保持现有文本、图片理解、图片生成、Embedding 行为不回退。
* [ ] OpenAI-compatible provider adapter 至少支持文本问答、图片/视觉理解、Embedding。
* [ ] OpenAI-compatible provider 未配置图片生成能力时，图片生成模式返回明确“不支持当前能力”的错误。
* [ ] 配置为不支持当前能力的 provider 时，接口返回可读错误并指出缺失能力。
* [ ] 前端只展示和编辑 `apiKeyRef`，不会展示、提交或保存真实 API key。
* [ ] 前端保存后，非密钥配置入库并立即影响对应运行时调用。
* [ ] 非密钥配置按 capability 多行持久化，至少覆盖教师讲稿、教师结构化解析、学生文本 QA、学生视觉 QA、学生图片生成、学生 Embedding 六类能力。
* [ ] 旧 `qa_runtime_configs` 数据可迁移到新 capability-row 表，迁移后运行时读写只走新表。
* [ ] `retrievalEnabled` / `retrievalTopK` 继续作为学生 QA 独立检索配置生效，不混入 Embedding capability。
* [ ] 配置了不存在的 `apiKeyRef` 时，相关调用返回明确错误。
* [ ] 修改 Embedding 模型或维度后，接口返回重新同步向量的 warning。
* [ ] 现有 QA compare、检索开关、`retrievalTopK` 配置继续可用。
* [ ] 相关 backend unittest 覆盖配置默认值、保存、恢复、实际模型选择、`apiKeyRef` 解析和缺失引用错误。
* [ ] 相关前端构建通过，QA 实验台配置表单可正常保存/恢复。

## Definition of Done

* Tests added/updated for backend config services and affected QA/script call paths.
* Frontend build passes after UI/API wrapper changes.
* SQL docs/migrations and SQLAlchemy model fields stay aligned.
* `config.example.py` documents all new defaults.
* Behavior change is reflected in Trellis spec if a new project convention emerges.

## Technical Approach

Prefer a shared internal config shape rather than hard-coding provider-specific fields into every call site:

* Add service-level dataclasses/value objects for teacher script-generation config, teacher structure-parse config, and student QA capability configs.
* Introduce or migrate to a capability-row runtime config table with `scope_key + capability` uniqueness. Persist per-capability provider/baseURL/API key reference/model/settings fields; this table must not contain real API key values.
* Replace student model runtime reads with the new capability-row table. Avoid carrying long-term fallback logic to the old `qa_runtime_configs` shape after migration.
* Keep retrieval settings as a separate student QA runtime section/table/row outside model capability config. Do not store retrieval switches inside `student_embedding.settingsJson`.
* Keep `Settings` / `config.local.py` as default source, and DB row as runtime override source.
* Keep scope storage compatible with the existing global style, e.g. a stable global `scope_key`; do not introduce school/course/teacher resolution in this task.
* Introduce student QA provider adapter interfaces for text chat, vision chat, image generation, and embeddings. Refactor current `DashScopeClient` behind those interfaces instead of calling it directly from orchestration code.
* Add an adapter registry/factory that resolves `(provider, capability)` from the effective runtime config and returns the matching adapter.
* Add or extend teacher-side control APIs under `/api/v1/...` with teacher auth, matching existing QA lab runtime config patterns.
* Update `src/api/teacher.js` and add a dedicated teacher model settings route/view, likely under `src/views/teacher/`.
* Keep `src/views/teacher/QaLab.vue` focused on QA compare/debug display and adjust it to read effective config summary if needed.

## Decision (ADR-lite)

**Context**: Teacher and student LLM usage is heterogeneous. Teacher script generation and PPT structure parsing are both text calls but have different prompt contracts and operational needs. Student QA uses text chat, vision chat, image generation, and embeddings with different model names, endpoint conventions, timeout behavior, and data compatibility risks.

**Decision**: Treat teacher script generation, teacher structure parsing, student text QA, student vision QA, student image generation, and student embeddings as separate capability configs. Student QA additionally introduces provider adapter boundaries so each capability can be backed by different suppliers. Allow shared defaults and UI reuse, but persist and resolve them independently.

**Consequences**: The schema, UI, and model client layer become larger than a single `baseUrl/apiKey/model` form, but the implementation avoids hidden coupling, supports local/private endpoints per capability, and keeps image generation / embedding changes explicit. Real API keys remain outside the business database, so operator convenience is lower than direct key editing, but the security boundary is cleaner. This increases the first implementation cost but reduces future provider migration cost.

## Open Questions

* 当前 grill-me 决策已收敛，等待最终确认后进入实现阶段。

## Out of Scope

* 不在本任务内实现所有可能供应商；只建立 provider adapter 边界并落地首批确认的 provider。
* 不在本任务内迁移既有向量数据；仅在 Embedding 配置变化时提示重新同步。
* 不在本任务内新增模型连通性测速/试调用功能；配置正确性通过现有讲稿生成、结构化解析、QA compare 和学生 QA 实际流程验证。
* 不在本任务内改变学生端 QA 消息、图片附件、图片生成结果的业务语义。

## Technical Notes

* Existing config defaults: `backend/app/common/config.py`
* Example local config: `config.example.py`
* Teacher script LLM caller: `backend/app/script/llm_client.py`
* Teacher PPT parse LLM caller: `backend/app/parser/llm_client.py`
* Student QA runtime service: `backend/app/student_runtime/qa_runtime_config_service.py`
* Student QA model client: `backend/app/student_runtime/qa_dashscope_client.py`
* Student QA runtime DB model: `backend/chaoxing_db/models/qa_runtime.py`
* Student QA runtime SQL doc: `docs/migrations/20260601_qa_runtime_configs.sql`
* Teacher QA lab route: `backend/app/teacher_runtime/extra_router.py`
* Frontend teacher API wrapper: `src/api/teacher.js`
* Frontend QA lab UI: `src/views/teacher/QaLab.vue`
* Backend implementation should read `.trellis/spec/backend/index.md` and relevant backend guides before coding.
* Frontend implementation should read `.trellis/spec/frontend/index.md` and relevant frontend guides before coding.
