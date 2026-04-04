# GET /api/v1/scripts/{scriptId}

## 接口定位
用于查询脚本详情，供教师端编辑与预览使用。

## 规划信息
- 模块：智课生成
- 方法：GET
- 模式：查询
- 后端归属：`backend/app/script/`

## 核心路径字段
- `scriptId`：脚本 ID

## 核心响应字段
- `scriptId`：脚本 ID
- `scriptStructure`：脚本结构
- `relatedPage`：关联页码信息
- `keyPoints`：章节重点
- `requestId`：请求追踪 ID

## 对接约束
- 返回结果需支持教师端脚本预览与二次编辑。
- 应保持与生成接口输出结构兼容。
