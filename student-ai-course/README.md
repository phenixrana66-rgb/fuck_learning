# Student AI Course

学生端前端已迁移到仓库根目录统一维护。

当前目录保留内容：

- `backend/student_plugin/` 学生端后端适配层
- `docs/` 学生端联调说明

统一前端请在仓库根目录执行：

```bash
npm install
npm run dev:web
```

## 学生端后端启动方式

首次运行：

```bash
cd backend/student_plugin
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

后续再次运行：

```bash
cd backend/student_plugin
.venv\Scripts\activate
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

如果依赖更新过，再补一次：

```bash
cd backend/student_plugin
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

如果需要和教师端一起联调，请在仓库根目录另开一个终端执行：

```bash
node teacher-ai-course/mock/server.js
```
