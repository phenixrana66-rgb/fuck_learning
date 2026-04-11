# Student AI Course

当前目录保留学生端相关说明和学生端 FastAPI 后端。

## 当前结构

- `backend/student_plugin/`：学生端 FastAPI 后端
- 根目录 `src/`：学生端与教师端共用的统一前端

## 前端说明

学生端前端已经统一到仓库根目录维护，请在仓库根目录执行：

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning
npm install
npm run dev:web
```

## 学生端后端首次启动

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning\student-ai-course\backend\student_plugin
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

## 学生端后端后续再次启动

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning\student-ai-course\backend\student_plugin
.venv\Scripts\activate
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

如果更新过依赖，再补一次：

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning\student-ai-course\backend\student_plugin
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

## 与教师端一起联调

教师端后端也已经迁移到 FastAPI，请在另一个终端执行：

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning\teacher-ai-course\backend\teacher_plugin
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 3001 --reload
```

然后回到仓库根目录启动前端：

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning
npm run dev:web
```

## 数据库说明

学生端与教师端共用同一套 MySQL 主库和同一套 SQLAlchemy ORM：

- 共享 ORM：`backend-common/chaoxing_db`
- 建表脚本：`docs/mysql建表.sql`
- 初始化测试数据：`docs/init_test_data.sql`

如需先初始化数据库，请在仓库根目录执行：

```powershell
mysql -u root -p
```

然后在 MySQL 控制台执行：

```sql
SOURCE D:/服务外包（学习通）/xuexitong/fuck_learning/docs/mysql建表.sql;
SOURCE D:/服务外包（学习通）/xuexitong/fuck_learning/docs/init_test_data.sql;
```
