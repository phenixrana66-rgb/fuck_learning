## 8. API 规划与平台对接策略
### 8.1 对外接口清单

| 模块 | 接口 | 方法 | 模式 | 说明 |
|---|---|---|---|---|
| 平台 | `/api/v1/platform/syncCourse` | POST | 同步 | 同步课程信息 |
| 平台 | `/api/v1/platform/syncUser` | POST | 同步 | 同步用户信息并返回内部身份映射 |
| 智课生成 | `/api/v1/lesson/parse` | POST | 当前为同步完成式 demo，长期目标为异步提交 | 当前可读取 `.pptx`、生成 `structurePreview` 并返回 `parseId` |
| 智课生成 | `/api/v1/lesson/parse/{parseId}` | GET | 查询 | 查询解析状态与结构化结果 |
| 智课生成 | `/api/v1/lesson/generateScript` | POST | 同步 / 可异步 | 生成结构化讲稿 |
| 智课生成 | `/api/v1/scripts/{scriptId}` | GET | 查询 | 获取脚本详情 |
| 智课生成 | `/api/v1/scripts/{scriptId}` | PUT | 保存 | 保存教师编辑稿 |
| 智课生成 | `/api/v1/lesson/generateAudio` | POST | 异步提交 | 生成整课或分章节音频 |
| 智课生成 | `/api/v1/lesson/publish` | POST | 异步提交 | 生成正式 LessonPackage |
| 学习播放 | `/api/v1/lesson/play` | POST | 同步 | 返回学生端播放装配数据 |
| 问答 | `/api/v1/qa/voiceToText` | POST | 同步 | 语音转文字 |
| 问答 | `/api/v1/qa/interact` | POST | 同步 | 证据约束问答 |
| 问答 | `/api/v1/qa/session/{sessionId}` | GET | 查询 | 查询多轮问答上下文 |
| 进度 | `/api/v1/progress/track` | POST | 同步 | 记录学习进度 |
| 进度 | `/api/v1/progress/adjust` | POST | 同步 | 获取续讲 / 补讲建议 |

### 8.2 API 兼容原则

- 统一采用 `/api/v1` 前缀；
- 请求与返回统一使用 UTF-8 JSON；
- 统一返回 `code`、`msg`、`data`、`requestId`；
- 所有新增字段尽量设计为非必填兼容扩展字段；
- `lesson/parse`、`lesson/generateAudio`、`lesson/publish` 必须支持异步模式；
- 平台对接请求必须支持 `enc` 签名校验。

这些原则直接来自 `requirements-analysis/08-平台对接与开放API需求.md`，因此本章的定位不是重新发明接口规则，而是把需求基线落实成正式架构接口族。

### 8.3 签名与安全约定

正式对接策略沿用开放 API 文档中的思路：

- 使用 `enc` 作为签名字段；
- 签名由“参数升序拼接 + staticKey + time”计算；
- 服务端重复计算并校验；
- 鉴权失败返回 `401 / 403`；
- 所有响应都必须返回 `requestId`，便于排查。
