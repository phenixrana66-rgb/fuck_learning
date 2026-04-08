# MySQL 建表执行说明

建表脚本文件：

- [mysql建表.sql](/D:/服务外包（学习通）/xuexitong/fuck_learning/docs/mysql建表.sql)

## 结构范围

这份脚本覆盖了当前师生双端需要的核心业务表，包括：

- 平台、学校、用户、课程、班级、课程成员
- 教师端章节树、章节 PPT、LLM 解析、讲稿、音频
- 学生端智课、知识单元、章节、章节页、锚点、知识点
- 学生页级阅读进度、章节进度、总进度、续学记录
- 教师章节练习、学生作答、章节掌握度留痕
- AI 问答会话、消息、结构化回答、语音转写
- 通知与接口日志


## 执行方式

在 MySQL 8 环境下执行：

```bash
mysql -u root -p < docs/mysql建表.sql
```

如果已经先进入 MySQL 控制台，也可以执行：

```sql
SOURCE D:/服务外包（学习通）/xuexitong/fuck_learning/docs/mysql建表.sql;
```

## 注意事项

- 脚本会重建 `chaoxing_ai_course` 库下的业务表，不会删除数据库本身。
- 脚本默认使用 `utf8mb4` 和 `InnoDB`。
- 脚本里没有写触发器、存储过程和掌握度计算公式，具体计算逻辑建议放在后端服务层。
