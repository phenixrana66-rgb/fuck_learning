# POST /api/v1/progress/adjust

## 接口定位
用于根据理解程度与学习进度，返回续讲、补讲或节奏调整方案。

## 规划信息
- 模块：进度
- 方法：POST
- 模式：同步
- 后端归属：`backend/app/progress/`

## 核心请求字段
- `userId`：学生用户 ID
- `lessonId`：智课 ID
- `currentSectionId`：当前章节 ID
- `understandingLevel`：理解程度
- `qaRecordId`：问答记录 ID
- `enc`：签名信息

## 核心响应字段
- `adjustPlan.continueSectionId`：续讲章节 ID
- `adjustPlan.adjustType`：调整类型
- `adjustPlan.supplementContent`：补讲内容
- `adjustPlan.nextSections`：后续章节调整建议
- `requestId`：请求追踪 ID

## 对接约束
- 内部需覆盖 `normal_continue`、`supplement_current`、`fallback_prerequisite`、`accelerate_following` 四类决策。
- 对外需兼容 `normal / supplement / accelerate` 的开放 API 表达。
