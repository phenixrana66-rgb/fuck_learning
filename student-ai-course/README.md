# Student AI Course

学生端前端已迁移到仓库根目录统一维护。

当前目录保留内容：

- `backend/student_plugin/` 学生端后端适配层
- `docs/` 学生端联调说明

统一前端请在仓库根目录执行：

```bash
npm install
npm run dev
```

学生端后端仍在当前目录启动：

```bash
cd backend/student_plugin
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
