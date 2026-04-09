# 学生端调试指南

## 1. 本地模拟学习通 iframe 免登

1. 启动前端：`npm run dev`
2. 启动学生端后端：参考 [backend/student_plugin/README.md](../backend/student_plugin/README.md)
3. 浏览器访问：

```text
http://localhost:5173/student/home?token=student_demo_token_001
```

页面会读取 query 中的 `token`，模拟学习通将免登 token 传入 iframe 插件。

## 2. 本地 Mock 超星 API

- 前端学生端统一请求 `/student-api`
- Vite 代理转发到本地 FastAPI：`http://localhost:5000`
- FastAPI 适配层默认启用 Mock 数据，无需真实超星环境即可联调以下接口：
  - `/auth/verify`
  - `/api/v1/getStudentLessonList`
  - `/api/v1/progress/get`
  - `/api/v1/lesson/play`
  - `/api/v1/qa/voiceToText`
  - `/api/v1/qa/interact`
  - `/api/v1/progress/adjust`
  - `/api/v1/lesson/resume`
  - `/api/v1/progress/track`

## 3. 提问与续学测试

1. 在学生端进入课程详情页
2. 页面会先调用 `progress/get` 恢复历史进度，再调用 `lesson/play`
3. 输入文字问题或使用语音输入
4. 前端会调用 `qa/interact` 或 `voiceToText -> qa/interact`
5. 触发续学后，前端会依次调用：
   - `progress/adjust`
   - `lesson/resume`
   - `progress/track`

## 4. 核心验证点

- 音频 `loadedmetadata` 后恢复到历史时间点
- `timeupdate` 每 15 秒自动调用 `progress/track`
- 课件页码根据 anchor `startTime` 自动切换
- 问答返回 `relatedKnowledgePoints`、`understandingLevel`、`resumeAnchor`
- 续学后音频直接跳回推荐时间点，无需整页刷新
