# POST /api/v1/lesson/generateScript

## 接口定位
基于解析结果生成结构化讲稿，衔接 `CIR -> ScriptDraft / ScriptVersion`。

## 规划信息
- 模块：智课生成
- 方法：POST
- 模式：同步 / 可异步
- 后端归属：`backend/app/script/`、`backend/app/cir/`

## 核心请求字段
- `parseId`：课件解析任务 ID
- `teachingStyle`：讲授风格
- `speechSpeed`：语速适配
- `customOpening`：自定义开场白
- `enc`：签名信息

## 核心响应字段
- `scriptId`：脚本 ID
- `scriptStructure`：脚本结构
- `editUrl`：教师编辑地址或编辑入口信息
- `audioGenerateUrl`：后续音频生成接口地址
- `requestId`：请求追踪 ID

## 当前代码行为（截至本次实现）
- 当前 `generateScript` 会读取已完成的 `parseId` 对应解析结果；
- 若解析任务不存在或尚未完成，会直接返回错误；
- 当前脚本段落会基于 `parse` 产出的 `CIR.nodes` 生成，而不是固定示例段落；
- `sectionName`、`relatedChapterId`、`relatedPage`、`keyPoints` 会尽量继承解析结果中的真实结构；
- 当前脚本主记录会持久化到数据库表 `script_records`，服务重启后仍可查询与更新。

## 对接约束
- 首版可同步实现，批量或长耗时场景允许异步化。
- 输出必须允许教师继续编辑，不直接替代教师意图。
- 当前 happy path 要求先完成 `lesson/parse`，再使用返回的 `parseId` 调用本接口。
- 统一响应结构为 `code / msg / data / requestId`。
