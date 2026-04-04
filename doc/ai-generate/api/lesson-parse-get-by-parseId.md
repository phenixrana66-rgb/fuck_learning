# GET /api/v1/lesson/parse/{parseId}

## 接口定位
用于查询解析状态，以及在完成后返回结构化结果。

## 规划信息
- 模块：智课生成
- 方法：GET
- 模式：查询
- 后端归属：`backend/app/courseware/`

## 核心路径字段
- `parseId`：解析任务 ID

## 核心响应字段
- `parseId`：解析任务 ID
- `fileInfo`：文件信息
- `taskStatus`：任务状态
- `structurePreview`：结构预览
- `cir`：课程中间表示（完成后返回）
- `progressPercent`：进度百分比
- `requestId`：请求追踪 ID

## 对接约束
- 与 `POST /api/v1/lesson/parse` 配套使用。
- 当前 demo 中查询结果直接返回完成态结构化结果。
- 未找到 `parseId` 时当前返回 404。
- 长期仍建议覆盖处理中、完成、失败三类状态，并由真实任务系统驱动。
- 完成态需支持返回结构化结果或其访问引用。
