# Teacher AI Course

教师端前端已经统一到仓库根目录维护，教师端后端已经从旧的 Node mock 迁移为 FastAPI。

## 当前结构

- `backend/teacher_plugin/`：教师端 FastAPI
- `mock/server.js`：旧 Node mock，已废弃，不再作为默认启动方式

## 教师端后端首次启动

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning\teacher-ai-course\backend\teacher_plugin
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 3001 --reload
```

## 教师端后端后续再次启动

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning\teacher-ai-course\backend\teacher_plugin
.venv\Scripts\activate
uvicorn app:app --host 0.0.0.0 --port 3001 --reload
```

如果依赖更新过，再执行：

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning\teacher-ai-course\backend\teacher_plugin
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 3001 --reload
```

## 与学生端一起联调

学生端后端也需要单独启动：

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning\student-ai-course\backend\student_plugin
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

前端从仓库根目录启动：

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning
npm run dev:web
```

## 当前后端能力

教师端 FastAPI 当前兼容这组接口，保持前端零改动：

- `POST /api/v1/platform/syncUser`
- `POST /api/v1/platform/syncCourse`
- `POST /api/v1/lesson/parse`
- `POST /api/v1/lesson/generateScript`
- `POST /api/v1/lesson/generateAudio`

默认端口仍是 `3001`，Vite 代理仍然走：

- `/api -> http://localhost:3001`

## 数据库与 ORM

教师端与学生端共用同一套 MySQL 主库和同一套 SQLAlchemy ORM：

- 共享 ORM：`backend-common/chaoxing_db`
- 建表脚本：`docs/mysql建表.sql`
- 初始化测试数据：`docs/init_test_data.sql`

测试数据库中已包含教师端 PPT 资源样例：

- `第九章 压杆稳定_20260401213017.ppt`

该资源已串联到章节 PPT、解析任务、解析结果、讲稿、音频和学生端 lesson 的测试链路中。
