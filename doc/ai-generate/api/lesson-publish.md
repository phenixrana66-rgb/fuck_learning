# POST /api/v1/lesson/publish

## 接口定位
用于冻结 CIR、脚本、音频版本并生成正式 `LessonPackage`。

## 规划信息
- 模块：智课生成
- 方法：POST
- 模式：当前代码为同步发布式 demo，长期目标仍为异步任务模式
- 后端归属：`backend/app/lesson/`、`backend/app/tasks/`

## 核心请求字段
- `coursewareId`：课件 ID
- `scriptId`：脚本 ID
- `audioId`：音频资源 ID
- `publishOptions`：发布选项
- `enc`：签名信息或会话鉴权信息

## 核心响应字段
- `lessonId`：正式智课 ID
- `publishStatus`：发布状态
- `lessonPackageRef`：播放包引用
- `requestId`：请求追踪 ID

## 当前代码行为（截至本次实现）
- 当前 `publish` 会校验 `coursewareId / scriptId / audioId` 是否属于同一条 demo 链；
- `coursewareId` 必须与 `parse` 结果中的 `cir.coursewareId` 一致；
- `audioId` 必须来自当前 `scriptId` 生成的音频；
- 发布成功后会冻结一个最小快照，包含 `nodeSequence`、`scriptRefs`、`audioRefs`；
- 当前快照仍保存在进程内 `_LESSON_PACKAGES`，重启服务后会丢失；
- 当前发布结果会直接返回 `publishStatus=published`，以满足完整 demo 链展示需要。

## 对接约束
- 必须支持异步任务模式。
- 发布时需形成稳定快照，明确区分发布态与运行态。
- 当前 happy path 要求 `coursewareId` 使用 parse 完成结果中的 `cir.coursewareId`。
