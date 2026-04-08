# POST /api/v1/lesson/generateAudio

## 接口定位
用于生成整课或分章节音频，产出 `AudioAsset / SectionAudio`。

## 规划信息
- 模块：智课生成
- 方法：POST
- 模式：当前代码为同步完成式 demo，长期目标仍为异步任务模式
- 后端归属：`backend/app/lesson/`、`backend/app/tasks/`

## 核心请求字段
- `scriptId`：脚本 ID
- `voiceType`：音色类型
- `audioFormat`：音频格式
- `sectionIds`：指定生成的章节 ID 列表
- `enc`：签名信息

## 核心响应字段
- `audioId`：音频任务或资源 ID
- `audioUrl`：整课音频地址
- `audioInfo`：音频文件信息
- `sectionAudios`：分章节音频信息
- `requestId`：请求追踪 ID

## 当前代码行为（截至本次实现）
- 当前 `generateAudio` 会读取真实 `scriptId` 对应的脚本结构；
- 若 `scriptId` 不存在，或 `sectionIds` 中存在脚本里没有的章节，会直接返回错误；
- 若不传 `sectionIds`，会默认基于整份脚本全部章节生成音频；
- 当前返回的 `sectionAudios` 数量与脚本真实章节数保持一致；
- 当前会记录 `lesson.generateAudio` 任务，但接口本身会直接返回可用于后续发布的 `audioId` 与完整音频信息；
- 当前音频 URL 仍是 demo 地址，不是实际 TTS 产物。

## 对接约束
- 必须支持异步任务模式。
- 需要支持章节级拆分，便于断点续播与补讲插入。
- 当前 happy path 要求先生成脚本，再使用返回的 `scriptId` 调用本接口。
- 统一响应结构为 `code / msg / data / requestId`。
