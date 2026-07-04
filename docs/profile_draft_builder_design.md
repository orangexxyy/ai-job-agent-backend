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
