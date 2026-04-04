# PUT /api/v1/scripts/{scriptId}

## 接口定位
用于保存教师编辑后的正式脚本版本。

## 规划信息
- 模块：智课生成
- 方法：PUT
- 模式：保存
- 后端归属：`backend/app/script/`

## 核心路径字段
- `scriptId`：脚本 ID

## 核心请求字段
- `scriptStructure`：编辑后的脚本结构
- `versionRemark`：版本说明（可选）
- `enc`：签名信息或会话鉴权信息

## 核心响应字段
- `scriptId`：脚本 ID
- `version`：脚本版本号
- `savedAt`：保存时间
- `requestId`：请求追踪 ID

## 对接约束
- 必须支持教师编辑后保存。
- 应保留脚本版本化能力，与发布态对象关联。
