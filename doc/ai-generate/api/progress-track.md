# POST /api/v1/progress/track

## 接口定位
用于记录学生学习进度与最近问答关联信息。

## 规划信息
- 模块：进度
- 方法：POST
- 模式：同步
- 后端归属：`backend/app/progress/`

## 核心请求字段
- `schoolId`：学校 ID
- `userId`：学生用户 ID
- `courseId`：课程 ID
- `lessonId`：智课 ID
- `currentSectionId`：当前学习章节 ID
- `progressPercent`：章节学习进度
- `lastOperateTime`：最后操作时间
- `qaRecordId`：最近问答记录 ID
- `enc`：签名信息

## 核心响应字段
- `trackId`：进度记录 ID
- `totalProgress`：总学习进度
- `nextSectionSuggest`：建议后续学习章节
- `requestId`：请求追踪 ID

## 对接约束
- 需要支撑学习运行态记录与问答后的续接判断。
- 返回结果应可被学生端进度展示直接消费。
