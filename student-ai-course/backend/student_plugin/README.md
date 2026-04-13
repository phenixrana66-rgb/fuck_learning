# Student Plugin Backend

当前目录保留为学生端兼容入口，但运行时已经复用仓库根目录的统一 backend。

## 目录定位

当前目录：

```powershell
student-ai-course/backend/student_plugin
```

共享数据库模型目录：

```powershell
backend-common/chaoxing_db
```

## 当前口径

- 统一后端端口：`3001`
- 前端代理前缀：`/student-api`
- 默认测试 token：`student_demo_token_001`
- 数据库连接配置：`DATABASE_URL`

## 推荐启动方式

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 3001 --reload
```

兼容入口 `student-ai-course/backend/student_plugin/app.py` 仍然存在，但它现在导出的也是统一后的 `backend.app.main:app`，不再要求单独维持一个 `5000` 端口服务。

## 启动前端

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning
npm run dev:web
```

## 如需从兼容入口启动

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning\student-ai-course\backend\student_plugin
uvicorn app:app --host 127.0.0.1 --port 3001 --reload
```

这个方式只保留兼容性，不再是推荐主路径。

## 数据库说明

当前后端不再只依赖内存 mock，已经具备数据库接入基础：

- MySQL 主库：`chaoxing_ai_course`
- 建表脚本：`docs/mysql建表.sql`
- 初始化测试数据：`docs/init_test_data.sql`
- 共享 ORM：`backend-common/chaoxing_db`

初始化数据库：

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning
mysql -u root -p
```

然后在 MySQL 控制台执行：

```sql
SOURCE D:/服务外包（学习通）/xuexitong/fuck_learning/docs/mysql建表.sql;
SOURCE D:/服务外包（学习通）/xuexitong/fuck_learning/docs/init_test_data.sql;
```

## 当前业务覆盖

当前数据库和共享模型已经覆盖：

- lesson / unit / section / page / anchor
- 页级学习进度、章节进度、课程总进度
- 章节练习、作答与掌握度
- AI 问答会话与消息
- 通知

## 当前口径

### 学习进度

- 学生只要打开过某一页，该页就算已读
- 章节学习进度 = `round(已读页数 / 总页数 * 100)`

### 掌握度

- 章节掌握度 = `round(章节学习进度 * 0.4 + 章节练习得分率 * 0.6)`
- AI 问答理解度当前不参与正式掌握度计算
