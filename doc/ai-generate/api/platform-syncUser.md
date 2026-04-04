# POST /api/v1/platform/syncUser

## 接口定位
用于同步教师或学生信息，并返回内部身份映射结果。

## 规划信息
- 模块：平台
- 方法：POST
- 模式：同步
- 后端归属：`backend/app/platform/`

## 核心请求字段
- `platformId`：外部平台 ID
- `userInfo`：用户信息对象
- `enc`：签名信息

## 核心响应字段
- `internalUserId`：系统内部用户 ID
- `syncStatus`：同步状态
- `authToken`：身份验证令牌或平台透传令牌
- `requestId`：请求追踪 ID

## 对接约束
- 使用 `/api/v1` 前缀。
- 请求与响应统一使用 UTF-8 JSON。
- 平台请求必须校验 `enc` 签名。
- 教师、学生、平台管理员按 `RBAC` 控制权限。
