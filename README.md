# fuck_learning

前端入口统一在仓库根目录，学生端和教师端共用一套前端工程；双端后端现在都使用 FastAPI，并共用一套 MySQL 主库与 SQLAlchemy ORM。

## 启动前准备

先在仓库根目录安装前端依赖：

```bash
npm install
```

如果要走数据库联调，先初始化 MySQL：

```bash
mysql -u root -p < docs/mysql建表.sql
mysql -u root -p < docs/init_test_data.sql
```

## 双端后端如何启动

建议开三个终端，分别启动学生端后端、教师端后端和前端。

### 第 1 步：启动学生端后端

首次运行：

```bash
cd student-ai-course/backend/student_plugin
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

后续再次启动：

```bash
cd student-ai-course/backend/student_plugin
.venv\Scripts\activate
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

如果你更新过 `requirements.txt`：

```bash
cd student-ai-course/backend/student_plugin
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

说明：

- 学生端后端端口：`5000`
- 前端学生端请求代理：`/student-api`

### 第 2 步：启动教师端后端

首次运行：

```bash
cd teacher-ai-course/backend/teacher_plugin
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 3001 --reload
```

后续再次启动：

```bash
cd teacher-ai-course/backend/teacher_plugin
.venv\Scripts\activate
uvicorn app:app --host 0.0.0.0 --port 3001 --reload
```

如果你更新过 `requirements.txt`：

```bash
cd teacher-ai-course/backend/teacher_plugin
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 3001 --reload
```

说明：

- 教师端后端端口：`3001`
- 前端教师端请求代理：`/api`

### 第 3 步：启动前端

所有 npm 命令都必须在仓库根目录执行：

```bash
cd D:\服务外包（学习通）\xuexitong\fuck_learning
npm run dev:web
```

这里使用 `npm run dev:web`，不要依赖 `npm run dev` 自动拉起后端。后端现在需要分别手动启动。

## 默认访问入口

- 首页：`http://localhost:5173/`
- 学生端：`http://localhost:5173/student/home?token=student_demo_token_001`
- 教师端：`http://localhost:5173/teacher/login`

## 后端说明

- 学生端 FastAPI：`student-ai-course/backend/student_plugin`
- 教师端 FastAPI：`teacher-ai-course/backend/teacher_plugin`
- 共享 SQLAlchemy ORM：`backend-common/chaoxing_db`
- 初始化测试数据中已登记测试 PPT：`第九章 压杆稳定_20260401213017.ppt`

## 构建

在仓库根目录执行：

```bash
npm run build
```
