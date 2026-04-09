# Teacher AI Course

教师端前端已迁移到仓库根目录统一维护，教师端后端也已从 Node mock 迁移为 FastAPI。

当前目录保留内容：

- `backend/teacher_plugin` 教师端 FastAPI 服务
- `mock/server.js` 旧 Node mock，已废弃，不再作为默认启动方式

## 首次启动教师端后端

```bash
cd backend/teacher_plugin
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 3001 --reload
```

## 后续再次启动教师端后端

```bash
cd backend/teacher_plugin
.venv\Scripts\activate
uvicorn app:app --host 0.0.0.0 --port 3001 --reload
```

## 与学生端一起联调

如果你要同时启动双端后端：

1. 在一个终端启动学生端 FastAPI
2. 在另一个终端启动教师端 FastAPI

教师端 FastAPI 启动命令：

```bash
cd teacher-ai-course/backend/teacher_plugin
.venv\Scripts\activate
uvicorn app:app --host 0.0.0.0 --port 3001 --reload
```

教师端与学生端共用一套 MySQL 主库和一套 SQLAlchemy ORM，公共模型目录：

```bash
backend-common/chaoxing_db
```

## 前端联调注意

如果教师端后端已经手动启动，前端请在仓库根目录执行：

```bash
npm run dev:web
```
