# Code Reading Guide

这份文档面向第一次阅读本项目的学习者，帮助你按顺序理解 FastAPI route / schema / service / database 的分层，以及未来 workflow / LangGraph 应该如何复用 service。

## 推荐阅读顺序

建议按下面顺序阅读：

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
