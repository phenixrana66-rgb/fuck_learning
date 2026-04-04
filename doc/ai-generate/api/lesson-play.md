# POST /api/v1/lesson/play

## 接口定位
用于向学生端返回播放装配数据，作为学习运行态入口。

## 规划信息
- 模块：学习播放
- 方法：POST
- 模式：同步
- 后端归属：`backend/app/lesson/`、`backend/app/progress/`

## 核心请求字段
- `lessonId`：智课 ID
- `userId`：学生用户 ID
- `resumeContext`：续播上下文（可选）
- `enc`：签名信息或会话鉴权信息

## 核心响应字段
- `lessonId`：智课 ID
- `nodeSequence`：节点顺序
- `scriptRefs`：脚本引用
- `audioRefs`：音频引用
- `currentSectionId`：当前章节 ID
- `requestId`：请求追踪 ID

## 对接约束
- 返回结果需满足学生端播放、问答返回后恢复播放、断点续播三类场景。
- 运行态数据不得直接覆盖发布态快照。
