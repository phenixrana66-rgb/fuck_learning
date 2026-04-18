# fuck_learning

本项目是一个前后端一体的课程学习系统：

- 前端：Vite + Vue 3，位于仓库根目录 `src/`
- 后端：FastAPI，入口为 `backend.app.main:app`
- 数据库：MySQL
- 学生问答：支持流式 LLM 输出、语音输入、章节问答

## 目录说明

- `src/`：前端页面与组件
- `backend/`：后端业务代码
- `backend/chaoxing_db/`：ORM / 数据模型相关
- `docs/mysql建表.sql`：MySQL 建表脚本
- `docs/init_test_data.sql`：测试数据初始化脚本
- `start-backend.ps1`：后端启动脚本
- `start-frontend.ps1`：前端启动脚本

## 默认端口

- 前端开发服务：`5173`
- 后端服务：`3001`

Vite 代理配置：

- `/student-api -> http://127.0.0.1:3001`
- `/api -> http://127.0.0.1:3001`

## 环境要求

- Node.js 18+
- npm 9+
- Python 3.11+
- MySQL 8.x

## 初次使用前必须准备的内容

### 1. 安装前后端依赖

在项目根目录执行：

```powershell
cd "D:\服务外包（学习通）\xuexitong\fuck_learning"
npm install
pip install -r requirements.txt
```

如果你使用虚拟环境，建议先激活虚拟环境再执行 `pip install -r requirements.txt`。

### 2. 准备 MySQL 数据库

先确认本机 MySQL 已启动，然后创建数据库：

```sql
CREATE DATABASE chaoxing_ai_course DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```

再导入建表脚本和初始化测试数据：

```powershell
mysql -u root -p chaoxing_ai_course < "D:\服务外包（学习通）\xuexitong\fuck_learning\docs\mysql建表.sql"
mysql -u root -p chaoxing_ai_course < "D:\服务外包（学习通）\xuexitong\fuck_learning\docs\init_test_data.sql"
```

如果你更习惯在 MySQL 控制台里执行，也可以使用：

```sql
SOURCE D:/服务外包（学习通）/xuexitong/fuck_learning/docs/mysql建表.sql;
SOURCE D:/服务外包（学习通）/xuexitong/fuck_learning/docs/init_test_data.sql;
```

### 3. 配置后端数据库连接

后端优先读取环境变量，也支持从仓库根目录的 `config.local.py` 读取默认值。

当前后端支持的主要数据库环境变量：

```text
A12_DB_URL
A12_DB_HOST
A12_DB_PORT
A12_DB_USER
A12_DB_PASSWORD
A12_DB_NAME
A12_DB_ECHO
```

当前仓库自带的 [start-backend.ps1](/D:/服务外包（学习通）\xuexitong\fuck_learning\start-backend.ps1) 默认写的是：

```text
A12_DB_HOST=127.0.0.1
A12_DB_PORT=3306
A12_DB_USER=root
A12_DB_PASSWORD=123456
A12_DB_NAME=chaoxing_ai_course
```

如果你的 MySQL 用户名、密码、端口或数据库名不同，请先修改：

- [start-backend.ps1](/D:/服务外包（学习通）\xuexitong\fuck_learning\start-backend.ps1)
- 或者在根目录新建 `config.local.py`

### 4. 配置 LLM / 语音识别 API

如果你只想先跑通页面和基础流程，数据库准备好即可。

如果你要使用真实的：

- PPT 解析 / 脚本生成 LLM
- 学生问答 LLM
- 语音识别兜底 ASR

则还需要配置下面这些后端参数。

常用环境变量：

```text
A12_LLM_API_BASE_URL
A12_LLM_API_KEY
A12_LLM_MODEL
A12_QA_LLM_PROVIDER
A12_QA_LLM_MODEL
A12_QA_ASR_MODEL
A12_DASHSCOPE_API_KEY
A12_DASHSCOPE_BASE_URL
```

代码默认配置来源见：

- [backend/app/common/config.py](/D:/服务外包（学习通）\xuexitong\fuck_learning\backend\app\common\config.py)

说明：

- 学生问答当前默认 `qa_llm_provider` 是 `dashscope`
- 语音识别兜底依赖 `A12_DASHSCOPE_API_KEY`
- 浏览器原生语音识别可在支持的 Chromium 浏览器中直接使用，不一定强依赖后端 ASR
- 如果未配置 `A12_LLM_API_KEY`，教师端部分 LLM 能力会报错

### 5. 前端环境变量

前端默认使用：

- [.env.development](/D:/服务外包（学习通）\xuexitong\fuck_learning\.env.development)
- [.env.production](/D:/服务外包（学习通）\xuexitong\fuck_learning\.env.production)

默认值：

```text
VITE_API_BASE=
VITE_STUDENT_API_BASE=/student-api
VITE_STATIC_KEY=chaoxing-ai-static-key
```

通常本地开发不需要改这里，除非你把后端代理前缀改掉了。

## 推荐启动顺序

每次启动项目，按下面顺序来：

1. 启动 MySQL
2. 启动后端
3. 启动前端
4. 打开浏览器访问页面

## 后端如何启动

### 方式一：使用脚本启动

在 PowerShell 中执行：

```powershell
cd "D:\服务外包（学习通）\xuexitong\fuck_learning"
.\start-backend.ps1
```

这个脚本当前实际执行的是：

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 3001 --reload
```

### 方式二：手动启动

如果你不想走脚本，也可以直接执行：

```powershell
cd "D:\服务外包（学习通）\xuexitong\fuck_learning"
$env:A12_DB_HOST="127.0.0.1"
$env:A12_DB_PORT="3306"
$env:A12_DB_USER="root"
$env:A12_DB_PASSWORD="123456"
$env:A12_DB_NAME="chaoxing_ai_course"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 3001 --reload
```

### 判断后端是否启动成功

后端启动成功后，终端通常会出现：

```text
Uvicorn running on http://127.0.0.1:3001
Application startup complete.
```

还可以直接访问 Swagger：

- [http://127.0.0.1:3001/docs](http://127.0.0.1:3001/docs)

## 前端如何启动

### 方式一：使用脚本启动

在新的 PowerShell 窗口执行：

```powershell
cd "D:\服务外包（学习通）\xuexitong\fuck_learning"
.\start-frontend.ps1
```

### 方式二：手动启动

```powershell
cd "D:\服务外包（学习通）\xuexitong\fuck_learning"
npm run dev -- --host 127.0.0.1 --port 5173
```

### 判断前端是否启动成功

前端启动成功后，终端会输出本地访问地址，通常是：

- [http://127.0.0.1:5173/](http://127.0.0.1:5173/)

## 首次启动后可访问的页面

- 门户页：[http://127.0.0.1:5173/](http://127.0.0.1:5173/)
- 学生首页：[http://127.0.0.1:5173/student/home?token=student_demo_token_001](http://127.0.0.1:5173/student/home?token=student_demo_token_001)
- 教师登录页：[http://127.0.0.1:5173/teacher/login](http://127.0.0.1:5173/teacher/login)
- 后端 Swagger：[http://127.0.0.1:3001/docs](http://127.0.0.1:3001/docs)

测试 Token：

```text
教师端：test_token_001
学生端：student_demo_token_001
```

## 常见问题

### 1. PowerShell 不允许执行 `.ps1`

如果看到类似“因为在此系统上禁止运行脚本”的提示，先执行：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

然后输入 `Y` 确认。

### 2. 提示 `No module named 'backend'`

说明你不是在项目根目录启动的。先执行：

```powershell
cd "D:\服务外包（学习通）\xuexitong\fuck_learning"
```

再重新运行启动命令。

### 3. 页面提示数据库认证失败

优先检查：

- `A12_DB_USER`
- `A12_DB_PASSWORD`
- `A12_DB_NAME`

### 4. 页面提示数据库连接失败

优先检查：

- MySQL 是否启动
- 端口是否为 `3306`
- 主机是否为 `127.0.0.1`

### 5. 学生问答没有返回内容

优先检查：

- 后端是否已经启动在 `3001`
- 浏览器地址是否带有有效 `token`
- `A12_DASHSCOPE_API_KEY` 是否已配置
- 页面是否已强制刷新到最新前端代码

## 构建

```powershell
npm run build
```
