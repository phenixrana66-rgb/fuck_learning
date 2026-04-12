# POST /api/v1/lesson/parse

## 接口定位
用于上传或提交课件解析任务，进入智课生成主链路的起点。

## 规划信息
- 模块：智课生成
- 方法：POST
- 模式：当前代码已改为本地后台执行式任务提交，长期目标仍为接入正式异步任务系统
- 后端归属：`backend/app/courseware/`、`backend/app/parser/`、`backend/app/tasks/`

## 核心请求字段
- `schoolId`：学校 ID
- `userId`：教师或上传用户 ID
- `courseId`：课程 ID
- `fileType`：当前接口字段仍沿用 `ppt` / `pdf` 枚举；但**现有 demo 实现只支持 `.pptx` 文件解析**
- `fileUrl`：课件文件 URL
- `isExtractKeyPoint`：是否自动提取重点
- `enc`：签名信息

## 核心响应字段
- `parseId`：解析任务 ID
- `fileInfo`：文件信息
- `structurePreview`：结构预览
- `taskStatus`：任务状态
- `requestId`：请求追踪 ID

## 当前代码行为（截至本次实现）
- 支持读取本地路径、`file://` 和 `http/https` 可访问的 `.pptx` 文件
- 使用 `python-pptx` 提取 slide 标题、正文、表格、备注
- 使用 OpenAI 兼容 `chat/completions` 接口生成章节结构
- `POST` 成功后会立即返回 `parseId` 与 `taskStatus=processing`，解析执行在本地后台线程中继续完成
- 当前接受态响应模型虽然保留了 `fileInfo`、`structurePreview` 字段，但创建任务时通常为空，完整结果需继续调用 `GET /api/v1/lesson/parse/{parseId}`
- `POST` 响应本身不直接返回 `cir`，如需完整 `cir` 请继续调用 `GET /api/v1/lesson/parse/{parseId}`
- 当前传入 `pdf` 或非 `.pptx` 文件时，任务会在后台失败，随后可通过 `GET /api/v1/lesson/parse/{parseId}` 查询失败态
- 当前解析任务主记录会持久化到数据库表 `task_records`，记录状态、进度、结果、错误与时间戳信息

## 当前依赖配置
- `A12_LLM_API_BASE_URL`
- `A12_LLM_API_KEY`
- `A12_LLM_MODEL`
- `A12_LLM_TIMEOUT_SECONDS`

## 当前联调方式
- 测试文件：`rest-client/lesson-parse.http`
- 示例课件：`examples/demo-courseware.pptx`

## 对接约束
- 长期目标仍应支持异步任务模式。
- 当前成功提交只代表任务已创建，不代表解析已完成。
- 当前失败场景由查询接口暴露，提交接口不再同步返回解析失败结果。
- 当前任务过程日志位于 `temp/ai-generate/tasks/logs/`，但日志不是任务主状态源。
- 统一响应结构为 `code / msg / data / requestId`。
