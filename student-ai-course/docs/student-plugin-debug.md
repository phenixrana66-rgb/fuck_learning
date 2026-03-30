# 学生端调试指南

## 1. 本地模拟学习通 iframe 免登

1. 启动前端：`npm run dev`
2. 启动 Flask 适配层：参考 [backend/student_plugin/README.md](../backend/student_plugin/README.md)
3. 使用浏览器访问：

```text
http://localhost:5173/student/home?token=student_demo_token_001
```

页面会读取 query 中的 `token`，模拟学习通将免登 token 传入 iframe 插件。

## 2. 本地 Mock 超星 API

- 前端学生端统一走 `/student-api`
- Vite 代理转发到本地 Flask：`http://localhost:5000`
- Flask 适配层默认启用 Mock 数据，无需真实超星环境即可测试以下接口：
  - `/auth/verify`
  - `/api/v1/getStudentLessonList`
  - `/api/v1/progress/get`
  - `/api/v1/lesson/play`
  - `/api/v1/qa/voiceToText`
  - `/api/v1/qa/interact`
  - `/api/v1/progress/adjust`
  - `/api/v1/lesson/resume`
  - `/api/v1/progress/track`

## 3. 打断提问与续讲测试

1. 在学习中心点击“进入智课”
2. 播放页会先调用 `progress/get` 恢复历史进度，再调用 `lesson/play`
3. 输入文字问题，或点击“语音提问/上传音频”
4. 前端会调用 `qa/interact` 或 `voiceToText -> qa/interact`
5. 点击“续讲”后，前端会依次调用：
   - `progress/adjust`
   - `lesson/resume`
   - `progress/track`

## 4. 核心逻辑验证点

- 音频 `loadedmetadata` 后恢复到历史时间点
- `timeupdate` 每 15 秒自动调用 `progress/track`
- 课件页码根据 anchor `startTime` 自动切换
- 问答返回 `relatedKnowledgePoints`、`understandingLevel`、`resumeAnchor`
- 续讲后音频直接跳回推荐时间点，无需整页刷新

## 5. 并发与性能建议

- 前端对 `progress/track` 做节流，避免高频写入
- 后端将课程结构、课件页码、知识点关系缓存到内存或 Redis
- 问答服务可预先将课件内容向量化，减少上下文匹配耗时
- 10 人并发场景下优先保障 `lesson/play`、`progress/get`、`progress/track` 等轻量接口
