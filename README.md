# fuck_learning

前端入口已统一到仓库根目录，学生端和教师端共用一套前端工程。默认先访问首页，再按角色进入对应端。

## 启动前准备

先在仓库根目录安装前端依赖：

```bash
npm install
```

如果要启动学生端后端，首次运行还需要安装 Python 依赖：

```bash
cd student-ai-course/backend/student_plugin
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 双端后端如何启动

建议开两个终端，分别启动学生端后端和教师端后端。

### 第 1 步：启动学生端后端

如果是首次运行：

```bash
cd student-ai-course/backend/student_plugin
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

如果之前已经成功运行过，后续再次启动只需要：

```bash
cd student-ai-course/backend/student_plugin
.venv\Scripts\activate
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

如果你更新过 `requirements.txt`，再次启动前先补一次依赖：

```bash
cd student-ai-course/backend/student_plugin
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

说明：

- 学生端后端使用 FastAPI
- 默认端口是 `5000`
- 前端学生端请求会通过 `/student-api` 代理到这里
- 停止服务时按 `Ctrl + C`

### 第 2 步：启动教师端后端

如果是首次运行：

```bash
cd D:\服务外包（学习通）\xuexitong\fuck_learning
npm install
node teacher-ai-course/mock/server.js
```

如果之前已经成功运行过，后续再次启动只需要：

```bash
cd D:\服务外包（学习通）\xuexitong\fuck_learning
node teacher-ai-course/mock/server.js
```

说明：

- 教师端后端当前是本地 Node mock
- 默认端口是 `3001`
- 前端教师端请求会走 `/api` 到这个服务
- 停止服务时按 `Ctrl + C`

### 第 3 步：如果还要联调前端

在第三个终端执行：

```bash
npm run dev:web
```

这里要使用 `npm run dev:web`，不要使用 `npm run dev`。

原因：

- `npm run dev` 会同时启动 Vite 和教师端 mock
- 你如果已经手动启动了教师端后端，再执行 `npm run dev` 会导致 `3001` 端口重复占用

## 默认访问入口

- 首页：`http://localhost:5173/`
- 学生端：`http://localhost:5173/student/home?token=student_demo_token_001`
- 教师端：`http://localhost:5173/teacher/login`

## 后端说明

- 学生端后端位于 `student-ai-course/backend/student_plugin`
- 教师端后端位于 `teacher-ai-course/mock/server.js`
- 学生端前后端本地联调要求签名密钥一致；根目录前端默认已使用 `chaoxing-ai-static-key`，如后端自定义了 `CHAOXING_STATIC_KEY`，需要同步保持一致

## 构建

在仓库根目录执行：

```bash
npm run build
```
