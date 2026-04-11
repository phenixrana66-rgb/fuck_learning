# Teacher Plugin Backend

教师端后端已经从旧 Node mock 迁移到 FastAPI，并接入共享 MySQL 主库和共享 SQLAlchemy ORM。

## 目录定位

当前目录：

```powershell
teacher-ai-course/backend/teacher_plugin
```

共享 ORM 目录：

```powershell
backend-common/chaoxing_db
```

## 默认配置

- 默认端口：`3001`
- 前端代理前缀：`/api`
- 数据库连接配置：`DATABASE_URL`

## 当前兼容接口

- `POST /api/v1/platform/syncUser`
- `POST /api/v1/platform/syncCourse`
- `POST /api/v1/lesson/parse`
- `POST /api/v1/lesson/generateScript`
- `POST /api/v1/lesson/generateAudio`

接口路径、方法和返回结构保持和原教师前端兼容。

## 首次启动

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning\teacher-ai-course\backend\teacher_plugin
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 3001 --reload
```

## 后续再次启动

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning\teacher-ai-course\backend\teacher_plugin
.venv\Scripts\activate
uvicorn app:app --host 0.0.0.0 --port 3001 --reload
```

如果依赖更新过：

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning\teacher-ai-course\backend\teacher_plugin
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 3001 --reload
```

## 与学生端和前端联调

学生端后端：

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning\student-ai-course\backend\student_plugin
.venv\Scripts\activate
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

前端：

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning
npm run dev:web
```

## 数据库说明

教师端和学生端共用：

- MySQL 主库：`chaoxing_ai_course`
- 建表脚本：`docs/mysql建表.sql`
- 初始化测试数据：`docs/init_test_data.sql`
- 共享 ORM：`backend-common/chaoxing_db`

当前测试数据已包含教师端测试 PPT 资源：

- `第九章 压杆稳定_20260401213017.ppt`

用于联调这条链路：

- 上传章节 PPT
- 解析任务
- 解析结果与知识树
- 讲稿生成
- 音频生成
- 发布到学生端 lesson
