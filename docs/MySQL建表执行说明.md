# MySQL 建表执行说明

脚本文件：

- [mysql建表.sql](/D:/服务外包（学习通）/xuexitong/fuck_learning/docs/mysql建表.sql)
- [init_test_data.sql](/D:/服务外包（学习通）/xuexitong/fuck_learning/docs/init_test_data.sql)

## 结构范围

当前脚本覆盖：

- 平台、学校、用户、课程、班级、课程成员
- 教师端章节树、章节 PPT、LLM 解析、讲稿、音频、章节练习
- 学生端 lesson、unit、section、page、anchor、knowledge point
- 页级阅读进度、章节进度、课程总进度、续学记录
- 练习作答、掌握度留痕、AI 问答、通知、接口日志

## 执行方式

在 MySQL 8 环境下执行：

```bash
mysql -u root -p < docs/mysql建表.sql
mysql -u root -p < docs/init_test_data.sql
```

如果已经进入 MySQL 控制台，也可以执行：

```sql
SOURCE D:/服务外包（学习通）/xuexitong/fuck_learning/docs/mysql建表.sql;
SOURCE D:/服务外包（学习通）/xuexitong/fuck_learning/docs/init_test_data.sql;
```

## 注意事项

- 脚本会重建 `chaoxing_ai_course` 库下的业务表，不会删除数据库本身
- 脚本默认使用 `utf8mb4` 和 `InnoDB`
- `init_test_data.sql` 已包含教师端测试 PPT 资源：`第九章 压杆稳定_20260401213017.ppt`
- 双端 FastAPI 共用的 SQLAlchemy ORM 目录：`backend-common/chaoxing_db`
- 掌握度与学习进度的计算公式建议继续放在后端服务层维护
