# GET /api/v1/qa/session/{sessionId}

## 接口定位
用于查询多轮问答上下文与历史记录。

## 规划信息
- 模块：问答
- 方法：GET
- 模式：查询
- 后端归属：`backend/app/qa/`

## 核心路径字段
- `sessionId`：问答会话 ID

## 核心响应字段
- `sessionId`：问答会话 ID
- `historyQa`：历史问答记录
- `currentSectionId`：当前关联章节 ID
- `understandingLevel`：最近一次理解程度
- `requestId`：请求追踪 ID

## 对接约束
- 仅保留必要多轮上下文，避免上下文无限膨胀。
- 返回结果应服务于多轮问答续接与学习态恢复。
