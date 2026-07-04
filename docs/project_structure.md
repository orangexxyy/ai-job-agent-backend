# Project Structure

## 整体目录结构

当前项目采用常见 FastAPI 分层结构：

```text
ai_job_agent/
├─ app/
│  ├─ main.py
│  ├─ database.py
│  ├─ models.py
│  ├─ routes/
│  ├─ schemas/
│  └─ services/
├─ scripts/
├─ frontend_demo/
├─ docs/
├─ README.md
├─ AGENTS.md
└─ requirements.txt
```

## 每一层的职责

- `app/main.py`  
  FastAPI 应用入口，负责创建 `FastAPI` 实例、注册 routes，并在启动时初始化 SQLite 数据库。

- `app/routes/`  
  HTTP 接口层。routes 只负责接收请求、调用 service、包装 response，不应该写大量业务逻辑。

- `app/schemas/`  
  Pydantic 数据结构层，定义请求体和响应体字段。schemas 只描述数据结构，不放业务判断。

- `app/services/`  
  业务逻辑层。profile、application、HR intent、HR reply、job_match、truth boundary 等核心逻辑都在这里。

- `app/database.py` / `app/models.py`  
  SQLite 连接和建表 SQL。数据库结构变化属于高风险操作，必须谨慎并同步文档。

- `scripts/`  
  开发测试脚本，例如 `api_smoke_test.py`，用于从外部通过 HTTP 验证主链路接口。

- `docs/`  
  设计文档、面试话术、演示脚本、结构说明和阅读指南。

## route / service 的区别

`GET /profile` 是 HTTP 接口，面向 Swagger、前端、测试脚本或外部调用方。

`get_candidate_profile()` 是内部 service 函数，面向后端代码、workflow、未来 LangGraph node 调用。

两者职责不同：

- route 是对外入口，关注 HTTP request / response。
- service 是可复用业务能力，关注具体业务规则和数据读写。

## 为什么后端内部 workflow 不建议再 HTTP 调自己

未来 workflow / LangGraph node 应该优先调用 `services/` 下的函数，而不是在后端内部再请求自己的 HTTP API。

原因：

- 避免额外 HTTP 开销。
- 避免依赖端口和服务启动状态。
- 避免循环调用。
- 更容易做单元测试和集成测试。
- 更容易复用业务逻辑。
- 更清楚地区分内部编排和外部 API。

FastAPI routes 是对外入口，LangGraph nodes 是内部编排步骤，二者都应该复用 service 层。

## 典型调用链

### POST /profile

```text
POST /profile
-> profile_routes.py
-> profile_service.py
-> database.py
-> SQLite
```

### POST /hr/reply

```text
POST /hr/reply
-> hr_routes.py
-> hr_reply_service.py
-> hr_intent_service.py
-> profile_service.py
-> context_reply_service.py
-> truth_boundary_service.py
-> application_service.py
```

### POST /job_match

```text
POST /job_match
-> job_match_routes.py
-> job_match_service.py
-> application_service.py
-> profile_service.py
```

### scripts/api_smoke_test.py

```text
scripts/api_smoke_test.py
-> HTTP 调用本地 FastAPI
-> 验证主链路接口
```

## 主要 service 函数速查

关键 public service function 应使用中文 docstring，技术名词保留英文，并简要说明用途、输入、输出和副作用，尤其是 SQLite 写入、Human-in-the-loop、LLM、RAG、LangGraph、Playwright 等边界。

| 函数 | 文件 | 作用 |
| --- | --- | --- |
| `save_candidate_profile` | `app/services/profile_service.py` | 保存单用户 `candidate_profile` |
| `get_candidate_profile` | `app/services/profile_service.py` | 读取单用户 `candidate_profile` |
| `create_application` | `app/services/application_service.py` | 创建投递记录 |
| `list_applications` | `app/services/application_service.py` | 查询投递记录列表 |
| `get_application` | `app/services/application_service.py` | 读取单条投递记录 |
| `update_application` | `app/services/application_service.py` | 局部更新投递记录 |
| `analyze_hr_message` | `app/services/hr_intent_service.py` | 规则版 HR intent 分析 |
| `generate_hr_reply` | `app/services/hr_reply_service.py` | 生成 HR 回复草稿 |
| `select_relevant_context_snippets` | `app/services/context_reply_service.py` | 从 profile context 中选择相关片段 |
| `build_context_enhanced_reply` | `app/services/context_reply_service.py` | 生成项目/技术/方案类增强草稿 |
| `analyze_job_match` | `app/services/job_match_service.py` | 规则版岗位匹配评分 |
| `check_truth_boundary` | `app/services/truth_boundary_service.py` | 检查回复草稿是否触碰事实边界 |

## 为未来 workflow / LangGraph 做准备

未来 workflow node 应该优先复用 `services/` 下的函数，而不是重复写 HTTP 请求。

推荐方向：

- `load_profile` node 调用 `get_candidate_profile()`。
- `load_application` node 调用 `get_application()`。
- `run_job_match` node 调用 `analyze_job_match()`。
- `generate_reply_draft` node 调用 `generate_hr_reply()`。
- `update_application` node 调用 `update_application()`。

这样可以保持业务逻辑集中在 service 层，让 FastAPI routes 和 LangGraph workflow 都复用同一套能力。
## Step 10 新增文件

- `app/routes/agent_routes.py`  
  提供 `POST /agent/workflow_preview` HTTP 入口，只负责接收请求、调用 service、包装响应和转换明确错误。
- `app/schemas/agent_schema.py`  
  定义 workflow preview 的 request / response 结构，包括 `workflow_steps`、`state_summary`、`job_match`、`hr_intent`、`hr_reply` 和审批状态。
- `app/services/workflow_service.py`  
  提供 `run_workflow_preview()`，直接复用现有 service function 串联只读预览流程。

### POST /agent/workflow_preview

```text
POST /agent/workflow_preview
-> agent_routes.py
-> workflow_service.py
-> profile_service.py
-> application_service.py
-> job_match_service.py(update_application=False)
-> hr_intent_service.py(optional)
-> hr_reply_service.py(update_application=False, optional)
```

`workflow_preview` 是规则版预览链路，不是 LangGraph。它不写 application，不调用 LLM，不实现 RAG / Playwright，不自动投递，不自动发送 HR 消息。

| 函数 | 文件 | 作用 |
| --- | --- | --- |
| `run_workflow_preview` | `app/services/workflow_service.py` | 串联 profile、application、job_match、HR intent 和 HR reply，返回只读 workflow preview |
## Step 11 新增文件

- `app/services/langgraph_workflow_service.py`  
  使用 LangGraph `StateGraph` 编排最小 workflow preview，复用 profile、application、job_match、HR intent 和 HR reply service。

### POST /agent/langgraph_workflow_preview

```text
POST /agent/langgraph_workflow_preview
-> agent_routes.py
-> langgraph_workflow_service.py
-> StateGraph
   -> load_profile_node
   -> load_application_node
   -> run_job_match_node
   -> analyze_hr_intent_node
   -> generate_reply_draft_node
   -> require_user_approval_node
```

Conditional Edge：

```text
load_profile_node -> handle_error_node | load_application_node
load_application_node -> handle_error_node | run_job_match_node
```

`langgraph_workflow_service.py` 是 Step 11 的最小 LangGraph demo，不写 application，不调用 LLM，不自动投递，不自动发送 HR 消息。

| 函数 | 文件 | 作用 |
| --- | --- | --- |
| `run_langgraph_workflow_preview` | `app/services/langgraph_workflow_service.py` | 使用 LangGraph StateGraph 串联只读 workflow preview |
## Step 11.5 可观测性字段

`app/services/langgraph_workflow_service.py` 现在除了执行最小 `StateGraph`，还负责生成面向 Swagger 和面试展示的观测数据：

- `_graph_structure()`  
  返回 nodes、edges、conditional_edges。
- `_record_state_snapshot()`  
  在关键 node 后记录轻量 state snapshot。
- `_add_edge_trace()`  
  记录本次 workflow 实际走过的边和条件判断原因。

这些字段只用于调试和展示，不改变业务行为，不写数据库。
## Step 12 新增 service

- `app/services/jd_parser_service.py`  
  本地规则版 JD 解析 service，用于标准化 `source_type`，抽取 `jd_keywords`、`jd_required_skills`、年限要求、地点要求和远程类型，并生成规则版 `jd_summary`。

职责边界：

- 不写数据库。
- 不调用 DeepSeek / LLM。
- 不实现 RAG / Embedding / 向量检索。
- 不抓取岗位，不连接真实招聘平台。
- 解析结果只用于求职者侧快速筛选和 application 数据标准化。

调用链：

```text
POST/PATCH /applications
-> application_routes.py
-> application_service.py
-> jd_parser_service.py
-> SQLite applications
```
## Step 13: Application Review Files

| File | Responsibility |
| --- | --- |
| `app/schemas/application_review_schema.py` | 定义 `POST /application_review` 的请求、响应和 review data 结构 |
| `app/routes/application_review_routes.py` | 注册 `/application_review` route，并处理 `application not found` |
| `app/services/application_review_service.py` | 基于 application、JD 解析字段、`job_match`、HR intent、风险、缺失信息、`confidence` 和 `evidence` 生成规则版跟进建议 |

调用链：

```text
POST /application_review
-> application_review_routes.review_application_route
-> application_review_service.review_application
-> application_service.get_application
-> job_match_service.analyze_job_match(update_application=False)
-> hr_intent_service.analyze_hr_message(optional)
```

Step 13 的 service 保持只读，不写 `application.status`，不发送 HR 消息，不自动投递，不调用 LLM / RAG / Playwright。`confidence` 是规则证据充分程度，不是模型概率；`evidence` 用于解释规则判断，也为未来 LLM enhanced review 提供上下文。

## Step 14: LLM Enhanced Review Files

| File | Responsibility |
| --- | --- |
| `app/services/llm_service.py` | DeepSeek-compatible Chat Completions 最小封装，处理 API key 缺失、网络错误和 JSON 解析 |
| `app/services/application_review_llm_service.py` | 基于规则版 application review 构造安全 prompt，并返回只读 LLM 增强分析 |
| `app/routes/application_review_routes.py` | 在 `/application_review` router 下注册 `/llm_enhance` |
| `app/schemas/application_review_schema.py` | 定义 LLM enhance 请求和响应 schema |

Step 14 不新增数据库表，不写 review 历史，不改 application status / next_action / risk_flags。

## Step 15: HR Reply Draft Files

| File | Responsibility |
| --- | --- |
| `app/services/hr_reply_draft_llm_service.py` | 默认基于规则版 application review 直接生成 `reply_strategy_for_user` 和 `hr_reply_draft`，支持一次 LLM 调用和 rule fallback |
| `app/routes/application_review_routes.py` | 在 `/application_review` router 下注册 `/hr_reply_draft` |
| `app/schemas/application_review_schema.py` | 定义 HR reply draft 请求和响应 schema |

Step 15 默认不调用 Step 14，避免重复 LLM 调用。它不新增消息发送能力，不写 review 历史，不改 application status / next_action / risk_flags。

## Step 16: LangGraph Review + Reply Package Files

| File | Responsibility |
| --- | --- |
| `app/services/langgraph_workflow_service.py` | 使用 LangGraph `StateGraph` 串联 profile 读取、application 读取、规则版 application review、HR reply package 生成和 Human-in-the-loop 审批节点 |
| `app/schemas/agent_schema.py` | 为 `/agent/langgraph_workflow_preview` 增加 `application_review`、`hr_reply_package`、`reply_strategy_for_user`、`hr_reply_draft`、`node_debug` 等响应字段 |
| `app/services/hr_reply_draft_llm_service.py` | 支持接收 `precomputed_rule_review`，让 LangGraph reply package 节点复用已生成的规则 review，避免重复分析 |
| `scripts/api_smoke_test.py` | 验证 Step 16 LangGraph 节点链路、reply package、`node_debug` 和 application 只读边界 |

Step 16 不新增 route 文件，不新增数据库表，不新增发送消息能力。`POST /agent/langgraph_workflow_preview` 仍然是只读 preview：不自动发送 HR 消息，不自动投递，不自动确认面试，不自动修改 application `status / next_action / risk_flags / last_hr_message`。

## Step 16.5: Architecture Review Document

| File | Responsibility |
| --- | --- |
| `docs/architecture_review_step16.md` | 梳理 Step 16 之后的项目定位、核心接口、Step 13-16 职责边界、LangGraph 节点链路、可观测性字段、Human-in-the-loop 边界、企业级差距和后续路线图 |

Step 16.5 是 docs-only 整理，不新增业务接口，不修改 service，不新增数据库表。

## Step 17.2: Mainline Acceptance Documents

| File | Responsibility |
| --- | --- |
| `docs/mainline_acceptance_report.md` | 记录主流程实测结果、关键证据、安全边界、Legacy 接口、当前风险和后续建议 |
| `docs/demo_3_minute_pitch.md` | 提供真实、不夸大的三分钟项目介绍稿 |

Step 17.2 不新增业务接口或数据库表；`scripts/api_smoke_test.py` 只调整可重复运行的测试 slot 唯一性、断言和清理逻辑。

## Step 19A: Automation Policy Files

| File | Responsibility |
| --- | --- |
| `app/schemas/automation_policy_schema.py` | 定义策略请求、决策和响应 |
| `app/services/automation_policy_service.py` | 纯规则风险与权限判断，强制禁止外部动作 |
| `app/routes/automation_policy_routes.py` | 提供只读策略评估 API |
| `docs/automation_policy_design.md` | 说明风险等级、动作权限和 Agent Loop 关系 |

## Step 20: Agent Loop Simulation Files

| File | Responsibility |
| --- | --- |
| `app/schemas/agent_loop_schema.py` | 定义单轮模拟请求和结果 |
| `app/services/agent_loop_service.py` | 只读编排 observe、intent、policy 和 plan |
| `app/routes/agent_loop_routes.py` | 提供 `/agent/loop/simulate` |
| `docs/agent_loop_simulation_design.md` | 说明单轮模拟及 supervised agent 演进 |

## Step 18A: Application Action History Files

| File | Responsibility |
| --- | --- |
| `app/schemas/action_history_schema.py` | 定义 action history item 和列表响应 |
| `app/services/action_history_service.py` | 写入关键动作并按 application 只读查询；强制 external action 为 false |
| `docs/action_history_design.md` | 说明数据结构、隐私控制、当前边界和后续演进 |

`application_service.py` 写入 application_created / hr_reply_confirmed，`interview_availability_service.py` 写入 interview_slot_booked，`application_routes.py` 提供 `GET /applications/{application_id}/action_history`。

## Step 16.7: Interview Availability And Fact Boundary Files

| File | Responsibility |
| --- | --- |
| `app/models.py` | 新增 `interview_availability_slots` SQLite 表定义 |
| `app/database.py` | 启动时初始化 `interview_availability_slots` 表 |
| `app/schemas/interview_availability_schema.py` | 定义面试可用时间段 create / update / response schema |
| `app/services/interview_availability_service.py` | 手动创建、查询、更新面试可用时间段；不接真实日历，不自动确认面试 |
| `app/routes/interview_availability_routes.py` | 注册 `/interview_availability_slots` API |
| `app/services/hr_reply_draft_llm_service.py` | 增加项目事实边界校验，并让 `interview_schedule` 草稿基于 available slots |
| `scripts/api_smoke_test.py` | 覆盖 project_intro 不混淆项目、面试时间有 / 无 slots、LangGraph 人工确认边界 |

Step 16.7 不连接 Google Calendar，不连接真实招聘平台，不自动发送 HR 消息，不自动投递，不自动确认面试。
## Step 21 新增文件

- `app/schemas/auto_reply_schema.py`：定义 supervised auto reply 请求和响应结构。
- `app/services/auto_reply_service.py`：复用 Step 20，执行低风险候选回复规则和安全 guard。
- `app/routes/auto_reply_routes.py`：提供 `POST /agent/auto_reply/simulate`。
- `docs/auto_reply_simulation_design.md`：记录生成规则、确认场景、阻断场景和只读边界。

```text
POST /agent/auto_reply/simulate
-> auto_reply_routes.py
-> auto_reply_service.py
-> agent_loop_service.py
-> automation_policy_service.py
-> read-only profile / application / slots / history services
```
## Step 22 新增文件

- `app/schemas/reply_send_gate_schema.py`：定义最终门禁请求、决策和 history 写入结果。
- `app/services/reply_send_gate_service.py`：复用 Step 21，执行 final safety check 和 simulated-send history 写入。
- `app/routes/reply_send_gate_routes.py`：提供 `POST /agent/reply_send_gate/simulate`。
- `docs/reply_send_gate_design.md`：记录门禁规则、决策枚举和外部动作边界。

```text
POST /agent/reply_send_gate/simulate
-> reply_send_gate_routes.py
-> reply_send_gate_service.py
-> auto_reply_service.py (Step 21, read-only)
-> action_history_service.py (only when gate passes)
```
## Step 23 新增文件

- `scripts/agent_workflow_demo.py`：准备独立 Demo fixture，运行九类 HR 场景并核验 action history。
- `docs/agent_workflow_demo_cases.md`：记录 low / medium / high / blocked 演示矩阵和预期结果。

Step 23 不新增 route、schema、service 或数据库结构。
## Step 24 新增目录

- `frontend_demo/index.html`：无构建依赖的静态 Agent Workflow 工作台。
- `frontend_demo/README.md`：直接打开和本地 HTTP server 两种启动方式。

前端只调用现有 `reply_send_gate` 和 `action_history` API。`app/main.py` 仅增加 `null`、`127.0.0.1:5173` 和 `localhost:5173` 本地来源的受限 CORS，不新增业务接口。
## Step 25 新增文件

- `scripts/start_demo.ps1`：Windows 一键启动 FastAPI 与静态前端，等待退出并只清理本次启动的进程树。

该脚本是本地开发工具，不新增后端业务能力，也不执行真实外部动作。
