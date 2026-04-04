## 7. LLM 编排与检索策略
### 7.1 LLM 在系统中的正式职责

| 角色 | 作用 | 输入 | 输出 |
|---|---|---|---|
| 页面重点提取器 | 从页级内容提取重点 | 页面结构、标题、图表说明 | `keyPoints` |
| 节点组织器 | 把页面组织为讲授节点 | 页级内容、顺序、主题相似度 | `LessonNode` |
| 教学表达器 | 生成教师口吻讲稿 | `CIR`、风格参数 | `ScriptDraft` |
| 证据问答器 | 在约束上下文中回答问题 | 问题、节点、证据片段 | `QARecord` |
| 理解判别器 | 估计是否听懂 | 问题、答案、历史问答 | `understandingLevel` |
| 续讲生成器 | 生成补讲内容或续讲计划 | 当前节点、理解程度、依赖关系 | `ResumePlan` |

### 7.2 Prompt 分类定稿

至少保留以下六类 Prompt：

- `keypoint_extraction`
- `lesson_node_building`
- `script_generation`
- `qa_grounded_answering`
- `understanding_estimation`
- `resume_or_reinforce`

### 7.3 检索路线定稿
正式采用“结构约束 + 精确匹配 + 向量补召回 + 重排回链”的混合检索方案：

```
用户问题
-> 术语归一化 / 同义词扩展
-> currentSectionId 限域
-> page / node 双粒度候选召回
-> Full-Text / trigram 精确匹配
-> pgvector 语义补召回
-> 重排（页码、术语命中、节点距离、证据密度）
-> evidencePages / evidenceSpans 回链
-> 送入受控问答 Prompt
```

### 7.4 Guardrails 定稿

Guardrails 至少检查：

- JSON 结构是否完整；
- 回答是否含页码；
- 页码是否存在于当前 `LessonPackage`；
- 回答长度是否失控；
- 是否越权引用当前课程外内容；
- 续讲目标章节是否合法。
