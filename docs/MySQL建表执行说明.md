# MySQL 建表与迁移说明

## 1. 结构真源

当前项目的数据库结构以三层为准：

1. `backend/chaoxing_db/models/*.py`
   这是 ORM 结构真源，运行时 `Base.metadata.create_all()` 依赖这里。
2. `docs/mysql建表.sql`
   这是全量初始化脚本，用于新建库或重建测试库。
3. `docs/migrations/*.sql`
   这是增量迁移脚本，只用于已有旧库升级，不用于全量初始化。

## 2. 当前规则

- 新增表、新增字段、新增外键时，必须同时更新：
  - `backend/chaoxing_db/models/*.py`
  - `docs/mysql建表.sql`
- 如果这次变更需要给已有库升级，还要补一份 `docs/migrations/*.sql`
- 不要只改 ORM 或只改 SQL 初始化脚本，否则后面会出现“代码有结构、数据库没有结构”的断层

## 3. section 音频这次变更

2026-04-16 这轮 section 级音频改造已经进入全量初始化：

- `chapter_section_audio_assets`
- `lesson_sections.section_audio_asset_id`

对应增量升级脚本保留在：

- `docs/migrations/20260416_section_audio_assets.sql`

这意味着：

- 新建库：只看 `docs/mysql建表.sql`
- 已有旧库升级：执行 `docs/migrations/20260416_section_audio_assets.sql`

## 4. 新建库执行方式

推荐顺序：

1. 执行 `docs/mysql建表.sql`
2. 需要测试数据时，再执行 `docs/init_test_data.sql`

### 4.1 在 MySQL 控制台执行

```sql
SOURCE E:/CodeWarehouse/A12chaoxin/code/docs/mysql建表.sql;
SOURCE E:/CodeWarehouse/A12chaoxin/code/docs/init_test_data.sql;
```

### 4.2 先进入 MySQL，再执行

```powershell
mysql -u root -p
```

然后：

```sql
SOURCE E:/CodeWarehouse/A12chaoxin/code/docs/mysql建表.sql;
SOURCE E:/CodeWarehouse/A12chaoxin/code/docs/init_test_data.sql;
```

### 4.3 在 PowerShell 中直接执行

```powershell
cmd /c "mysql -u root -p < E:\CodeWarehouse\A12chaoxin\code\docs\mysql建表.sql"
cmd /c "mysql -u root -p < E:\CodeWarehouse\A12chaoxin\code\docs\init_test_data.sql"
```

注意：

- 不要直接在 PowerShell 里写 `mysql -u root -p < ...`
- PowerShell 对这种重定向语法处理不稳定，优先用 `cmd /c`

## 5. 已有库升级方式

已有旧库不要重新跑全量建表脚本，优先跑对应迁移脚本。

当前可用迁移：

- `docs/migrations/20260416_section_audio_assets.sql`

执行方式：

```sql
SOURCE E:/CodeWarehouse/A12chaoxin/code/docs/migrations/20260416_section_audio_assets.sql;
```

## 6. 目录职责

### `backend/chaoxing_db`

- 存放 ORM 模型
- 负责运行时建表元数据
- 这里定义的是“代码结构口径”

### `docs/mysql建表.sql`

- 负责全量初始化
- 适合新环境、测试库、重建库
- 这里定义的是“全量 SQL 口径”

### `docs/migrations`

- 负责历史库增量升级
- 一个文件对应一批结构变更
- 不替代全量初始化脚本

## 7. 维护建议

- 后续如果再引入 section 级发布、学生端消费字段扩展，先改 `backend/chaoxing_db/models`
- 然后同步 `docs/mysql建表.sql`
- 最后判断是否需要给存量库补迁移脚本
- 每次迁移完成后，最好同步 `temp/database/01-当前数据库表与字段盘点.md`
