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
- 解析任务记录已可桥接落到本地文件仓储，并生成 `temp` 下的任务日志，服务重启后仍可恢复查询
- `POST /api/v1/lesson/parse` 已改为先返回 `processing`，解析执行转入本地后台路径
- `script / lesson` 已能基于真实 parse 结果形成最小 happy path：`generateScript -> generateAudio -> publish -> play`

当前仍以 demo / 占位为主的点：

- `common/security.py` 还是 `verify_signature_placeholder`
- 多个 `service.py` 仍使用内存字典或示例返回
- 当前 PPT 解析 demo 仅支持 `.pptx`，不支持 `.pdf` 与旧 `.ppt`
- `courseware` 解析任务仍未落 MySQL / Redis，但提交与执行已经拆开，不再是同步完成式接口
- 当前解析任务仍未接 MySQL / Redis / Dramatiq，但已通过本地文件仓储实现临时持久化桥接
- 真实 MySQL / Alembic / Dramatiq / Redis / MinIO / TTS / ASR 尚未全接通
- 只有解析链接入了 LLM；问答、续讲仍未消费真实结构化结果

## 四、默认下一步优先级

建议下一步继续按这个顺序推进：

1. 解析链路从 demo 升级为任务制与持久化：`courseware / parser / cir / tasks`
2. 脚本与发布链：`script / lesson`
3. 问答证据链：`qa`
4. 续讲与指标：`progress / observability`

### 当前解析链 demo 的接手要点

- 接口：`POST /api/v1/lesson/parse`、`GET /api/v1/lesson/parse/{parseId}`
- 现状：`POST` 仅创建任务并返回 `taskStatus=processing`，解析会在本地后台路径继续执行
- 补充：若解析失败，需要通过 `GET` 查询 `failed` 状态与错误信息
- 桥接持久化：当前任务记录文件默认落在 `temp/ai-generate/tasks/tasks.json`，对应日志落在 `temp/ai-generate/tasks/logs/`
- 配置：需要 `A12_LLM_API_BASE_URL`、`A12_LLM_API_KEY`、`A12_LLM_MODEL`、`A12_LLM_TIMEOUT_SECONDS`
- 调试：优先使用 `rest-client/lesson-parse.http` 与 `examples/demo-courseware.pptx`

## 五、如果下次继续开发，先读什么

下次继续时，默认按这个顺序恢复上下文：

1. 先读 [../01-编码入口.md](../01-编码入口.md)
2. 再读 [../03-联动顺序与完成定义.md](../03-联动顺序与完成定义.md)
3. 再读 [../05-接口到代码文件映射.md](../05-接口到代码文件映射.md)
4. 如果是解析链，先看 `backend/app/parser/` 与 `rest-client/lesson-parse.http`
5. 最后根据任务跳到 `../api/` 对应接口文档

## 六、维护要求

每次出现以下情况，都要更新本文件：

- 当前阶段完成度变化
- 新增真实依赖接入
- 当前优先级变化
- 日常编码入口或恢复顺序变化

本轮额外说明：

- `temp/zrt/docs/字段级数据库设计说明书.md` 与 `temp/zrt/docs/mysql建表.sql` 当前可作为数据库落库时的外部字段级参考
- 但仓库内正式基线仍以 `doc/ai-generate/` 为准；只有已经吸收到我方文档的内容，才视为后续开发默认方案
