# POST /api/v1/qa/interact

## 接口定位
用于在当前学习节点上下文中执行证据约束问答。

## 规划信息
- 模块：问答
- 方法：POST
- 模式：同步
- 后端归属：`backend/app/qa/`、`backend/app/cir/`

## 核心请求字段
- `schoolId`：学校 ID
- `userId`：学生用户 ID
- `courseId`：课程 ID
- `lessonId`：智课 ID
- `sessionId`：问答会话 ID
- `questionType`：提问类型
- `questionContent`：提问内容
- `currentSectionId`：当前学习章节 ID
- `historyQa`：历史问答记录
- `enc`：签名信息

## 核心响应字段
- `answerId`：回答记录 ID
- `answerContent`：回答内容
- `answerType`：回答类型
- `relatedKnowledge`：关联知识点
- `suggestions`：追问建议
- `understandingLevel`：理解程度
- `evidencePages`：来源页码列表（扩展字段）
- `evidenceSpans`：证据片段列表（扩展字段）
- `relatedNodeIds`：关联节点（扩展字段）
- `answerConfidence`：回答可信度（扩展字段）
- `requestId`：请求追踪 ID

## 对接约束
- 回答必须受当前节点、相邻节点与必要前置节点约束。
- 证据不足时必须保守回答。
- 新增字段应以非必填兼容扩展字段方式追加。
