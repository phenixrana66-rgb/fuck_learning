# POST /api/v1/platform/syncCourse

## 接口定位
用于同步课程信息，完成外部平台课程与系统内部课程的关联。

## 规划信息
- 模块：平台
- 方法：POST
- 模式：同步
- 后端归属：`backend/app/platform/`

## 核心请求字段
- `platformId`：外部平台 ID
- `courseInfo`：课程信息对象
- `enc`：签名信息

## 核心响应字段
- `internalCourseId`：系统内部课程 ID
- `syncStatus`：同步状态
- `syncTime`：同步时间
- `requestId`：请求追踪 ID

## 对接约束
- 使用 `/api/v1` 前缀。
- 请求与响应统一使用 UTF-8 JSON。
- 平台请求必须校验 `enc` 签名。
- 统一响应结构为 `code / msg / data / requestId`。
