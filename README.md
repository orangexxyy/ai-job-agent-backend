# AI Job Agent

AI Job Agent 是一个面向 AI应用开发 / 大模型应用开发求职场景的 Human-in-the-loop 后端 Demo。项目用于管理求职档案、投递记录、HR 消息、岗位匹配和回复草稿，当前主要服务于学习、求职流程管理和中文面试展示。

本项目不是自动海投工具，不自动发送 HR 消息，不连接真实招聘平台，也不做招聘决策。所有涉及投递、沟通、面试时间确认、薪资承诺和外部平台操作的动作，都必须由用户最终确认。

## 当前阶段

当前已完成到 Step 16.5：

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
- Step 14：`/application_review/llm_enhance` LLM 只读增强分析，基于规则 review 做解释和查漏补缺
- Step 15：`/application_review/hr_reply_draft` 基于 application review 生成可人工审核的 HR 回复草稿
- Step 16：`/agent/langgraph_workflow_preview` 接入 application review 和 HR reply package，并返回 `node_debug`
- Step 16.5：Docs-only，整理当前架构、Demo 验收路线、企业级差距和后续路线图

当前核心能力仍以规则版 baseline、LangGraph workflow preview、只读 LLM enhance 和可人工审核的 HR reply draft 为主；相关 LLM 接口在配置 API key 后会调用 DeepSeek-compatible LLM。当前不实现 RAG、Embedding、Playwright 或前端；不连接真实招聘平台，不自动投递，不自动发送 HR 消息，不自动确认面试时间，不自动修改 application status。

## Current architecture summary

当前项目采用 FastAPI route / Pydantic schema / service / SQLite 的轻量分层。主链路围绕 `candidate_profile` 和 `applications` 展开：先用规则版 `job_match` 和 `application_review` 形成可解释 baseline，再用 Step 15 生成 `reply_strategy_for_user` 和 `hr_reply_draft`，最后通过 Step 16 的 LangGraph workflow preview 串联 `run_application_review_node`、`generate_hr_reply_package_node` 和 `require_user_approval_node`。

更完整的架构梳理见 [Step 16 Architecture Review](docs/architecture_review_step16.md)。

## Current limitations

当前项目是求职展示级 Human-in-the-loop Demo，不是企业级自动招聘系统。它还没有生产级权限系统、多租户隔离、review history / audit log、LangGraph checkpoint / resume / approval interrupt、完整 retry policy、前端工作台、RAG / Embedding、Playwright 岗位采集或真实招聘平台接入。所有外发消息、投递、面试时间确认和状态变更都必须由用户人工确认。

## 技术栈

- Python
- FastAPI
- Pydantic
- SQLite
- python-dotenv
- requests
- DeepSeek-compatible config placeholder

项目中保留 DeepSeek-compatible 配置。当前 `/application_review/llm_enhance` 和 `/application_review/hr_reply_draft` 会在配置 `DEEPSEEK_API_KEY` 后尝试调用 DeepSeek-compatible Chat Completions；没有 API key 时会返回 `llm_used=false` / `api_key_missing` 或 `draft_source=rule_fallback`。`/agent/langgraph_workflow_preview` 在生成 HR reply package 时会复用 Step 15 的同一套 fallback 机制。

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
- `POST /application_review/llm_enhance`：在规则 review 基础上调用 DeepSeek-compatible LLM 做只读解释增强
- `POST /application_review/hr_reply_draft`：基于 application review / LLM enhance 生成可人工审核的 HR 回复草稿
- `POST /agent/workflow_preview`：普通 Python 版只读 workflow preview
- `POST /agent/langgraph_workflow_preview`：LangGraph StateGraph 版只读 workflow preview，串联 application review、HR reply package、Human-in-the-loop 审批节点，并返回可观测性字段

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

### application_review LLM enhance

`POST /application_review/llm_enhance` 是 Step 14 新增的 LLM 只读增强接口。它先调用规则版 `application_review`，再把 `review_score`、`review_level`、`confidence`、`evidence`、`risk_flags`、`missing_information` 和 `llm_ready_context` 交给 DeepSeek-compatible Chat Completions 做自然语言解释、规则结果检查、冲突提示和保守下一步建议。

它不是自动投递、自动发送、自动确认面试或招聘决策系统。没有 `DEEPSEEK_API_KEY` 时，接口不会崩溃，会返回 `llm_used=false` 和 `api_key_missing`，同时保留规则版 `rule_review`。

### application_review HR reply draft

`POST /application_review/hr_reply_draft` 是 Step 15 新增的 HR 回复草稿接口。它默认不调用 Step 14 的 `/application_review/llm_enhance`，而是直接基于规则版 `application_review`、HR intent、原始 HR message、application 和 candidate_profile 一次性生成“给用户看的回复策略”和“给 HR 的回复草稿”，避免一次草稿生成触发两次 LLM 调用。

返回内容包括 `reply_strategy_for_user`、`hr_reply_draft`、`draft_source`、`draft_type`、`draft_text`、`draft_goal`、`must_confirm_before_send`、`risk_notes`、`safe_to_send` 和 `human_review_required`。没有 API key 或 LLM 调用失败时会返回 `draft_source=rule_fallback` 的保守草稿。

这个接口不会发送消息，不会自动投递，不会自动确认面试，不会自动修改 application `status / next_action / risk_flags`。`safe_to_send=true` 也只表示内容风险较低，不代表可以自动发送。

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
- [Step 16 Architecture Review](docs/architecture_review_step16.md)
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

- Step 17：用户确认后的状态更新 workflow，只有用户确认后才更新 application status / next_action。
- Step 18：错误处理与 retry policy。
- Step 19：checkpoint / resume / approval interrupt 设计。
- Step 20：review history / audit log。
- Later：Playwright dry-run 岗位采集，必须人工确认，且不做自动投递。

当前只有 `/application_review/llm_enhance`、`/application_review/hr_reply_draft` 以及复用 HR reply package 的 LangGraph preview 可能在配置 API key 后调用 DeepSeek-compatible LLM；没有 API key 时会保留规则结果并 fallback。当前不做 RAG / Embedding，不做 Playwright，不连接真实招聘平台，不自动投递，不自动发送 HR 消息。

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

## Step 14: LLM enhanced application review

Step 14 新增 `POST /application_review/llm_enhance`，用于在规则版 `application_review` 基础上做只读 LLM 增强分析：
- 规则 review 仍然是 baseline，不是最终事实
- LLM 只做解释增强、查漏补缺、冲突提示和保守下一步建议
- 没有 API key 时返回 `llm_used=false` / `api_key_missing`
- 不生成完整 HR 回复草稿
- 不自动发送消息，不自动投递，不自动确认面试，不自动修改 application `status`

LLM prompt 明确要求区分原始事实、规则推断和 LLM 建议；不得编造 JD、HR 消息、候选人经历、薪资、面试时间或公司信息。即使未来 LLM 返回增强分析，最终动作仍然需要用户确认。

## Step 15: LLM HR reply draft

Step 15 新增 `POST /application_review/hr_reply_draft`，用于基于 Step 13 的规则 review 结果生成回复策略和 HR 回复草稿：
- `confirm_details`：确认外包、驻场、合同主体、薪资范围、工作地点、工作方式和岗位职责等信息
- `project_intro`：基于真实项目上下文回答项目经历问题
- `interview_schedule`：只表达可进一步沟通，不能自动确认具体面试时间
- `salary_expectation`：保守沟通薪资期望，不承诺最终薪资
- `polite_decline`：礼貌婉拒
- `general_follow_up`：默认跟进

Step 15 refinement 后，该接口默认不再调用 Step 14，`debug.step14_llm_enhance_called=false`，避免重复 LLM 调用。Step 14 仍然保留为独立的用户分析增强接口。Step 15 只生成草稿，不发送消息，不自动投递，不自动确认面试，不自动修改 application 状态。没有 API key 或 LLM 调用失败时，会返回 `rule_fallback` 草稿。

## Step 16: LangGraph application review + HR reply package

Step 16 增强 `POST /agent/langgraph_workflow_preview`，把 Step 13 的 `application_review` 和 Step 15 的 `hr_reply_draft` 接入 LangGraph preview：

- `run_application_review_node`：调用规则版 `review_application(update_application=False)`，生成只读跟进建议、`confidence`、`evidence`、风险点和缺失信息。
- `generate_hr_reply_package_node`：在存在 `hr_message` 时生成 `reply_strategy_for_user` 和 `hr_reply_draft`，并复用已经生成的规则 review，避免重复分析。
- `require_user_approval_node`：继续作为 Human-in-the-loop 停止点，返回 `approval_required=true` 和 `approved_by_user=false`。
- `node_debug`：按节点展示是否调用 LLM、是否读库、是否写库、是否外部调用、节点状态和草稿来源。

Step 14 `/application_review/llm_enhance` 仍保留为独立分析增强接口，不被强制并入 LangGraph。Step 16 的 LangGraph preview 可能在 HR reply package 节点通过 Step 15 调用一次 DeepSeek-compatible LLM；没有 API key 或调用失败时会返回 `rule_fallback`，smoke test 不依赖真实 API key。

该 workflow 仍然是只读预览：不自动发送 HR 消息，不自动投递，不自动确认面试，不自动修改 application `status / next_action / risk_flags / last_hr_message`，不实现 RAG / Embedding / Playwright，也不连接真实招聘平台。
