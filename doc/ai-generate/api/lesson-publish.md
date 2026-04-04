# POST /api/v1/lesson/publish

## 接口定位
用于冻结 CIR、脚本、音频版本并生成正式 `LessonPackage`。

## 规划信息
- 模块：智课生成
- 方法：POST
- 模式：异步提交
- 后端归属：`backend/app/lesson/`、`backend/app/tasks/`

## 核心请求字段
- `coursewareId`：课件 ID
- `scriptId`：脚本 ID
- `audioId`：音频资源 ID
- `publishOptions`：发布选项
- `enc`：签名信息或会话鉴权信息

## 核心响应字段
- `lessonId`：正式智课 ID
- `publishStatus`：发布状态
- `lessonPackageRef`：播放包引用
- `requestId`：请求追踪 ID

## 对接约束
- 必须支持异步任务模式。
- 发布时需形成稳定快照，明确区分发布态与运行态。
