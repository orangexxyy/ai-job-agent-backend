# Code Reading Guide

这份文档面向第一次阅读本项目的学习者，帮助你按顺序理解 FastAPI route / schema / service / database 的分层，以及未来 workflow / LangGraph 应该如何复用 service。

## 推荐阅读顺序

建议按下面顺序阅读：

0. `docs/api_surface_guide.md`：先区分当前主流程、Legacy 和 Debug / Preview API，避免从旧接口开始理解项目。
0. `docs/mainline_acceptance_report.md`：查看当前主线哪些环节已通过、哪一项仍有 LLM 措辞稳定性风险。
0. `docs/demo_3_minute_pitch.md`：在理解代码后，用三分钟版本复习项目定位、流程、设计和安全边界。

## Step 19A: Automation Policy 阅读顺序

1. `docs/automation_policy_design.md`
2. `app/schemas/automation_policy_schema.py`
3. `app/services/automation_policy_service.py`
4. `app/routes/automation_policy_routes.py`
5. `scripts/api_smoke_test.py`

重点确认 evaluator 不写数据库、不调用 LLM，所有外部动作均为 false。

## Step 20: Agent Loop Simulation 阅读顺序

1. `docs/agent_loop_simulation_design.md`
2. `app/schemas/agent_loop_schema.py`
3. `app/services/agent_loop_service.py`
4. `app/routes/agent_loop_routes.py`
5. `scripts/api_smoke_test.py`

## Step 18A: Action History 阅读顺序

1. `docs/action_history_design.md`：先理解轻量追踪目标、隐私控制和非完整审计边界。
2. `app/models.py` 与 `app/database.py`：查看 history 表和初始化逻辑。
3. `app/schemas/action_history_schema.py`：查看只读响应结构。
4. `app/services/action_history_service.py`：查看写入与按 application 查询。
5. `application_service.py`、`interview_availability_service.py`：查看三个动作的接入位置。
6. `application_routes.py`：查看只读查询接口。
7. `scripts/api_smoke_test.py`：查看写入、去重、外部动作 false 和查询只读验收。

## Step 28A: Profile Apply History 阅读顺序

1. `docs/profile_draft_builder_design.md`：先理解私有草稿、人工确认和最小留痕边界。
2. `app/models.py` 与 `app/database.py`：查看独立 history 表和幂等初始化。
3. `app/schemas/profile_apply_history_schema.py`：查看不包含简历正文的记录结构。
4. `app/services/profile_apply_history_service.py`：确认 detail 白名单、确认/验证条件和外部动作拒绝。
5. `scripts/apply_profile_draft.py`：查看 history 只在保存并读回验证成功后写入。
6. `scripts/test_profile_apply_history.py`：查看临时数据库下的 dry-run、取消、成功和隐私边界验收。

阅读重点：这不是 application action history，不新增 API，也不是完整 profile 版本管理或生产级 audit log。

## Step 29A: Profile Draft Review 阅读顺序

1. `docs/profile_draft_builder_design.md`：理解本地审核、摘要输出和二次确认边界。
2. `app/schemas/profile_draft_schema.py`：确认 POST 只接收 `confirmation_text`，response 不含完整正文。
3. `app/services/profile_draft_service.py`：查看 CLI / API 共享的 load、backup、save、verify 和 history 流程。
4. `app/routes/profile_draft_routes.py`：查看默认路径固定、拒绝 query 参数并限制 loopback client 的本地 Review API。
5. `scripts/apply_profile_draft.py`：确认 CLI 仍要求交互终端和手动 `YES`。
6. `frontend_demo/index.html`：查看结构化展示和双重确认。
7. `scripts/test_profile_draft_review.py`：查看临时文件与 SQLite 下的 API、隐私和写入条件验收。

阅读重点：前端不能提交完整 profile 或文件路径；GET 缺失时返回 `draft_exists=false` 且保持只读，POST 仅在精确确认后应用默认 draft。

## Step 30A: Candidate Preference Form 阅读顺序

1. `app/schemas/profile_schema.py`：确认 Step 30A 复用现有字段，不新增数据库结构。
2. `frontend_demo/index.html`：查看 GET 最新 profile、白名单合并、事实源保护和保存后验证。
3. `app/services/automation_policy_service.py`：回看薪资底线、外包、驻场和工作制风险识别。
4. `app/services/auto_reply_service.py`：查看敏感 intent 如何优先读取明确偏好并生成保守候选。
5. `app/services/reply_send_gate_service.py`：确认 preference candidate 仍停在人工确认且不写 simulated-send history。
6. `scripts/api_smoke_test.py`：查看空偏好、拒绝、具体确认、自己回答和 Final Gate 边界矩阵。
7. `scripts/agent_workflow_demo.py`：查看前端 Demo 使用的明确偏好 fixture。

阅读重点：Step 30A 不是完整 profile 编辑器；偏好是敏感回复候选的事实源之一，不是自动发送授权。

1. `README.md`
2. `docs/project_structure.md`
3. `app/main.py`
4. `app/routes/profile_routes.py`
5. `app/services/profile_service.py`
6. `app/schemas/profile_schema.py`
7. `app/routes/application_routes.py`
8. `app/services/application_service.py`
9. `app/routes/hr_routes.py`
10. `app/services/hr_intent_service.py`
11. `app/services/hr_reply_service.py`
12. `app/services/context_reply_service.py`
13. `app/routes/job_match_routes.py`
14. `app/services/job_match_service.py`
15. `scripts/api_smoke_test.py`
16. `docs/agent_workflow_design.md`

## 如何看一个接口

以 `/profile` 为例：

1. 先看 route：`app/routes/profile_routes.py`  
   理解 URL、HTTP method、request schema、response schema。

2. 再看 schema：`app/schemas/profile_schema.py`  
   理解请求体和响应体有哪些字段。

3. 再看 service：`app/services/profile_service.py`  
   理解真正的数据保存和读取逻辑。

4. 再看数据库字段：`app/models.py`  
   理解 SQLite 表结构。

5. 最后用 Swagger 或 smoke test 验证  
   Swagger 看接口形状，`scripts/api_smoke_test.py` 看主链路是否能跑通。

## 如何看一个业务流程

以 `/hr/reply` 为例：

```text
接收 HR message
-> analyze intent
-> load candidate_profile
-> 可选 load application
-> 可选选择 project_context snippets
-> 生成 reply_draft
-> truth boundary 检查
-> 可选更新 application
-> 返回 response
```

阅读时可以按这个顺序看：

1. `app/routes/hr_routes.py`
2. `app/schemas/hr_schema.py`
3. `app/services/hr_reply_service.py`
4. `app/services/hr_intent_service.py`
5. `app/services/profile_service.py`
6. `app/services/context_reply_service.py`
7. `app/services/truth_boundary_service.py`
8. `app/services/application_service.py`

## 常见困惑解释

### 为什么 `GET /profile` 和 `get_candidate_profile()` 都存在

`GET /profile` 是 HTTP API，给 Swagger、前端、测试脚本或外部调用方使用。  
`get_candidate_profile()` 是内部 service 函数，给后端代码、workflow、未来 LangGraph node 使用。

### 为什么 workflow 不直接调 HTTP 接口

后端内部 workflow 直接调用 service 更简单、稳定、可测试。  
如果内部再 HTTP 调自己，会依赖端口、服务启动状态和网络调用，还可能造成循环调用。

### 为什么 schemas 里只有字段，没有业务逻辑

schemas 的职责是定义数据结构，例如 request / response 的字段和类型。  
业务判断应该放在 service 层，这样 route、workflow、测试都能复用。

### 为什么 routes 不应该写太多业务逻辑

routes 是 HTTP 入口，应该尽量薄。  
如果业务逻辑写在 routes 里，未来 LangGraph node 或其他内部流程就难以复用。

### 为什么 service 是最值得重点看的地方

service 层包含真正的业务规则，例如保存 profile、更新 application、分析 intent、生成 reply draft、计算 job_match。  
未来 Agent workflow 也应该优先复用 service 函数。

### 为什么 smoke test 是外部 HTTP 调用，而 workflow 是内部函数调用

smoke test 模拟外部用户或测试脚本，目的是验证 FastAPI 接口主链路。  
workflow 是后端内部编排，应该复用 service 函数，避免额外 HTTP 开销。

## 面试表达

这个项目采用 FastAPI 常见分层方式：routes 负责 HTTP，schemas 负责数据结构，services 负责业务逻辑，database/models 负责存储。未来接 LangGraph 时，会把 service 函数作为 node 能力复用，而不是让图内部再调用 HTTP 接口。这样可以保持业务逻辑集中、可测试、可复用，也更容易加入 Human-in-the-loop 审批节点。

## 阅读建议

- 先理解 `candidate_profile`，再看 `applications`。
- 先看规则版 `hr_analyze`，再看 `hr_reply`。
- 理解 `application_id` 上下文后，再看 `job_match`。
- 最后看 `agent_workflow_design.md`，理解为什么这些 service 可以被未来 workflow 编排。
- 阅读 service 时优先看 public function 的中文 docstring；技术名词会保留英文，重点关注输入、输出、副作用和 Human-in-the-loop 边界。
## Step 10 阅读补充：workflow_preview

阅读 `POST /agent/workflow_preview` 时，建议顺序：

1. `app/routes/agent_routes.py`
2. `app/schemas/agent_schema.py`
3. `app/services/workflow_service.py`
4. `app/services/job_match_service.py`
5. `app/services/hr_reply_service.py`
6. `scripts/api_smoke_test.py`

重点关注：

- workflow preview 内部直接调用 service function，不通过 HTTP 调用自己的后端接口。
- `analyze_job_match(update_application=False)` 用来避免预览时写入 `match_score`、`next_action`、`risk_flags`。
- `generate_hr_reply(update_application=False)` 用来避免预览时写入 `last_hr_message` 和 `next_action`。
- `approval_required=true` 和 `approved_by_user=false` 表示流程停在 Human-in-the-loop 节点。
- 当前不是 LangGraph，只是 rule-based workflow baseline。
## Step 11 阅读补充：LangGraph workflow

阅读 `POST /agent/langgraph_workflow_preview` 时，建议顺序：

1. `app/routes/agent_routes.py`
2. `app/schemas/agent_schema.py`
3. `app/services/langgraph_workflow_service.py`
4. `app/services/workflow_service.py`
5. `app/services/job_match_service.py`
6. `app/services/hr_reply_service.py`
7. `scripts/api_smoke_test.py`

对比阅读方式：

- 先看 Step 10 的 `run_workflow_preview()`，理解普通 Python workflow baseline。
- 再看 Step 11 的 `run_langgraph_workflow_preview()`，理解同一业务链路如何映射到 LangGraph `StateGraph`。
- 重点看 `WorkflowState` 如何保存跨 node 状态。
- 重点看 `load_profile_node` 和 `load_application_node` 后面的 Conditional Edge 如何处理错误。
- 重点确认 `analyze_job_match(update_application=False)` 和 `generate_hr_reply(update_application=False)` 如何保证预览链路只读。
## Step 11.5 阅读补充：observability

阅读 LangGraph 可观测性增强时，建议顺序：

1. 先看 `WorkflowState`，理解 state 中新增的 `state_snapshots` 和 `edge_trace`。
2. 再看 `_build_graph()`，理解真实 LangGraph Node / Edge / Conditional Edge。
3. 再看各个 node function，观察它们如何调用 `_record_state_snapshot()` 和 `_add_edge_trace()`。
4. 最后看 `_build_response_data()`，确认 `graph_structure`、`state_snapshots`、`edge_trace` 如何暴露到 API response。

阅读重点：

- `graph_structure` 是静态图结构说明。
- `state_snapshots` 是执行过程中的状态摘要。
- `edge_trace` 是本次请求的执行路径。
- 这些字段是观测增强，不是新业务能力。
## Workflow / LangGraph 阅读建议

学习 workflow / LangGraph 阶段时，建议先读 [workflow_langgraph_summary.md](workflow_langgraph_summary.md)，建立 Step 10、Step 11、Step 11.5 的整体理解；然后再读 `app/services/workflow_service.py` 和 `app/services/langgraph_workflow_service.py`，对照普通 Python workflow 与 LangGraph StateGraph 的实现差异。
## Step 12 阅读补充：JD parsing

阅读 JD 手动导入增强时，建议顺序：

1. `app/routes/application_routes.py`
2. `app/schemas/application_schema.py`
3. `app/services/application_service.py`
4. `app/services/jd_parser_service.py`
5. `app/services/job_match_service.py`
6. `app/services/workflow_service.py`
7. `app/services/langgraph_workflow_service.py`

重点关注：

- `jd_parser_service.py` 只做本地规则解析，不写数据库，不调用 LLM / RAG / Embedding。
- `application_service.py` 在 create / update 时负责调用 parser 并写入结构化字段。
- `job_match` 和 workflow preview 可以复用更规范的 application / JD 上下文，但 Step 12 不改变 workflow 结构。
## Step 13: Application Review 阅读顺序

学习 application review 时，建议按这个顺序阅读：

1. `app/schemas/application_review_schema.py`：先看请求和响应字段，理解 `review_score`、`review_level`、`confidence`、`evidence`、`decision_factors` 和 debug 边界。
2. `app/routes/application_review_routes.py`：再看 route 如何把 `application not found` 转换成稳定响应。
3. `app/services/application_review_service.py`：重点看规则评分、风险覆盖、缺失信息、`confidence`、`evidence`、`suggested_next_message_type` 和只读边界。
4. `app/services/job_match_service.py`：理解 review 如何复用 `analyze_job_match(update_application=False)`。
5. `app/services/hr_intent_service.py`：理解可选 HR message 如何影响跟进建议。

当前 Step 13 不改变 LangGraph workflow 结构；它可以作为后续 workflow 中“跟进决策节点”的候选 service。

## Step 14: LLM Enhanced Review 阅读顺序

1. `app/services/llm_service.py`：看 DeepSeek-compatible Chat Completions 的最小封装、无 API key 容错和 JSON 解析。
2. `app/services/application_review_llm_service.py`：看如何先调用规则版 review，再构造安全 prompt，并返回只读 LLM 增强结果。
3. `app/schemas/application_review_schema.py`：看 `ApplicationReviewLLMEnhanceRequest` 和 response data。
4. `app/routes/application_review_routes.py`：看 `/application_review/llm_enhance` 如何复用同一个 router。

阅读时重点确认：LLM 只做解释增强，不写数据库，不自动发送消息，不自动投递，也不自动修改 application status。

## Step 15: HR Reply Draft 阅读顺序

1. `app/services/hr_reply_draft_llm_service.py`：看如何直接复用规则版 review，并生成 `reply_strategy_for_user` 和 `hr_reply_draft`。
2. 重点阅读 `resolve_draft_type()`：确认 draft_type 如何优先根据 HR intent 决定，再参考 suggested_next_message_type、风险和状态。
3. 重点阅读 `build_prompt_by_draft_type()`：确认不同 draft_type 如何使用不同目标模板，并且所有模板共享安全边界。
4. `app/schemas/application_review_schema.py`：看 `ApplicationReviewReplyDraftRequest` 和 response data。
5. `app/routes/application_review_routes.py`：看 `/application_review/hr_reply_draft` 如何挂在现有 router 下。
6. `scripts/api_smoke_test.py`：看无 API key / 网络失败时如何验证接口不崩溃。

阅读时重点确认：该接口只返回草稿，不发送 HR 消息，不写数据库，不改 application status。

## Step 16: LangGraph Review + Reply Package 阅读顺序

学习 Step 16 时，建议按这个顺序阅读：

1. `app/schemas/agent_schema.py`：先看 `WorkflowPreviewData` 新增的 `application_review`、`hr_reply_package`、`reply_strategy_for_user`、`hr_reply_draft` 和 `node_debug`。
2. `app/services/langgraph_workflow_service.py`：重点看 `WorkflowState`、`_build_graph()`、`run_application_review_node()`、`generate_hr_reply_package_node()` 和 `require_user_approval_node()`。
3. `app/services/application_review_service.py`：确认 LangGraph review 节点复用的是 `review_application(update_application=False)`。
4. `app/services/hr_reply_draft_llm_service.py`：确认 reply package 节点复用 Step 15 的草稿生成逻辑，并支持传入 `precomputed_rule_review` 避免重复 review。
5. `scripts/api_smoke_test.py`：看 smoke test 如何验证 Step 16 节点、`node_debug`、LLM fallback 和只读边界。

阅读时重点确认：`node_debug` 是节点级可观测性字段；LangGraph workflow preview 不自动发送、不自动投递、不自动确认面试、不自动修改 application 状态。Step 14 `/application_review/llm_enhance` 仍然是独立接口，不是 Step 16 必须调用的节点。

## Step 16.5: 架构复习阅读建议

如果目标是准备面试或继续做 Step 17 之后的功能，建议先读：

1. `docs/architecture_review_step16.md`：建立当前项目定位、Step 13-16 边界、LangGraph 节点链路和企业级差距的整体认识。
2. `docs/demo_script.md`：按三条 Demo 路线验证外包 / 驻场风险、项目经验回复和面试时间场景。
3. `docs/interview_talking_points.md`：整理 30 秒版本、2 分钟版本和 LangGraph / Human-in-the-loop 的表达。
4. `app/services/langgraph_workflow_service.py`：最后再回到代码，确认文档中的节点和实际实现一致。

Step 16.5 不改变业务代码，重点是让后续阅读和演示路线更清楚。

阅读 Step 17 时要注意：`confirm_hr_reply` 仅处理用户确认 HR 回复已处理 / 已手动发送后的 application 状态更新；它不是通用 approval 系统，完整 audit log 仍属于后续规划。

## Step 16.7: 项目事实边界和面试时间阅读顺序

建议按这个顺序阅读：

1. `app/schemas/interview_availability_schema.py`：先看 `interview_availability_slots` 的字段和状态。
2. `app/services/interview_availability_service.py`：确认 slots 只是手动维护的 SQLite 记录，不接真实日历。
3. `app/routes/interview_availability_routes.py`：看 `POST / GET / PATCH` 三个最小接口。
4. `app/services/hr_reply_draft_llm_service.py`：重点看 `project_intro` 的 project fact boundary，以及 `interview_schedule` 如何读取 available slots。
5. `scripts/api_smoke_test.py`：看如何验证项目技术栈不混说、无 slots 不虚构时间、有 slots 只引用 slots、LangGraph 仍停在人工确认节点。

阅读时重点确认：AI Job Agent 当前没有 RAG / Embedding / 向量检索；RAG 企业知识库项目没有 LangGraph；面试时间草稿不自动确认具体时间。
## Step 21: Supervised Auto Reply Simulation 阅读顺序

1. `app/schemas/auto_reply_schema.py`：先看候选回复、确认和 blocked 字段。
2. `app/services/auto_reply_service.py`：确认如何复用 `simulate_agent_loop()`，以及低风险模板和中高风险 guard。
3. `app/services/agent_loop_service.py`：回看 intent、Automation Policy 和 slot preview 来源。
4. `app/routes/auto_reply_routes.py`：查看只读 HTTP 入口。
5. `scripts/api_smoke_test.py`：查看八场景矩阵和前后状态快照。

阅读重点：生成 `reply_candidate` 不代表发送；Step 21 不调用 LLM、不写数据库、不执行外部动作。
## Step 22: Final Reply Send Gate Simulation 阅读顺序

1. `app/schemas/reply_send_gate_schema.py`：查看 final decision、安全 flags 和 history 字段。
2. `app/services/reply_send_gate_service.py`：阅读 Step 21 复用、文本检查、决策顺序和有限写入。
3. `app/services/action_history_service.py`：确认 `external_action_performed=true` 会被拒绝。
4. `app/routes/reply_send_gate_routes.py`：查看 HTTP 入口。
5. `scripts/api_smoke_test.py`：查看九类场景、history 数量和状态不变断言。

阅读重点：Step 22 只写 simulated-send history，不修改 application，不执行真实外部动作。
## Step 23: Agent Workflow Demo 阅读顺序

1. `docs/agent_workflow_demo_cases.md`：先理解 low / medium / high / blocked 场景矩阵。
2. `scripts/agent_workflow_demo.py`：查看 fixture 准备、九场景调用、history 核验和清理流程。
3. `app/services/agent_loop_service.py`：回看 intent / policy / plan。
4. `app/services/auto_reply_service.py`：确认候选回复生成边界。
5. `app/services/reply_send_gate_service.py`：确认最终门禁和 simulated-send history。

Step 23 没有新增业务 service；Demo 通过 HTTP 使用现有 API，不执行真实外部动作。
