# Step 16 架构梳理：Application Review + HR Reply Package + LangGraph Preview

本文档用于 Step 16.5 的项目逻辑整理，帮助后续开发、Demo 验收和面试复习。它描述当前已经实现的能力和边界，不把未实现内容写成已完成能力。

## 项目当前定位

AI Job Agent 是面向 AI 应用开发 / 大模型应用开发求职场景的 Human-in-the-loop 后端 Demo。

当前项目主要用于：

- 管理 `candidate_profile` 求职档案。
- 手动记录和更新 `applications` 投递记录。
- 分析 HR message 的 intent。
- 基于规则和候选人上下文生成 HR 回复草稿。
- 基于 JD、application 状态、job_match 和 HR intent 给出跟进建议。
- 用 LangGraph 展示一个只读 workflow preview。

它不是自动海投工具，不连接真实招聘平台，不自动发送 HR 消息，不自动确认面试时间，也不是企业级自动招聘系统。

## 当前已完成能力

- Step 1-5：建立 `candidate_profile`、`applications`、HR intent、HR reply 和 `application_id` 上下文。
- Step 6：增加 `scripts/api_smoke_test.py`，覆盖主链路验收。
- Step 7：增加规则版 `job_match`，用于求职者侧岗位优先级判断。
- Step 8：增强项目经历、技术问题、业务方案类 HR 回复草稿。
- Step 9-11.6：沉淀 Agent workflow / LangGraph 设计和可观测性文档。
- Step 12：增加 rule-based JD parsing 和岗位来源标准化。
- Step 13：增加规则版 `application_review`。
- Step 14：增加独立的 LLM enhanced application review。
- Step 15：增加 HR reply package，一次性返回 `reply_strategy_for_user` 和 `hr_reply_draft`。
- Step 16：把 `application_review` 和 HR reply package 接入 LangGraph workflow preview。

## 核心接口清单

- `GET /health`
- `POST /profile`
- `GET /profile`
- `POST /applications`
- `GET /applications`
- `GET /applications/{application_id}`
- `PATCH /applications/{application_id}`
- `POST /hr/analyze`
- `POST /hr/reply`
- `POST /job_match`
- `POST /application_review`
- `POST /application_review/llm_enhance`
- `POST /application_review/hr_reply_draft`
- `POST /agent/workflow_preview`
- `POST /agent/langgraph_workflow_preview`
- `POST /interview_availability_slots`
- `GET /interview_availability_slots`
- `PATCH /interview_availability_slots/{slot_id}`

## Step 13 / 14 / 15 / 16 的职责边界

### Step 13：application_review

`POST /application_review` 是规则版 follow-up decision baseline。

它负责：

- 读取 application。
- 复用 `job_match`。
- 结合 JD 解析字段、application status、HR intent、风险点和缺失信息。
- 返回 `review_score`、`review_level`、`confidence`、`evidence`、`recommended_action`、`risk_flags`、`missing_information`。

它不调用 LLM，不写 application，不发送消息，不改状态。

### Step 14：LLM enhanced application review

`POST /application_review/llm_enhance` 是独立的用户分析增强接口。

它负责：

- 先调用规则版 `application_review`。
- 把规则结果交给 DeepSeek-compatible LLM 做解释增强、查漏补缺、冲突提示和保守建议。
- 在没有 API key 时返回 `llm_used=false` 和 `api_key_missing`。

它不生成完整 HR 回复草稿，不写数据库，不发送消息，不改 application。

### Step 15：HR reply package

`POST /application_review/hr_reply_draft` 生成“给用户看的回复策略”和“给 HR 的回复草稿”。

它负责：

- 默认直接复用规则版 `application_review`。
- 根据 HR intent、风险、缺失信息、application 和 candidate_profile 生成 `reply_strategy_for_user`。
- 生成 `hr_reply_draft`，包含 `draft_text`、`draft_goal`、`must_confirm_before_send`、`risk_notes`、`safe_to_send`。
- 没有 API key 或 LLM 调用失败时返回 `draft_source=rule_fallback`。

它不自动发送 HR 消息，不自动投递，不自动确认面试，不自动修改 application。

### Step 16：LangGraph workflow preview

`POST /agent/langgraph_workflow_preview` 把 Step 13 和 Step 15 接入 LangGraph。

它负责：

- 读取 candidate_profile。
- 读取 application。
- 运行规则版 application review。
- 生成 HR reply package。
- 停在 `require_user_approval_node`。
- 返回 `graph_structure`、`state_snapshots`、`edge_trace` 和 `node_debug`。

它仍然是只读 preview，不自动执行真实求职动作。

## LangGraph 当前节点链路

当前节点链路：

```text
START
-> load_profile_node
-> load_application_node
-> run_application_review_node
-> generate_hr_reply_package_node
-> require_user_approval_node
-> END
```

错误分支会进入：

```text
handle_error_node -> END
```

节点职责：

- `load_profile_node`：读取 `candidate_profile`，缺失时进入错误分支。
- `load_application_node`：读取指定 application，缺失时进入错误分支。
- `run_application_review_node`：调用规则版 application review，不调用 LLM，不写 application。
- `generate_hr_reply_package_node`：生成回复策略和 HR 草稿；配置 API key 时可能调用一次 DeepSeek-compatible LLM，没有 API key 时 fallback。
- `require_user_approval_node`：设置 `approval_required=true`、`approved_by_user=false`，停止等待用户确认。

## state / node / edge / node_debug / edge_trace

- `state`：LangGraph 中贯穿节点传递的数据容器，包含 application、review、reply package、审批状态和 debug 字段。
- `node`：一个业务步骤，例如读取 application、运行 review、生成 reply package。
- `edge`：节点之间的流转关系。
- `conditional edge`：根据错误或条件决定走向，例如缺少 application 时进入 `handle_error_node`。
- `node_debug`：节点级可观测性，展示每个节点是否调用 LLM、是否读库、是否写库、是否外部调用、节点状态和草稿来源。
- `edge_trace`：本次请求实际走过的边，适合排查 workflow 为什么走到某个节点。

## 为什么 Step 15 不默认调用 Step 14

Step 14 是“给用户看的分析增强”，Step 15 是“生成回复策略和 HR 草稿”。

Step 15 默认不调用 Step 14，原因是：

- 避免一次草稿生成触发两次 LLM 调用。
- 降低成本和延迟。
- 保持 smoke test 不依赖真实 API key。
- 保持规则版 review 作为稳定 baseline。
- 让 Step 14 可以独立用于用户想看更详细分析的场景。

未来如果需要更强表达，可以让用户显式选择 LLM enhanced review，而不是默认强制调用。

## Step 16.7：项目事实边界和面试可用时间

Step 16.7 修复两个 Demo 验收中暴露的问题。

### 项目事实边界

项目介绍必须区分 RAG 企业知识库项目和 AI Job Agent 项目。

RAG 企业知识库项目可以说：

- FastAPI
- 文档入库
- txt / PDF / Excel
- Document / chunk / metadata
- FAISS + BM25 + RRF
- Reranker
- low_confidence
- SQLite 多轮会话
- React Demo

RAG 企业知识库项目不可以说：

- LangGraph
- 自动投递
- 自动发送 HR 消息
- 招聘 Agent

AI Job Agent 项目可以说：

- FastAPI
- candidate profile
- application tracking
- JD parsing
- job_match
- application_review
- LLM enhanced review
- HR reply draft
- LangGraph workflow preview
- require_user_approval_node
- node_debug / edge_trace / state_snapshots

AI Job Agent 项目不可以说：

- RAG 检索
- Embedding
- 向量数据库
- FAISS / BM25 / Reranker
- 自动投递
- 自动发送 HR 消息
- 自动确认面试
- 企业级生产系统

`project_intro` 草稿生成增加了轻量关键词校验。如果草稿出现明显混淆，例如“AI Job Agent 使用 RAG 检索”或“RAG 项目使用 LangGraph”，系统会替换为安全 fallback，并在 `debug.project_fact_boundary_fallback=true` 中记录。

### 面试可用时间 slots MVP

新增 `interview_availability_slots` 表，用于手动维护面试可用时间段。

字段包括：

- `id`
- `date`
- `start_time`
- `end_time`
- `timezone`
- `status`：`available / held / booked / expired`
- `note`
- `created_at`
- `updated_at`

当前只做后端最小闭环：

- `POST /interview_availability_slots`：创建可用时间段。
- `GET /interview_availability_slots`：查询时间段，默认只返回 `status=available`。
- `PATCH /interview_availability_slots/{slot_id}`：更新 `status` 或 `note`。

`interview_schedule` 草稿生成会读取 available slots：

- 没有 slots 时，只能回复“需要先确认日程，稍后回复”，不能虚构明天下午、后天上午等时间。
- 有 slots 时，只能提供 slots 中的时间段供 HR 参考。
- 无论是否有 slots，都不自动确认面试，不自动发送 HR 消息。

## Human-in-the-loop 安全边界

当前所有关键动作都保持 Human-in-the-loop：

- HR 回复只生成草稿，不自动发送。
- application review 只给建议，不自动改状态。
- LangGraph workflow preview 只预览节点结果，不执行真实外部动作。
- 面试时间只能建议确认，不能自动承诺。
- 薪资、到岗时间、异地、外包、驻场等敏感内容必须由用户确认。
- 候选人经历、学历、项目、薪资和工作年限不能编造。

## 当前不是企业级系统的原因

当前项目还不是企业级生产系统，主要原因：

- 没有用户体系、权限系统和多租户隔离。
- 没有生产级数据库设计、迁移策略和备份恢复。
- 没有完整 audit log / review history。
- 没有 LangGraph checkpoint / resume / interrupt 持久化。
- 没有完整 retry policy、超时控制、熔断和任务队列。
- 没有真实招聘平台接入，也没有平台合规处理。
- 没有前端工作台。
- 没有 RAG / Embedding 项目经历知识库。
- LLM 只用于可选增强和草稿生成，缺少更完整的评测、监控和安全治理。
- 当前规则仍是 demo baseline，不是完整业务策略系统。

## 后续企业级增强方向

建议后续按风险和价值逐步推进：

1. Step 17 已完成：仅在用户确认 HR 回复已处理 / 已手动发送后，更新对应 application `status / next_action / notes`；当前不是通用 approval 系统。
2. Step 18：错误处理与 retry policy，包括 LLM 调用失败、数据库异常、网络超时和 fallback 策略。
3. Step 19：checkpoint / resume / approval interrupt 设计，让 workflow 可以停在人工确认点后继续执行。
4. Step 20：review history / audit log，记录每次 review、草稿、用户确认和状态变化。
5. Later：Playwright dry-run 岗位采集，只做岗位信息采集预览，仍不自动投递。

更长期可以考虑：

- 前端工作台。
- 多用户权限和数据隔离。
- RAG 化项目经历资料。
- 更完整的 prompt / rule evaluation。
- LLM 输出安全审查。
- 生产级部署、日志、监控和告警。
