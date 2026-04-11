# MySQL 建表执行说明

当前仓库已经统一为：

- 学生端 FastAPI
- 教师端 FastAPI
- 一套共享 MySQL 主库
- 一套共享 SQLAlchemy ORM

## 脚本文件

- [mysql建表.sql](/D:/服务外包（学习通）/xuexitong/fuck_learning/docs/mysql建表.sql)
- [init_test_data.sql](/D:/服务外包（学习通）/xuexitong/fuck_learning/docs/init_test_data.sql)

## 数据范围

当前脚本覆盖：

- 平台、学校、用户、课程、教学班、课程成员
- 教师端章节树、章节 PPT、LLM 解析、讲稿、音频、章节练习
- 学生端 lesson、unit、section、page、anchor、knowledge point
- 页级阅读进度、章节进度、课程总进度、续学记录
- 练习作答、掌握度留痕、AI 问答、通知、接口日志

## 执行方式

### 方式一：在系统终端执行

#### PowerShell 推荐写法

先进入 MySQL：

```powershell
mysql -u root -p
```

再执行：

```sql
SOURCE D:/服务外包（学习通）/xuexitong/fuck_learning/docs/mysql建表.sql;
SOURCE D:/服务外包（学习通）/xuexitong/fuck_learning/docs/init_test_data.sql;
```

如果希望继续在 PowerShell 中直接执行命令，可以改为：

```powershell
cmd /c "mysql -u root -p < docs\mysql建表.sql"
cmd /c "mysql -u root -p < docs\init_test_data.sql"
```

不要直接在 PowerShell 里执行下面这种带 `<` 的命令：

```powershell
mysql -u root -p < docs/mysql建表.sql
```

因为 PowerShell 不支持这里的 `<` 重定向写法。

### 方式二：在 MySQL 控制台执行

```sql
SOURCE D:/服务外包（学习通）/xuexitong/fuck_learning/docs/mysql建表.sql;
SOURCE D:/服务外包（学习通）/xuexitong/fuck_learning/docs/init_test_data.sql;
```

## 当前测试资源

`init_test_data.sql` 已包含教师端测试 PPT 资源登记：

- `第九章 压杆稳定_20260401213017.ppt`

该测试资源会出现在这些链路中：

- `chapter_ppt_assets`
- `chapter_parse_tasks`
- `chapter_parse_results`
- `chapter_knowledge_nodes`
- `chapter_scripts`
- `chapter_audio_assets`
- `lessons / lesson_units / lesson_sections / lesson_section_pages`

## 当前学习进度与掌握度口径

### 学习进度

- 学生只要读到某一页，该页就算完成
- 章节学习进度 = `round(已读页数 / 总页数 * 100)`
- 课程总进度 = `round(所有章节学习进度平均值)`

### 掌握度

- 章节掌握度只保留两类来源：
  - 学习进度贡献 `40%`
  - 章节练习贡献 `60%`
- 章节掌握度 = `round(章节学习进度 * 0.4 + 章节练习得分率 * 0.6)`
- AI 问答理解度当前只保留记录和推荐用途，不参与正式掌握度计算

## 共享 ORM

双端共用的 SQLAlchemy ORM 目录：

```powershell
backend-common/chaoxing_db
```

学生端和教师端都通过这套模型访问同一套 MySQL 主库。

## 注意事项

- 脚本默认使用 `utf8mb4` 和 `InnoDB`
- 业务库名为 `chaoxing_ai_course`
- 建议先执行 `mysql建表.sql`，再执行 `init_test_data.sql`
- 如果你已经有旧测试库，建议先确认是否需要备份再重跑脚本
