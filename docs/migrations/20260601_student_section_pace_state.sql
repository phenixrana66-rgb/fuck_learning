-- 学生章节内动态调速状态字段

ALTER TABLE `student_section_progress`
  ADD COLUMN `pace_mode` VARCHAR(32) DEFAULT NULL COMMENT '当前章节调速模式：supplement/reinforce',
  ADD COLUMN `pace_reason_summary` VARCHAR(255) DEFAULT NULL COMMENT '规则映射后的调速原因摘要',
  ADD COLUMN `pace_trigger_source` VARCHAR(32) DEFAULT NULL COMMENT '最近一次触发来源：qa/practice',
  ADD COLUMN `pace_updated_at` DATETIME DEFAULT NULL COMMENT '最近一次调速更新时间';
