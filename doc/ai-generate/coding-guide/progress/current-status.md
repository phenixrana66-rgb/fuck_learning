# 当前进度

本文件用于记录**当前代码与文档的最新有效状态**，供下一次继续开发时快速恢复上下文。

## 一、当前文档体系状态

目前 `doc/ai-generate/` 下已经形成五层：

- `requirements-analysis/`：需求与验收边界
- `project-architecture/`：系统结构、对象、状态、模块边界
- `tech-stack-selection/`：技术栈、运行时、存储、部署与测试基线
- `coding-guide/`：日常编码入口、模块映射、联动顺序、接口到代码定位
- `api/`：逐接口契约文档

## 二、当前 coding-guide 已有内容

- `01-编码入口.md`：平时编码默认入口
- `02-后端模块与实现映射.md`：模块职责与后续实现目标
- `03-联动顺序与完成定义.md`：阶段顺序与 DoD
- `05-接口到代码文件映射.md`：接口文档到后端代码文件定位
- `06-编码流程与文档持久化规范.md`：先读什么、改完同步什么
- `07-数据库持久化演进规划.md`：从内存态到 MySQL / Redis / MinIO 的落地边界与阶段顺序

补充状态：

- 已完成一次 `temp/zrt` 协作文档与我方文档的数据库设计比对
- `project-architecture/05-核心数据模型设计.md` 已补入“逻辑对象 -> 首批物理表”的开发参考映射
- `coding-guide/07-数据库持久化演进规划.md` 已补入“当前可直接用于开发的最小表清单、关键回链字段、关键约束与索引”

## 三、当前 backend 代码状态（高层）

当前 `backend/app` 已具备：

- `main.py` 主应用与 6 组业务路由挂载
- `platform / courseware / script / lesson / qa / progress` 六个领域包
- `common / parser / cir / tasks / observability` 支撑包

其中已经落地的较真实 demo 能力：

- `courseware / parser / cir` 已打通 **PPTX -> 文本抽取 -> LLM 结构化 -> StructurePreview / CIR** 主链
- `parser/pptx_reader.py` 已能读取本地或远程 `.pptx` 文件，提取 slide 标题、正文、表格和备注
- `parser/llm_client.py` 已能通过 OpenAI 兼容 `chat/completions` 接口生成章节结构
- `rest-client/lesson-parse.http` 已提供可直接联调的解析请求样例
- 解析任务状态已统一收口到 `tasks/service.py`，成功态结果与失败态错误都可按 `parseId` 查询
- 解析任务主记录已通过 `tasks/models.py` + `tasks/repository.py` 落到数据库表 `task_records`
- `POST /api/v1/lesson/parse` 已改为先返回 `processing`，解析执行转入本地后台路径
- `script/models.py` + `script/repository.py` 已让脚本生成、查询、更新落到数据库表 `script_records`
- `script / lesson` 已能基于真实 parse 结果形成最小 happy path：`generateScript -> generateAudio -> publish -> play`
- `common/config.py` 与 `common/db.py` 已正式消费数据库连接配置，测试可切 SQLite，开发环境可连 MySQL

当前仍以 demo / 占位为主的点：

- `common/security.py` 还是 `verify_signature_placeholder`
- `lesson / qa / progress` 仍使用内存字典或示例返回
- 当前 PPT 解析 demo 仅支持 `.pptx`，不支持 `.pdf` 与旧 `.ppt`
- `courseware / cir` 的课件主记录、解析结果、节点树还没有完整落库
- 当前解析任务尚未接 Redis / Dramatiq / MinIO，执行路径仍是本地后台路径
- 真实 MySQL / Alembic / Dramatiq / Redis / MinIO / TTS / ASR 尚未全接通
- 只有解析链接入了 LLM；问答、续讲仍未消费真实结构化结果

## 四、当前验证状态（2026-04）

- 自动化测试：`python -m unittest discover -s backend/tests -p "test_*.py"` 已通过，22/22
- 静态检查：`basedpyright` 当前已无 error，但仍存在 warning
- 手工验收：SQLite 与 MySQL 两轮都已验证 parse/task/script 入库链
- 验收输入：两轮手工验收都使用真实 `examples/01总论.pptx`
- 已知限制：当前环境缺少 `A12_LLM_API_KEY`，所以手工验收对 outline 生成做了确定性 patch，未走真实外部 LLM

## 五、默认下一步优先级

建议下一步继续按这个顺序推进：

1. 补齐解析链剩余真实依赖：`courseware / parser / cir / tasks`
2. 在脚本已落库基础上补音频与发布链：`lesson`
3. 问答证据链：`qa`
4. 续讲与指标：`progress / observability`

### 当前解析链 demo 的接手要点

- 接口：`POST /api/v1/lesson/parse`、`GET /api/v1/lesson/parse/{parseId}`
- 现状：`POST` 仅创建任务并返回 `taskStatus=processing`，解析会在本地后台路径继续执行
- 补充：若解析失败，需要通过 `GET` 查询 `failed` 状态与错误信息
- 当前持久化：任务主记录进入数据库表 `task_records`，对应日志落在 `temp/ai-generate/tasks/logs/`
- 配置：需要 `A12_LLM_API_BASE_URL`、`A12_LLM_API_KEY`、`A12_LLM_MODEL`、`A12_LLM_TIMEOUT_SECONDS`
- 数据库：可通过 `A12_DB_URL` 或 `A12_DB_HOST / A12_DB_PORT / A12_DB_USER / A12_DB_PASSWORD / A12_DB_NAME / A12_DB_ECHO` 提供连接配置
- 调试：优先使用 `rest-client/lesson-parse.http` 与 `examples/demo-courseware.pptx`

## 六、如果下次继续开发，先读什么

下次继续时，默认按这个顺序恢复上下文：

1. 先读 [../01-编码入口.md](../01-编码入口.md)
2. 再读 [../03-联动顺序与完成定义.md](../03-联动顺序与完成定义.md)
3. 再读 [../05-接口到代码文件映射.md](../05-接口到代码文件映射.md)
4. 如果是解析链，先看 `backend/app/parser/` 与 `rest-client/lesson-parse.http`
5. 最后根据任务跳到 `../api/` 对应接口文档

## 七、维护要求

每次出现以下情况，都要更新本文件：

- 当前阶段完成度变化
- 新增真实依赖接入
- 当前优先级变化
- 日常编码入口或恢复顺序变化

本轮额外说明：

- `temp/zrt/docs/字段级数据库设计说明书.md` 与 `temp/zrt/docs/mysql建表.sql` 当前可作为数据库落库时的外部字段级参考
- 但仓库内正式基线仍以 `doc/ai-generate/` 为准；只有已经吸收到我方文档的内容，才视为后续开发默认方案
