# fuck_learning

前端入口已统一到仓库根目录，学生端和教师端共用一套前端工程。默认先访问首页，再按角色进入对应端。

## 启动前端

在仓库根目录执行：

```bash
npm install
npm run dev
```

## 默认访问入口

- 首页：`http://localhost:5173/`

## 从首页进入学生端和教师端

- 首页中的学生端入口会跳转到：`http://localhost:5173/student/home?token=student_demo_token_001`
- 首页中的教师端入口会跳转到：`http://localhost:5173/teacher/login`

## 也可以直接访问

- 学生端：`http://localhost:5173/student/home?token=student_demo_token_001`
- 教师端：`http://localhost:5173/teacher/login`

## 后端说明

- 学生端后端仍位于 `student-ai-course/backend/student_plugin`，需要单独启动
- 教师端本地 mock 仍位于 `teacher-ai-course/mock/server.js`，执行根目录 `npm run dev` 时会一起启动
- 学生端前后端本地联调要求签名密钥一致；根目录前端默认已使用 `chaoxing-ai-static-key`，如后端自定义了 `CHAOXING_STATIC_KEY`，需要同步保持一致

学生端后端启动方式：

```bash
cd student-ai-course/backend/student_plugin
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## 构建

在仓库根目录执行：

```bash
npm run build
```
