# Student Plugin Backend

学生端后端已迁移为 FastAPI，并补充了共享数据库配置与 ORM 入口。

## 首次启动

```bash
cd backend/student_plugin
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

## 后续再次启动

```bash
cd backend/student_plugin
.venv\Scripts\activate
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

如果更新过 `requirements.txt`：

```bash
cd backend/student_plugin
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

## 默认配置

- 默认端口：`5000`
- 默认调试 token：`student_demo_token_001`
- 数据库连接：`DATABASE_URL`
- 共享 SQLAlchemy ORM：`backend-common/chaoxing_db`
- 所有接口仍要求带签名的 JSON 请求体，包含 `time` 和 `enc`

## 与教师端一起联调

如果你要同时启动双端后端，请再单独启动教师端 FastAPI：

```bash
cd ../../teacher-ai-course/backend/teacher_plugin
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 3001 --reload
```

如果教师端之前已经准备过虚拟环境，后续只需要：

```bash
cd ../../teacher-ai-course/backend/teacher_plugin
.venv\Scripts\activate
uvicorn app:app --host 0.0.0.0 --port 3001 --reload
```
