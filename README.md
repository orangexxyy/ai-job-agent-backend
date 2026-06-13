# AI Job Agent

AI Job Agent 是一个面向 AI应用开发 / 大模型应用开发求职场景的 Human-in-the-loop 后端 Demo。项目用于管理求职档案、投递记录、HR 消息、岗位匹配和回复草稿，当前主要服务于学习、求职流程管理和中文面试展示。

本项目不是自动海投工具，不自动发送 HR 消息，不连接真实招聘平台，也不做招聘决策。所有涉及投递、沟通、面试时间确认、薪资承诺和外部平台操作的动作，都必须由用户最终确认。

## 当前阶段

当前已完成到 Step 13：

- Step 1：`candidate_profile` 求职档案保存与读取
- Step 2：`/hr/analyze` 规则版 HR Intent Analyzer
- Step 3：`/hr/reply` 基于 `candidate_profile` 的 HR 回复草稿
- Step 4：`/applications` 投递记录管理
- Step 5：`/hr/reply` 支持可选 `application_id` 上下文
- Step 6：API smoke test harness
- Step 7：`/job_match` 规则版岗位匹配评分
- Step 8：`/hr/reply` 基于 `resume_text` / `project_context` 增强项目类回复草稿
- Step 9：Agent Workflow Design / 面试展示文档收口
- Step 10：`/agent/workflow_preview` 普通 Python rule-based workflow preview
- Step 11：`/agent/langgraph_workflow_preview` 最小 LangGraph StateGraph workflow preview
- Step 11.5：LangGraph workflow 可观测性增强，返回 `graph_structure`、`state_snapshots`、`edge_trace`
- Step 11.6：Docs-only，沉淀 Workflow / LangGraph 阶段总结
- Step 12：JD 手动导入增强 / 岗位来源标准化 / rule-based JD parsing
- Step 13：Application review / follow-up decision layer，基于 application、JD 解析字段、job_match 和 HR intent 给出只读跟进建议

当前核心能力仍以规则版 baseline 和最小 LangGraph preview 为主，不调用 DeepSeek / LLM，不实现 RAG、Embedding、Playwright 或前端；不连接真实招聘平台，不自动投递，不自动发送 HR 消息，不自动确认面试时间，不自动修改 application status。

## 技术栈

- Python
- FastAPI
- Pydantic
- SQLite
- python-dotenv
- requests
- DeepSeek-compatible config placeholder

项目中保留 DeepSeek-compatible 配置占位，用于后续扩展。当前接口不会真实调用 DeepSeek / LLM。

## 启动方式

安装依赖：

```bash
pip install -r requirements.txt
```

建议使用 `8001` 端口，避免和其他 RAG 项目的 `8000` 端口冲突：

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

访问 Swagger：

```text
http://127.0.0.1:8001/docs
```

## 接口说明

当前可用接口：

- `GET /health`：健康检查
- `POST /profile`：保存或更新 `candidate_profile`
- `GET /profile`：读取 `candidate_profile`
- `POST /hr/analyze`：分析 HR 消息 intent
- `POST /hr/reply`：生成 HR 回复草稿，可选绑定 `application_id`
- `POST /applications`：创建投递记录
- `GET /applications`：查询投递记录列表
- `GET /applications/{application_id}`：读取单条投递记录
- `PATCH /applications/{application_id}`：更新投递记录
- `/applications` 创建/更新会基于本地规则生成 `source_type`、`jd_summary`、`jd_keywords`、`jd_required_skills`、`jd_years_requirement`、`jd_location_requirement`、`jd_remote_type`
- `POST /job_match`：基于规则分析某条 application 的岗位匹配度
- `POST /application_review`：基于 application、JD 解析字段、job_match 和 HR intent 生成只读跟进建议
- `POST /agent/workflow_preview`：普通 Python 版只读 workflow preview
- `POST /agent/langgraph_workflow_preview`：LangGraph StateGraph 版只读 workflow preview，包含可观测性字段

## 核心模块

### applications

`applications` 模块用于手动记录和更新求职投递过程中的关键信息，包括公司、岗位、JD、来源、状态、HR 最新消息和下一步动作。

当前只支持手动记录和更新，不做自动投递，不连接真实招聘平台，不抓取岗位，也不会自动联系 HR。

### job_match

`POST /job_match` 是规则版岗位匹配评分接口，用于从求职者侧辅助判断某条 application 是否值得优先跟进。它不是招聘决策系统，不代表招聘方是否录用候选人。

评分维度包括：

- `role_fit`
- `tech_stack_fit`
- `project_relevance`
- `preference_fit`

当 `update_application=true` 时，只会安全回写：

- `applications.match_score`
- `applications.next_action`
- `applications.risk_flags`

它不会修改 `status`，不会修改 `last_hr_message`，不会自动投递，不会自动发送 HR 消息，也不会调用 DeepSeek / LLM。

### application_review

`POST /application_review` 是 Step 13 新增的 rule-based follow-up decision baseline。它不会重新做一套 job_match，而是在现有 `job_match` 分数基础上，结合 application 状态、JD 解析字段、HR intent、风险点和缺失信息，生成下一步跟进建议。

返回内容包括：
- `review_score`
- `review_level`
- `confidence`
- `recommended_action`
- `evidence`
- `risk_flags`
- `missing_information`
- `suggested_next_message_type`
- `decision_factors`
- `llm_ready_context`

当前该接口保持只读：不调用 DeepSeek / LLM，不做 RAG / Embedding，不使用 Playwright，不连接真实招聘平台，不自动投递，不自动发送 HR 消息，不自动确认面试，也不自动修改 application `status`。

`confidence` 表示规则证据充分程度，不是大模型概率。`evidence` 用于解释规则判断，例如来自 `job_match`、`jd_keywords`、`hr_message`、`risk_flags` 或 `application_status` 的证据；同时也会进入 `llm_ready_context.evidence_summary`，为未来可选的 LLM enhanced review 提供结构化上下文。未来 LLM 只能参考这些规则结果，不能把规则推断当作事实，最终仍然需要 Human-in-the-loop。

### `/hr/reply` 与 `application_id`

旧版请求不传 `application_id` 仍然可用。传入 `application_id` 时，系统会读取对应投递记录，优先使用 application 的 `company_name` 和 `job_title` 作为上下文，并返回 `application_context`。

生成回复草稿后，系统只会安全更新：

- `last_hr_message`
- `next_action`

不会自动修改 `status`，不会自动确认面试时间，也不会发送消息。

### `/hr/reply` 与 profile context 增强

当 HR 消息命中 `project_experience`、`technical_question` 或 `business_proposal` 时，`/hr/reply` 会尝试从 `candidate_profile.resume_text`、`candidate_profile.project_context` 和 `candidate_profile.available_projects` 中选择少量相关片段，用来生成更具体但保守的回复草稿。

这不是 RAG，不做 Embedding，不做向量检索，也不调用 DeepSeek / LLM。当前只是本地关键词匹配和短片段选择，最多返回 3 条 `selected_context_snippets`。

返回数据包含：

- `context_used`
- `selected_context_snippets`
- `context_reply_mode`

如果没有可用上下文，接口会返回保守 fallback，提示补充 `resume_text / project_context`，不会编造项目经历。

## API Smoke Test Harness

`scripts/api_smoke_test.py` 是本地接口验收脚本，用于快速检查当前主链路 API 是否可用。它是开发验收工具，不是业务功能。

运行方式：

```bash
python scripts/api_smoke_test.py
```

也可以指定地址：

```bash
python scripts/api_smoke_test.py --base-url http://127.0.0.1:8001
```

脚本会临时写入测试 `candidate_profile`，并在结束时尽量恢复原 profile。脚本会创建一条 `HARNESS Demo Company <timestamp>` application 测试记录，并在收尾阶段尽量标记为 `closed`。

## 项目文档入口

- [Agent Workflow Design](docs/agent_workflow_design.md)
- [Interview Talking Points](docs/interview_talking_points.md)
- [Demo Script](docs/demo_script.md)
- [Workflow / LangGraph Summary](docs/workflow_langgraph_summary.md)
- [Project Structure](docs/project_structure.md)
- [Code Reading Guide](docs/code_reading_guide.md)

Step 9 只做文档收口，没有修改业务代码，也没有实现 LangGraph / RAG / Playwright。

## 代码结构与阅读指南

- [Project Structure](docs/project_structure.md)
- [Code Reading Guide](docs/code_reading_guide.md)

这两份文档用于说明 route / schema / service / database 的分层职责、典型调用链，以及未来 workflow / LangGraph 为什么应该优先复用 service 函数，而不是在后端内部再调用自己的 HTTP API。

## 明确边界

当前未实现：

- 自动投递
- 自动发送 HR 消息
- 真实招聘平台接入
- Playwright
- RAG
- Embedding / 向量检索
- 前端
- 真实 LLM 调用
- 生产级权限系统
- 完整多轮聊天
- conversations / messages 持久化
- 招聘决策系统

项目不会编造候选人的工作经历、教育经历、地址、工作年限、薪资、项目历史或其他履历信息。任何涉及真实外部沟通和求职承诺的内容，都必须保持 Human-in-the-loop。

## Roadmap

- Step 14：可选的人工确认后状态更新 workflow，只有用户确认后才更新 application status / next_action。
- Step 15：可选 LLM parser / RAG project context，仅在明确需要时再做。
- Later：Playwright dry-run 岗位采集，必须人工确认，且不做自动投递。

当前仍不调用 DeepSeek / LLM，不做 RAG / Embedding，不做 Playwright，不连接真实招聘平台，不自动投递，不自动发送 HR 消息。

## Step 10: rule-based workflow_preview

Step 10 新增 `POST /agent/workflow_preview`，用于把已有 service 能力串成一个只读预览流程：

- 读取 `candidate_profile`
- 读取指定 `application`
- 复用 `analyze_job_match(update_application=False)`
- 可选分析 HR message
- 可选复用 `generate_hr_reply(update_application=False)`
- 返回 `workflow_steps`、`state_summary`、`job_match`、`hr_intent`、`hr_reply` 和 Human-in-the-loop 审批状态

这个接口是规则版 workflow preview，不是 LangGraph 实现。它不调用 DeepSeek / LLM，不实现 RAG，不使用 Playwright，不连接真实招聘平台，不自动投递，不自动发送 HR 消息，不自动确认面试时间，也不写入 application。

接口：

- `POST /agent/workflow_preview`

示例请求：

```json
{
  "application_id": 1,
  "hr_message": "方便介绍一下你做过的 RAG 或 Agent 项目吗？"
}
```
## Step 11: minimal LangGraph Workflow Demo

Step 11 新增 `POST /agent/langgraph_workflow_preview`，用于用 LangGraph `StateGraph` 表达 Step 10 的同一条 workflow preview。

它和 `POST /agent/workflow_preview` 并行保留，便于面试展示：

- `POST /agent/workflow_preview`：普通 Python rule-based workflow baseline
- `POST /agent/langgraph_workflow_preview`：LangGraph StateGraph workflow preview

LangGraph 版本会返回：

- `workflow_mode = "langgraph_preview"`
- `workflow_engine = "langgraph_stategraph"`
- `workflow_steps`
- `state_summary`
- `job_match`
- `hr_intent`
- `hr_reply`
- `approval_required = true`
- `approved_by_user = false`

当前只是最小 LangGraph demo，不调用 DeepSeek / LLM，不实现 RAG，不使用 Playwright，不连接真实招聘平台，不自动投递，不自动发送 HR 消息，不自动确认面试时间，也不写入 application。

示例请求：

```json
{
  "application_id": 1,
  "hr_message": "方便介绍一下你做过的 RAG 或 Agent 项目吗？"
}
```
## Step 11.5: LangGraph observability

`POST /agent/langgraph_workflow_preview` 已增强可观测性，返回中额外暴露：

- `graph_structure`：展示 LangGraph nodes、普通 edges、conditional edges
- `state_snapshots`：展示每个关键 node 执行后的轻量 state 变化
- `edge_trace`：展示本次 workflow 实际走过的边和条件判断结果

这些字段用于学习 LangGraph 编排、Swagger 调试和面试展示。当前仍然不调用 DeepSeek / LLM，不实现 RAG，不使用 Playwright，不连接真实招聘平台，不自动投递，不自动发送 HR 消息，不自动确认面试时间，也不写入 application。
## Workflow / LangGraph 阶段总结

- [Workflow / LangGraph 阶段总结](docs/workflow_langgraph_summary.md)：用于复习 Step 10、Step 11、Step 11.5，说明普通 Python workflow、LangGraph workflow、可观测性字段、Human-in-the-loop 边界和未实现能力。

## Step 12: rule-based JD parsing

Step 12 增强了手动 application / JD 录入质量：

- `source` / `job_source` 会标准化为 `source_type`
- `jd_text` 会通过本地规则生成 `jd_summary`
- 返回 `jd_keywords`、`jd_required_skills`、`jd_years_requirement`、`jd_location_requirement`、`jd_remote_type`
- 创建或更新 application 时，如果传入新的 `jd_text`，会重新解析这些字段

这是本地规则 baseline，不调用 DeepSeek / LLM，不做 RAG / Embedding，不抓取岗位，不连接真实招聘平台，不自动投递，也不自动发送 HR 消息。

## Step 13: rule-based application review

Step 13 新增 `POST /application_review`，用于生成 application 的只读跟进建议：
- 复用 `analyze_job_match(update_application=False)`
- 可选复用 `analyze_hr_message`
- 结合 `source_type`、`jd_keywords`、`jd_required_skills`、`jd_remote_type`、`status`、`risk_flags` 和缺失信息
- 返回 `review_score`、`review_level`、`recommended_action`、`suggested_next_message_type` 和 `decision_factors`
- 返回 `confidence` 和 `evidence`，用于说明规则证据是否充分以及结论由哪些信号支撑

它是 Human-in-the-loop 的 follow-up decision baseline，不是招聘决策系统。当前不调用 DeepSeek / LLM，不做 RAG / Embedding，不使用 Playwright，不连接真实招聘平台，不自动投递，不自动发送 HR 消息，也不自动修改 application `status`。
