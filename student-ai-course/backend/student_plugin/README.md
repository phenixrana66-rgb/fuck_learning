# Student Plugin Backend

学生端后端适配层已迁移为 FastAPI，用于本地联调学习通免登、课程列表、课程播放、进度追踪、问答和通知接口。

## 首次启动

```bash
cd backend/student_plugin
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

## 后续再次启动

如果之前已经成功运行过，通常只需要：

```bash
cd backend/student_plugin
.venv\Scripts\activate
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

如果你更新过 `requirements.txt`，再次启动前先执行：

```bash
cd backend/student_plugin
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

## 默认配置

- 默认端口：`5000`
- 默认调试 token：`student_demo_token_001`
- 所有接口仍要求带签名的 JSON 请求体，包含 `time` 和 `enc`
- 本地调试默认开启：`CHAOXING_MOCK_MODE=true`
- 停止服务时按 `Ctrl + C`

## 联调说明

- 前端学生端统一请求 `/student-api`
- Vite 会把 `/student-api` 代理到 `http://localhost:5000`
- 接口路径、请求方式和响应结构保持不变，前端无需改动

## 与教师端一起联调

如果你要同时启动双端后端，请再单独启动教师端 mock：

```bash
node ../../teacher-ai-course/mock/server.js
```

或在仓库根目录执行：

```bash
node teacher-ai-course/mock/server.js
```
