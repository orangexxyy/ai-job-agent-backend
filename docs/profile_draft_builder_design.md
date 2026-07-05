# Candidate Profile Draft Builder Design

## 目标

Step 27B 将 `docs/input/current_resume.txt` 转换为兼容 `CandidateProfileInput` 的私有 JSON 草稿。它解决的是“让用户审核结构化事实”，不是自动更新 Agent 的正式画像。

## 事实链

```text
resume_source 原始文件
-> Step 27A current_resume.txt
-> Step 27B candidate_profile_draft.json
-> 用户人工审核
-> 后续手动写入 candidate_profile
-> Agent Workflow 正式事实源
```

Agent Workflow 不直接读取 DOCX、`resume_source` 或 `current_resume.txt`，避免运行时事实来源漂移。

## 规则提取

- 学历：本科、大专、专科、硕士、研究生、博士。
- 专业：优先读取 `专业：xxx` / `专业为 xxx`，再按“数据科学与大数据技术”→“大数据技术应用”→“大数据技术”的完整度匹配，最后才匹配 `xxx专业`。所有结果必须真实出现在 `current_resume.txt`；只有短词“大数据技术”时报告会要求用户确认完整名称。
- 求职方向：AI 应用开发、大模型应用开发、Python 后端 + AI、RAG / Agent。
- 技术栈：FastAPI、RAG、FAISS、BM25、Reranker、LangChain、LangGraph、SQLite、React 等。
- 项目：企业知识库 RAG、AI Job Agent、医药 RAG、Coze / 飞书旅游 Workflow。

脚本不会因为 JD 或技术关键词就把能力写成已实现项目；项目名必须满足对应的组合信号，最终仍需用户审核。

## 默认偏好

薪资数字、城市、外包、驻场、加班、异地和出差偏好没有明确事实时不会猜测。草稿使用“需要用户确认”的保守文本，并保留 Human-in-the-loop 边界。

## 安全边界

- 输出位于被 `.gitignore` 保护的 `docs/input/generated/`。
- 不调用 `/profile`，不写 SQLite。
- 不调用 LLM 或外部 API。
- 不修改正式 `candidate_profile`。
- 草稿必须经用户确认后才能用于后续手动同步。

## Step 27C：应用草稿

`scripts/apply_profile_draft.py` 默认只做 dry-run，展示目标岗位、项目、truth boundaries、文本预览和偏好字段，不写数据库。只有传入 `--apply` 并输入精确的 `YES` 后，才会：

1. 读取当前正式 `candidate_profile`。
2. 在私有 `profile_backups/` 下创建 JSON 备份。
3. 复用 `save_candidate_profile()` 写入经过 `CandidateProfileInput` 校验的草稿。
4. 使用 `get_candidate_profile()` 读回并比较所有输入字段。
5. 仅在读回验证成功后写入一条 `profile_apply_history` 最小操作留痕。

正式应用只支持在交互终端运行 `--apply`，并由用户手动输入精确的 `YES`。脚本不提供非交互确认参数，自动化脚本或 Coding Agent 不能绕过该确认。应用脚本禁用 dotenv 自动读取，不调用 LLM、外部 API 或 `/profile`。这不是自动简历更新生产流程。

## Step 28A：Profile Apply History

`profile_apply_history` 与 application 维度的 `application_action_history` 分离。它只记录 `draft_path`、`backup_path`、用户确认、写入验证结果和创建时间；`detail_json` 采用固定白名单，仅包含 target roles、available projects、truth boundaries 的数量，以及 `resume_text` / `project_context` 的字符长度。

dry-run、未输入 `YES`、保存失败或读回验证失败都不会写 history。`external_action_performed=true` 会被 service 拒绝。该能力是本地 Demo 的简单操作留痕，不保存完整简历正文，不提供版本回滚、多用户权限或生产级 audit log。
