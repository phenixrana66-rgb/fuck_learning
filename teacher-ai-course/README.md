# Teacher AI Course

教师端前端已迁移到仓库根目录统一维护。

当前目录保留内容：

- `mock/server.js` 教师端本地 mock 服务

## 首次启动教师端后端

```bash
cd ..
npm install
node teacher-ai-course/mock/server.js
```

## 后续再次启动教师端后端

```bash
node mock/server.js
```

默认端口：

- `3001`

## 与学生端一起联调

如果你要同时启动双端后端：

1. 在一个终端启动学生端 FastAPI
2. 在另一个终端启动教师端 mock

教师端 mock 启动命令：

```bash
node teacher-ai-course/mock/server.js
```

如果教师端之前已经启动过，后续再次运行不需要重新 `npm install`。

## 前端联调注意

如果教师端 mock 已经手动启动，前端请在仓库根目录执行：

```bash
npm run dev:web
```

不要执行 `npm run dev`，因为该命令会再次自动启动教师端 mock。
