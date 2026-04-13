# fuck_learning

当前仓库采用统一前端 + 单 FastAPI 后端 + 一套 MySQL 主库：

- 前端：仓库根目录下的 Vite 项目
- 统一后端入口：`backend.app.main`
- 共享 ORM：`backend/chaoxing_db`
- 建表与测试数据：`docs/mysql建表.sql`、`docs/init_test_data.sql`

## 目录说明

- `src/`：前端代码，学生端和教师端共用同一个 Vite 工程
- `backend/`：仓库唯一后端目录，包含 FastAPI 应用与共享 SQLAlchemy 模型
- `public/lesson-previews/pressure-stability/`：压杆稳定章节的测试页图资源
- `docs/mysql建表.sql`：MySQL 建表脚本
- `docs/init_test_data.sql`：初始化测试数据脚本

## 压杆稳定 PPT 预览说明

- 学生端“压杆稳定”知识学习页现在使用真实 PPT 导出的页图，不再使用示意 SVG 作为正式展示。
- 页图资源默认放在 `public/lesson-previews/pressure-stability/`，文件名格式为 `page-1.png`、`page-2.png`。
- 教师端执行 `POST /api/v1/lesson/parse` 的 `upload/status` 链路时，会尝试把上传的 PPT 导出为 PNG 页图，并同步补齐章节分页数据。
- 当前这条导出链路依赖本机已安装桌面版 Microsoft PowerPoint，因为服务端通过 Windows COM 调用 PowerPoint 执行 `SaveAs(..., 18)` 导出图片。
- 如果机器上没有安装 PowerPoint，教师端解析状态会失败，学生端仍只能看到已有的本地测试页图，不能自动生成新的课件页图。

## 当前默认端口

- 前端：`5173`
- 统一后端：`3001`

Vite 代理：

- `/student-api -> http://127.0.0.1:3001`
- `/api -> http://127.0.0.1:3001`

## 当前默认数据库连接

当前代码默认使用下面这条连接串：

```powershell
mysql+pymysql://root:123456@127.0.0.1:3306/chaoxing_ai_course?charset=utf8mb4
```

如果你本机 MySQL 不是这个账号密码，需要在启动前先设置 `DATABASE_URL`，否则统一后端在访问数据库时会返回 500。

PowerShell 设置方式：

```powershell
$env:DATABASE_URL="mysql+pymysql://root:你的密码@127.0.0.1:3306/chaoxing_ai_course?charset=utf8mb4"
```

建议在启动统一后端前先设置一次。

## 初始化数据库

先确认本机 MySQL 已启动，然后在 PowerShell 中执行：

```powershell
mysql -u root -p
```

进入 MySQL 后执行：

```sql
SOURCE D:/服务外包（学习通）/xuexitong/fuck_learning/docs/mysql建表.sql;
SOURCE D:/服务外包（学习通）/xuexitong/fuck_learning/docs/init_test_data.sql;
```

如果你一定要在 PowerShell 里直接执行重定向，需走 `cmd /c`：

```powershell
cmd /c "mysql -u root -p < docs\mysql建表.sql"
cmd /c "mysql -u root -p < docs\init_test_data.sql"
```

## 首次启动

先进入仓库根目录：

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning
```

安装前端依赖：

```powershell
npm install
```

### 1. 安装后端依赖并启动统一后端

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning
pip install -r requirements.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 3001 --reload
```

### 2. 启动前端

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning
npm run dev:web
```

## 后续再次启动

如果依赖已经装好，只需要重新启动统一后端与前端。

### 统一后端再次启动

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 3001 --reload
```

### 前端再次启动

```powershell
cd D:\服务外包（学习通）\xuexitong\fuck_learning
npm run dev:web
```

## 依赖更新后怎么启动

如果后端依赖有变更，请在仓库根目录对应的 Python 环境里重新执行 `pip install -r requirements.txt` 后，再启动统一后端。

## 最新访问方式

### 前端入口

- 首页：`http://localhost:5173/`
- 学生端首页：`http://localhost:5173/student/home?token=student_demo_token_001`
- 教师端登录页：`http://localhost:5173/teacher/login`

### 教师端登录方式

教师端当前测试 token 仍然是：

```text
test_token_001
```

访问 `http://localhost:5173/teacher/login` 后，在输入框中填入 `test_token_001`，点击“同步用户与课程”即可。

### 学生端访问方式

学生端测试 token：

```text
student_demo_token_001
```

直接打开：

```text
http://localhost:5173/student/home?token=student_demo_token_001
```

即可进入学生首页。

## 当前已验证可用的后端链路

我已按本地真实启动方式验证通过以下接口：

### 教师端

- `POST http://127.0.0.1:3001/api/v1/platform/syncUser`
- `POST http://127.0.0.1:3001/api/v1/platform/syncCourse`

其中 `test_token_001` 当前可正常返回教师信息和课程列表。

### 学生端

- `POST http://127.0.0.1:3001/student-api/auth/verify`
- `POST http://127.0.0.1:3001/student-api/api/v1/getStudentLessonList`
- `POST http://127.0.0.1:3001/student-api/api/v1/lesson/play`
- `POST http://127.0.0.1:3001/student-api/api/v1/lesson/section/detail`
- `POST http://127.0.0.1:3001/student-api/api/v1/progress/page/read`

学生端新加的“压杆稳定”知识学习链路也已验证通过：

- 章节详情可返回
- 页级阅读进度可写回
- 学习进度与掌握度会更新

## 这次双端进不去的原因

本次排查确认有两个实际问题：

1. 后端依赖里缺少 `cryptography`
   - MySQL 8 默认常用 `caching_sha2_password`
   - 没有这个包时，PyMySQL 会直接报运行时错误

2. 默认数据库连接串写的是错误密码
   - 原先默认值是 `root:password`
   - 你本机实际可用的是 `root:123456`
   - 所以教师端输入 `test_token_001` 后，一查数据库就会返回 500
   - 学生端访问数据库增强接口时也会表现成服务器异常

当前仓库已将这两个问题修正：

- 根目录 `requirements.txt` 已加入 `PyMySQL` 与 `cryptography`
- 默认 `DATABASE_URL` 已改成 `root:123456`

如果你本机后续改了 MySQL 密码，请记得同步设置 `DATABASE_URL`。

## 构建

前端构建命令：

```powershell
npm run build
```

## 相关文件

- [根 README](/D:/服务外包（学习通）/xuexitong/fuck_learning/README.md)
- [MySQL 建表说明](/D:/服务外包（学习通）/xuexitong/fuck_learning/docs/MySQL建表执行说明.md)
