# Student AI Course

一个面向学习通场景的学生端 AI 智课演示项目，包含 Vite 前端页面和 Flask Mock 后端，便于本地联调免登、课件同步、实时问答与续讲流程。

## 项目结构

- `src/`：学生端前端页面与交互逻辑
- `backend/student_plugin/`：本地适配层与 Mock 数据
- `docs/`：调试说明与联调文档

## 前端启动

```bash
cd D:/student-ai-course
npm install
npm run dev
```

## 后端启动

```bash
cd D:/student-ai-course/backend/student_plugin
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## 本地访问入口

```text
http://localhost:5173/student/home?token=student_demo_token_001
```

## 联调说明

- 前端默认通过 `/student-api` 访问本地适配层。
- 后端默认监听 `http://localhost:5000`。
- 本地调试时默认开启 Mock 模式，无需真实超星环境即可体验完整流程。
