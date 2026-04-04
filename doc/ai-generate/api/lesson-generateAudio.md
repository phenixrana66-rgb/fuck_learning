# POST /api/v1/lesson/generateAudio

## 接口定位
用于生成整课或分章节音频，产出 `AudioAsset / SectionAudio`。

## 规划信息
- 模块：智课生成
- 方法：POST
- 模式：异步提交
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

## 对接约束
- 必须支持异步任务模式。
- 需要支持章节级拆分，便于断点续播与补讲插入。
- 统一响应结构为 `code / msg / data / requestId`。
