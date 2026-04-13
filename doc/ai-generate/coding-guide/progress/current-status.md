# 当前进度

本文件用于记录**当前代码与文档的最新有效状态**，供下一次继续开发时快速恢复上下文。

## 一、当前文档体系状态

目前 `doc/ai-generate/` 下已经形成五层：

- `requirements-analysis/`：需求与验收边界
- `project-architecture/`：系统结构、对象、状态、模块边界
- `tech-stack-selection/`：技术栈、运行时、存储、部署与测试基线
- `coding-guide/`：日常编码入口、模块映射、联动顺序、接口到代码定位
- `api/`：逐接口契约文档

## 二、当前 coding-guide 已有内容

- `01-编码入口.md`：平时编码默认入口
- `02-后端模块与实现映射.md`：模块职责与后续实现目标
- `03-联动顺序与完成定义.md`：阶段顺序与 DoD
- `05-接口到代码文件映射.md`：接口文档到后端代码文件定位
- `06-编码流程与文档持久化规范.md`：先读什么、改完同步什么
- `07-数据库持久化演进规划.md`：从内存态到 MySQL / Redis / MinIO 的落地边界与阶段顺序

补充状态：

- 已完成一次 `temp/zrt` 协作文档与我方文档的数据库设计比对
- `project-architecture/05-核心数据模型设计.md` 已补入“逻辑对象 -> 首批物理表”的开发参考映射
- `coding-guide/07-数据库持久化演进规划.md` 已补入“当前可直接用于开发的最小表清单、关键回链字段、关键约束与索引”

## 三、当前仓库实际运行结构（2026-04 更新）

当前仓库的真实运行口径已经收敛为：

- 一个根目录 Vue / Vite 前端：`src/`
- 一个统一 FastAPI 后端入口：`backend/app/main.py`
- 一套共享 MySQL 主库：`chaoxing_ai_course`
- 一套共享 ORM：`backend/chaoxing_db`

### 1. 前端现状

- 当前只有一个根目录前端应用，入口是 `src/main.js`
- 路由在 `src/router/index.js`，同一 SPA 同时承载学生端与教师端页面
- Vite 代理在 `vite.config.js` 中统一配置为：
  - `/api -> http://127.0.0.1:3001`
  - `/student-api -> http://127.0.0.1:3001`

### 2. 后端现状

当前唯一真实后端入口是 `backend/app/main.py`，当前实际挂载：

- `compat_router`
- `qa_router`
- `progress_router`
- `student_router`（前缀 `/student-api`）

这意味着当前仓库已经不再以“学生后端 + 教师后端分别作为正式主入口”的方式运行。

### 3. 教师端链路现状

- 教师前端仍走兼容接口前缀 `/api/v1/*`
- 当前主要由 `backend/app/compat/router.py` 负责兼容分流
- 兼容层会把教师旧 payload 分派到 `backend/app/teacher_runtime/services.py`
- 因此教师链路当前实际形态是：`compat/router -> teacher_runtime/services`

### 4. 学生端链路现状

- 学生端统一挂到 `backend/app/student_runtime/router.py`
- 对外接口前缀保持 `/student-api/*`
- 当前内部形态不是纯数据库化，而是：
  - `adapter.py` 提供兼容 mock / 内存底座
  - `db_learning_service.py`、`db_qa_service.py` 提供数据库增强

### 5. 兼容入口与遗留目录

学生、教师遗留 plugin 包装入口如仍存在，也已不是主运行时，只是待清理的兼容壳。

当前真实运行应始终以 `backend.app.main:app` 为准。

仍需要留意的遗留项：

- 学生端与教师端旧目录已经删除，仓库只保留根目录统一后端
- 旧 Node mock 已不属于当前默认运行时范围

## 四、当前统一后端迁移进度判断

基于本次全仓读取，可以把当前进度概括为：

### 已完成的统一化

- 前端已经统一到根目录单一 Vite 工程
- 后端已经统一到 `backend.app.main`
- 学生 `/student-api/*` 与教师 `/api/v1/*` 两套路由已被单一后端承接
- `backend/chaoxing_db` 已作为共享 ORM / 数据层接入统一后端
- `task_records` 与 `script_records` 已形成真实数据库主记录落点

### 已完成但仍带兼容性质的部分

- 教师端仍依赖 `compat/router.py` 承接旧接口语义
- 学生端仍保留 `adapter.py` 作为 mock / 内存底座
- 学生、教师旧 backend 目录即使保留，也只应视为待删除兼容壳

### 尚未完全收口的部分

- `common/security.py` 在部分主链路中仍可见 placeholder 校验口径
- `lesson / qa / progress` 并未全部完成统一、彻底的数据库化
- 解析链虽然已接任务主记录，但完整对象存储、真正异步基础设施仍未全接入

## 五、默认下一步优先级

如果后续继续推进，而不是仅做文档同步，建议优先级改为：

1. 以前端真实页面联调为主，确认教师端 `/api/v1/*` 与学生端 `/student-api/*` 在统一后端下完全可用
2. 继续收口学生端 `adapter.py` 的 mock 兜底，让数据库结果逐步成为单一事实源
3. 继续收口教师端兼容层，把 `compat/router.py` 中仍然偏旧接口语义的分流逐步压缩
4. 再考虑补齐 `lesson / qa / progress` 的持久化与异步化

### 当前接手要点

- 运行入口以 `backend.app.main:app` 为准
- 学生接口前缀保持 `/student-api`
- 教师接口前缀保持 `/api`
- 根目录 `README.md` 应作为统一后端的主启动说明
- `doc/ai-generate/` 下的其他文档若仍按旧的模块拆分理解仓库，应优先以代码与根 README 为准

## 六、如果下次继续开发，先读什么

下次继续时，默认按这个顺序恢复上下文：

1. 先读 [../01-编码入口.md](../01-编码入口.md)
2. 再读 [../03-联动顺序与完成定义.md](../03-联动顺序与完成定义.md)
3. 再读 [../05-接口到代码文件映射.md](../05-接口到代码文件映射.md)
4. 如果是解析链，先看 `backend/app/parser/` 与 `rest-client/lesson-parse.http`
5. 最后根据任务跳到 `../api/` 对应接口文档

## 七、维护要求

每次出现以下情况，都要更新本文件：

- 当前阶段完成度变化
- 新增真实依赖接入
- 当前优先级变化
- 日常编码入口或恢复顺序变化

本轮额外说明：

- `temp/zrt/docs/字段级数据库设计说明书.md` 与 `temp/zrt/docs/mysql建表.sql` 当前可作为数据库落库时的外部字段级参考
- 但仓库内正式基线仍以 `doc/ai-generate/` 为准；只有已经吸收到我方文档的内容，才视为后续开发默认方案
