# Teacher AI Course

## 本地开发

推荐直接运行：

```bash
npm run dev
```

该命令会同时启动：

- Vite 前端开发服务
- 本地教师端 mock 服务 `http://localhost:3001`

如果只想单独启动前端或 mock：

```bash
npm run dev:web
npm run mock
```

## 测试数据

- 登录测试 token：`test_token_001`
- 本地开发默认通过 Vite 代理把 `/api` 转发到 `http://localhost:3001`

## 说明

当前仓库只保留教师端内容。学生端独立项目位于 `D:/student-ai-course`。
