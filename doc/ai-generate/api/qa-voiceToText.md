# POST /api/v1/qa/voiceToText

## 接口定位
用于把学生语音问题转换成文字，供后续 `qa/interact` 使用。

## 规划信息
- 模块：问答
- 方法：POST
- 模式：同步
- 后端归属：`backend/app/qa/`

## 核心请求字段
- `voiceUrl`：语音文件 URL
- `voiceDuration`：语音时长
- `language`：语言类型
- `enc`：签名信息

## 核心响应字段
- `text`：转写文本
- `confidence`：识别置信度
- `timestamp`：识别时间
- `requestId`：请求追踪 ID

## 对接约束
- 只负责 ASR 转写，不直接生成问答结果。
- 输出结果应可直接传入 `POST /api/v1/qa/interact`。
