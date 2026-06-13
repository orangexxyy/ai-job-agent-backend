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
