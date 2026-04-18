# fuck_learning

超星 AI 互动课程项目，当前仓库是一个前后端合并后的单仓工程：

- 前端：Vite + Vue 3 + Element Plus
- 后端：FastAPI
- 数据库：MySQL
- 向量库：PostgreSQL + pgvector（用于学生问答检索，可选）
- 主要场景：教师端课件解析/脚本生成/音频生成，学生端课程学习、进度追踪、AI 问答、语音输入

## 项目结构

### 根目录

- `src/`：前端源码
- `public/`：前端静态资源
- `backend/`：FastAPI 后端
- `docs/`：数据库脚本、迁移说明、问答检索相关 SQL
- `examples/`：示例资源与本地静态挂载目录
- `dist/`：前端构建产物
- `start-frontend.ps1`：前端启动脚本
- `start-backend.ps1`：后端启动脚本
- `config.example.py`：本地配置示例
- `config.local.py`：本地配置覆盖文件

### 前端页面

位于 `src/views/`：

- `HomePortal.vue`：门户页
- `student/Home.vue`：学生首页
- `student/Player.vue`：学生课程播放页
- `student/KnowledgeLearning.vue`：学生章节学习页
- `teacher/Login.vue`：教师登录页
- `teacher/LessonManage.vue`：课程管理
- `teacher/CourseParse.vue`：课件解析
- `teacher/ScriptGenerate.vue`：脚本生成
- `teacher/ScriptEdit.vue`：脚本编辑
- `teacher/AudioGenerate.vue`：音频生成

### 后端模块

位于 `backend/app/`：

- `common/`：配置、数据库、异常、通用响应、安全
- `compat/`：兼容层接口
- `lesson/`：课程与音频缓存逻辑
- `parser/`：课件解析
- `script/`：脚本生成与存储
- `progress/`：学习进度相关接口
- `qa/`：问答接口
- `student_runtime/`：学生端运行时、RAG、流式问答、语音识别
- `teacher_runtime/`：教师端扩展运行时

## 技术栈

### 前端

- Vue 3
- Vue Router
- Element Plus
- Axios
- CryptoJS
- Vite

### 后端

- FastAPI
- Uvicorn
- SQLAlchemy
- Pydantic
- Alembic
- PyMySQL
- psycopg / pgvector
- httpx
- python-pptx
- PyMuPDF
- openpyxl

## 环境要求

- Node.js 18+
- npm 9+
- Python 3.11+
- MySQL 8.x
- PostgreSQL 14+（如果要启用向量检索）

## 安装依赖

在仓库根目录执行：

```powershell
cd "D:\服务外包（学习通）\xuexitong\fuck_learning"
npm install
pip install -r requirements.txt
```

如果使用 Python 虚拟环境，先激活虚拟环境再安装后端依赖。

## 前端配置

前端环境变量文件：

- `.env.development`
- `.env.production`

当前默认配置：

```text
VITE_API_BASE=
VITE_STUDENT_API_BASE=/student-api
VITE_STATIC_KEY=chaoxing-ai-static-key
```

本地开发时，Vite 代理会将：

- `/api` 转发到 `http://127.0.0.1:3001`
- `/student-api` 转发到 `http://127.0.0.1:3001`

对应配置位于 [vite.config.js](/D:/服务外包（学习通）/xuexitong/fuck_learning/vite.config.js)。

## 后端配置

后端主配置位于：

- [backend/app/common/config.py](/D:/服务外包（学习通）/xuexitong/fuck_learning/backend/app/common/config.py)

本地覆盖配置位于：

- [config.local.py](/D:/服务外包（学习通）/xuexitong/fuck_learning/config.local.py)
- [config.example.py](/D:/服务外包（学习通）/xuexitong/fuck_learning/config.example.py)

后端支持两类配置来源：

1. 环境变量 `A12_*`
2. 根目录 `config.local.py`

常用数据库配置：

```text
A12_DB_URL
A12_DB_HOST
A12_DB_PORT
A12_DB_USER
A12_DB_PASSWORD
A12_DB_NAME
A12_DB_ECHO
```

常用模型配置：

```text
A12_LLM_API_BASE_URL
A12_LLM_API_KEY
A12_LLM_MODEL
A12_QA_LLM_PROVIDER
A12_QA_LLM_MODEL
A12_QA_EMBEDDING_MODEL
A12_QA_EMBEDDING_DIMENSIONS
A12_QA_ASR_MODEL
A12_DASHSCOPE_API_KEY
A12_DASHSCOPE_BASE_URL
A12_VECTOR_DB_URL
```

本地 `config.local.py` 里还包含以下附加字段：

- 火山引擎 TTS 配置：`APPID`、`ACCESS_TOKEN`、`TTS_URL`、`TTS_CLUSTER`、`TTS_VOICE_TYPE`
- 火山引擎 ASR 配置：`ASR_URL`、`ASR_CLUSTER`
- DashScope 问答 / 向量 / ASR 配置

## 数据库初始化

### MySQL

建库：

```sql
CREATE DATABASE chaoxing_ai_course DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```

导入脚本：

```powershell
mysql -u root -p chaoxing_ai_course < "D:\服务外包（学习通）\xuexitong\fuck_learning\docs\mysql建表.sql"
mysql -u root -p chaoxing_ai_course < "D:\服务外包（学习通）\xuexitong\fuck_learning\docs\init_test_data.sql"
```

相关文件：

- [docs/mysql建表.sql](/D:/服务外包（学习通）/xuexitong/fuck_learning/docs/mysql建表.sql)
- [docs/init_test_data.sql](/D:/服务外包（学习通）/xuexitong/fuck_learning/docs/init_test_data.sql)
- [docs/MySQL建表执行说明.md](/D:/服务外包（学习通）/xuexitong/fuck_learning/docs/MySQL建表执行说明.md)

### PostgreSQL + pgvector（可选）

如果启用学生问答向量检索，还需要单独准备向量库，并执行：

- [docs/postgresql_pgvector.sql](/D:/服务外包（学习通）/xuexitong/fuck_learning/docs/postgresql_pgvector.sql)

用于 MySQL 问答检索表的辅助 SQL：

- [docs/mysql_qa_retrieval.sql](/D:/服务外包（学习通）/xuexitong/fuck_learning/docs/mysql_qa_retrieval.sql)

## 默认端口

- 前端：`5173`
- 后端：`3001`

## 启动方式

推荐顺序：

1. 启动 MySQL
2. 启动 PostgreSQL（如果启用向量库）
3. 启动后端
4. 启动前端

### 启动后端

脚本方式：

```powershell
cd "D:\服务外包（学习通）\xuexitong\fuck_learning"
.\start-backend.ps1
```

当前脚本内容等价于：

```powershell
$env:A12_DB_HOST = "127.0.0.1"
$env:A12_DB_PORT = "3306"
$env:A12_DB_USER = "root"
$env:A12_DB_PASSWORD = "123456"
$env:A12_DB_NAME = "chaoxing_ai_course"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 3001 --reload
```

### 启动前端

脚本方式：

```powershell
cd "D:\服务外包（学习通）\xuexitong\fuck_learning"
.\start-frontend.ps1
```

当前脚本内容等价于：

```powershell
npm run dev:web
```

也就是：

```powershell
npm run dev
```

### 手动启动

后端：

```powershell
cd "D:\服务外包（学习通）\xuexitong\fuck_learning"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 3001 --reload
```

前端：

```powershell
cd "D:\服务外包（学习通）\xuexitong\fuck_learning"
npm run dev -- --host 127.0.0.1 --port 5173
```

## 访问入口

### 页面

- 门户页：`http://127.0.0.1:5173/`
- 学生首页：`http://127.0.0.1:5173/student/home?token=student_demo_token_001`
- 学生课程页：`/student/player/:lessonId`
- 学生章节学习页：`/student/knowledge-learning/:lessonId/:sectionId?`
- 教师登录页：`http://127.0.0.1:5173/teacher/login`

### 后端

- Swagger：`http://127.0.0.1:3001/docs`

## 路由说明

前端路由定义位于 [src/router/index.js](/D:/服务外包（学习通）/xuexitong/fuck_learning/src/router/index.js)。

教师端除登录页外，会检查平台 token：

- URL 查询参数里的 `token`
- 或 `sessionStorage` 中保存的 token

## 主要接口入口

后端入口位于 [backend/app/main.py](/D:/服务外包（学习通）/xuexitong/fuck_learning/backend/app/main.py)。

当前挂载的主要路由：

- `compat_router`，前缀 `settings.api_prefix`
- `qa_router`，前缀 `settings.api_prefix`
- `progress_router`，前缀 `settings.api_prefix`
- `student_router`，前缀 `/student-api`

静态挂载：

- `/mock-remote/examples`
- `/cache/voice`

## 开发常用命令

安装依赖：

```powershell
npm install
pip install -r requirements.txt
```

启动前端：

```powershell
npm run dev
```

启动后端：

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 3001 --reload
```

构建前端：

```powershell
npm run build
```

## 测试与辅助资源

- `backend/tests/`：后端测试
- `rest-client/`：接口调试资源
- `output/`：输出目录
- `logs/`：运行日志
- `doc/`、`docs/`：说明文档与脚本

## 常见问题

### PowerShell 无法执行 `.ps1`

执行：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 前端访问不到后端

检查：

- 后端是否已启动在 `127.0.0.1:3001`
- `vite.config.js` 代理是否被修改
- 浏览器是否命中了旧缓存

### 数据库连接失败

检查：

- MySQL 是否已启动
- `A12_DB_*` 是否正确
- `config.local.py` 是否覆盖了预期配置

### 学生问答不可用

检查：

- `A12_DASHSCOPE_API_KEY` 是否已配置
- 向量库是否已初始化
- 相关检索表是否已导入

## 备注

当前仓库里仍保留了一些历史目录和辅助资源，例如：

- `teacher-ai-course/`
- `student-ai-course/`
- `backend-common/`

实际本地运行时，当前主入口仍是根目录前端工程和 `backend.app.main:app`。
