# Migrations 说明

这个目录只放“已有数据库的增量升级脚本”。

## 使用规则

- 新建库或重建库：执行 `docs/mysql建表.sql`
- 已有旧库升级：执行本目录下对应迁移脚本
- 迁移脚本不会替代全量初始化脚本

## 当前迁移

### `20260416_section_audio_assets.sql`

用途：

- 新增 `chapter_section_audio_assets`
- 给 `lesson_sections` 增加 `section_audio_asset_id`
- 补 section 级音频与发布快照之间的关联

适用场景：

- 旧库原本只有 `chapter_audio_assets`
- 现在需要升级到 section 级音频模型

## 维护要求

每次新增结构变更时：

1. 先更新 `backend/chaoxing_db/models/*.py`
2. 再更新 `docs/mysql建表.sql`
3. 如果要兼容已有旧库，再补一份本目录迁移脚本
