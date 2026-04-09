# API 规划阅读导航

本文件用于快速定位 `doc/ai-generate/api/` 目录下的接口规划文件，便于按业务链路和模块分组阅读，减少一次性逐个翻找文件的成本。

## 先读什么

如果你的目标是“继续写代码”，建议不要直接从单接口文档开始，而是先读：

- [../coding-guide/01-编码入口.md](../coding-guide/01-编码入口.md)
- [../coding-guide/02-后端模块与实现映射.md](../coding-guide/02-后端模块与实现映射.md)
- [../coding-guide/05-接口到代码文件映射.md](../coding-guide/05-接口到代码文件映射.md)

`coding-guide/` 负责告诉你这次改动属于哪个模块、哪个阶段、应该先补什么；`api/` 再负责告诉你单接口应该长什么样。

## 文档目录

- [platform-syncCourse.md](./platform-syncCourse.md) - 平台课程同步接口
- [platform-syncUser.md](./platform-syncUser.md) - 平台用户同步接口
- [lesson-parse-post.md](./lesson-parse-post.md) - 课件解析任务提交接口
- [lesson-parse-get-by-parseId.md](./lesson-parse-get-by-parseId.md) - 课件解析状态与结果查询接口
- [lesson-generateScript.md](./lesson-generateScript.md) - 结构化讲稿生成接口
- [scripts-get-by-scriptId.md](./scripts-get-by-scriptId.md) - 脚本详情查询接口
- [scripts-put-by-scriptId.md](./scripts-put-by-scriptId.md) - 教师编辑稿保存接口
- [lesson-generateAudio.md](./lesson-generateAudio.md) - 音频生成任务提交接口
- [lesson-publish.md](./lesson-publish.md) - LessonPackage 发布接口
- [lesson-play.md](./lesson-play.md) - 学生端播放装配接口
- [qa-voiceToText.md](./qa-voiceToText.md) - 语音转文字接口
- [qa-interact.md](./qa-interact.md) - 证据约束问答接口
- [qa-session-get-by-sessionId.md](./qa-session-get-by-sessionId.md) - 多轮问答会话查询接口
- [progress-track.md](./progress-track.md) - 学习进度记录接口
- [progress-adjust.md](./progress-adjust.md) - 续讲与节奏调整接口

## 推荐阅读顺序

### 平台对接先读
- [../coding-guide/02-后端模块与实现映射.md](../coding-guide/02-后端模块与实现映射.md)
- [platform-syncCourse.md](./platform-syncCourse.md)
- [platform-syncUser.md](./platform-syncUser.md)

### 智课生成主链路
- [../coding-guide/03-联动顺序与完成定义.md](../coding-guide/03-联动顺序与完成定义.md)
- [lesson-parse-post.md](./lesson-parse-post.md)
- [lesson-parse-get-by-parseId.md](./lesson-parse-get-by-parseId.md)
- [lesson-generateScript.md](./lesson-generateScript.md)
- [scripts-get-by-scriptId.md](./scripts-get-by-scriptId.md)
- [scripts-put-by-scriptId.md](./scripts-put-by-scriptId.md)
- [lesson-generateAudio.md](./lesson-generateAudio.md)
- [lesson-publish.md](./lesson-publish.md)
- [lesson-play.md](./lesson-play.md)

### 问答链路
- [../coding-guide/03-联动顺序与完成定义.md](../coding-guide/03-联动顺序与完成定义.md)
- [qa-voiceToText.md](./qa-voiceToText.md)
- [qa-interact.md](./qa-interact.md)
- [qa-session-get-by-sessionId.md](./qa-session-get-by-sessionId.md)

### 进度与续讲链路
- [../coding-guide/03-联动顺序与完成定义.md](../coding-guide/03-联动顺序与完成定义.md)
- [progress-track.md](./progress-track.md)
- [progress-adjust.md](./progress-adjust.md)

## 范围说明

- 本目录只覆盖接口规划文件本身。
- 如果你是为了日常编码而阅读接口文档，优先先看 [../coding-guide/04-阅读导航.md](../coding-guide/04-阅读导航.md)。
- 如果要查看系统分层、模块边界和正式架构约束，请转到 [../project-architecture/14-阅读导航.md](../project-architecture/14-阅读导航.md)。
- 如果要查看后端、异步任务、数据库、AI 接入与部署技术栈，请转到 [../tech-stack-selection/16-阅读导航.md](../tech-stack-selection/16-阅读导航.md)。
