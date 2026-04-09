# 下次开始时怎么做

如果你是下一次进入这个项目的人，默认这样开始：

## 1. 先恢复上下文

依次阅读：

1. `coding-guide/progress/current-status.md`
2. `coding-guide/01-编码入口.md`
3. `coding-guide/03-联动顺序与完成定义.md`
4. `coding-guide/05-接口到代码文件映射.md`

## 2. 再确认本次任务属于哪一类

- 模块实现推进
- 具体接口改动
- 真实依赖接入
- 文档同步与整理

## 3. 如果是接口任务

再进入：

- `api/api-navigation.md`
- 对应接口文档

## 4. 写完别忘了同步文档

至少检查：

- 接口行为是否变化 -> 更新 `api/`
- 代码落位是否变化 -> 更新 `coding-guide/05`
- 阶段完成度是否变化 -> 更新 `coding-guide/progress/current-status.md`
