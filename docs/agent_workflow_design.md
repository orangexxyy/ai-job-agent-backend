# Agent Workflow Design

## 项目定位

AI Job Agent 是面向 AI应用开发 / 大模型应用开发求职场景的 Human-in-the-loop Agent 后端 Demo。它用于管理候选人求职档案、具体投递记录、HR 消息分析、岗位匹配评分和回复草稿生成。

当前项目不是自动海投工具，不自动发送 HR 消息，不连接真实招聘平台，也不做招聘决策。系统可以自动生成分析结果和草稿，但所有外发动作、投递动作、面试时间确认和外部平台操作都必须由用户确认。

## Step 1-8 能力总览

- Step 1：`candidate_profile`  
  建立候选人稳定求职档案，包括薪资、城市、到岗时间、目标岗位、项目经历和 truth boundaries。

- Step 2：`hr_analyze`  
  基于规则分析 HR 消息 intent，例如薪资、到岗、面试时间、项目经历、技术问题和业务方案。

- Step 3：`hr_reply`  
  基于 `candidate_profile` 生成 HR 回复草稿，并经过 truth boundary 检查，不自动发送。

- Step 4：`applications`  
  手动记录具体投递，包括公司、岗位、JD、状态、HR 最新消息和下一步动作。

- Step 5：`application_id context`  
  `/hr/reply` 可以绑定具体 application，优先使用投递记录中的公司和岗位上下文，并安全更新 `last_hr_message` / `next_action`。

- Step 6：`api smoke test harness`  
  用 `scripts/api_smoke_test.py` 做本地 API 主链路验收，保证核心接口可跑通。

- Step 7：`job_match`  
  基于规则做求职者侧岗位匹配评分，回写 `match_score`、`next_action`、`risk_flags`，不代表招聘方录用决策。

- Step 8：`profile context enhanced reply`  
  `/hr/reply` 对项目经历、技术问题、业务方案类 intent 使用 `resume_text` / `project_context` 做轻量片段选择，生成更具体但保守的草稿。当前不是 RAG，不调用 LLM。

## 核心数据源

- `candidate_profile`：候选人的稳定求职档案，是回复草稿和匹配评分的基础事实来源。
- `applications`：具体投递记录，提供公司、岗位、JD、状态、HR 最新消息和下一步动作。
- `resume_text`：简历级文本资料，用于回答项目经历和技术实践类问题。
- `project_context`：更详细的项目上下文，用于生成项目讲法、技术解释和 PoC 方案草稿。
- `truth_boundaries`：不能夸大的能力边界，防止系统编造生产级经历、自动投递经历或自动沟通能力。

## 核心工具能力视角

以下能力可以视为未来 Agent workflow 可编排的工具节点。它们不一定已经以独立 Tool 接口暴露，但代表当前系统可复用的能力：

- `get_candidate_profile`：读取候选人档案。
- `get_application`：读取某条投递记录。
- `analyze_hr_message`：分析 HR 消息 intent 和风险级别。
- `generate_hr_reply`：生成 HR 回复草稿。
- `analyze_job_match`：规则版岗位匹配评分。
- `update_application`：安全更新投递记录中的状态字段、下一步动作、匹配分和风险标记。
- `run_api_smoke_test`：运行本地 API 验收脚本。

## 未来 Agent Workflow 草图

```text
START
-> load_profile
-> load_application
-> run_job_match
-> decide_next_action
-> generate_reply_draft
-> require_user_approval
-> update_application
-> END
```

这个流程的核心思想是：系统可以自动整理信息、计算建议、生成草稿和更新内部下一步动作，但不能越过用户确认去执行外部沟通或投递。

## State 设计

未来 LangGraph State 可以包含：

- `application_id`
- `candidate_profile`
- `application`
- `match_score`
- `match_level`
- `hr_message`
- `reply_draft`
- `selected_context_snippets`
- `risk_flags`
- `next_action`
- `approval_required`
- `approved_by_user`

这些字段让 workflow 能够在多个节点之间传递上下文，并支持失败回退、人工确认和审计。

## Node 设计

- `load_profile`  
  读取 `candidate_profile`。如果不存在，返回明确错误并停止。

- `load_application`  
  根据 `application_id` 读取投递记录。只加载必要字段，避免把完整数据库行无脑作为上下文。

- `run_job_match`  
  基于规则计算岗位匹配分、匹配等级、风险标记和建议下一步。

- `analyze_hr_intent`  
  对 HR 消息做 intent 分类，判断是否需要 profile、project context 或人工确认。

- `generate_reply_draft`  
  根据 intent、candidate profile、application context 和 profile context 生成保守回复草稿。

- `check_truth_boundary`  
  检查草稿是否触碰不可夸大的能力边界。

- `require_user_approval`  
  对所有外发动作、面试时间确认、投递动作进行人工确认拦截。

- `update_application_status`  
  只在用户确认或明确规则允许时更新投递记录。当前系统不会由 `/hr/reply` 自动修改 status。

- `export_action_plan`  
  输出给用户看的下一步行动建议，例如“准备项目讲法”“确认面试时间”“谨慎评估外包风险”。

## Conditional Edge 示例

- `match_score >= 80` -> 建议优先跟进。
- `match_score < 40` -> 建议不优先投入。
- HR 消息属于项目经历 / 技术方案 -> 使用 profile context enhanced reply。
- `safe_to_send = false` -> 必须进入 human approval。
- `application not found` -> 返回错误并停止。
- `candidate_profile not found` -> 提示先创建 profile。
- `risk_flags` 非空 -> 在下一步动作中提醒用户确认风险点。

## Human-in-the-loop 边界

可以自动完成：

- 自动生成回复草稿。
- 自动分析岗位匹配。
- 自动生成 `next_action`。
- 自动标记内部风险提示。

必须人工确认：

- 发送 HR 消息。
- 投递简历。
- 确认面试时间。
- 薪资承诺或谈判回复。
- 任何真实招聘平台操作。
- 外部平台操作必须 dry-run 或由用户确认后执行。

## 为什么后续适合 LangGraph

LangGraph 适合这个项目的原因：

- 状态化工作流：求职流程天然有 profile、application、message、reply、approval 等状态。
- 多节点编排：读取档案、岗位评分、HR intent、回复生成、人工确认可以拆成节点。
- 条件分支：不同 intent、risk_level、match_score 会走不同路径。
- 工具调用：可把现有 service 能力包装成工具节点。
- 人工确认节点：非常适合 Human-in-the-loop。
- 失败回退：profile 缺失、application 缺失、上下文不足都可以显式处理。
- 审计 `agent_steps`：方便面试展示和后续排查。

## 当前不做什么

- 不实现完整自动投递。
- 不自动发送消息。
- 不自动确认面试。
- 不做招聘决策。
- 不连接真实招聘平台。
- 不绕过平台风控。
- 不夸大候选人经历。
- 不调用 DeepSeek / LLM。
- 不实现 Playwright。
- 不实现 RAG 或 Embedding。

## 后续路线

- Step 13：Application review / follow-up decision layer。
- Step 14：LLM enhanced application review，只读增强分析。
- Step 15：HR reply draft enhancement，可选，仍需人工确认。
- Step 16：用户确认后的状态更新 workflow，可选，且必须 Human-in-the-loop。
- Later：Playwright dry-run 岗位采集，必须人工确认，且不做自动投递。
## Step 10 已实现：规则版 workflow_preview

Step 10 新增 `POST /agent/workflow_preview`，先用普通 Python service 串联现有能力，作为 LangGraph 之前的最小可运行 workflow preview。

当前链路：

```text
load_candidate_profile
-> load_application
-> run_job_match(update_application=False)
-> analyze_hr_intent(optional)
-> generate_reply_draft(update_application=False, optional)
-> require_user_approval
```

设计边界：

- 这是 rule-based preview，不是 LangGraph。
- workflow 内部直接调用 service function，不从后端内部 HTTP 调用自己的 API。
- `job_match` 和 `hr_reply` 都关闭 application 回写，保证预览接口不修改数据库中的投递状态。
- 输出 `approval_required=true`、`approved_by_user=false`，明确下一步需要用户人工确认。
- 不调用 DeepSeek / LLM，不实现 RAG / Embedding，不使用 Playwright，不连接真实招聘平台。
- 不自动投递、不自动发送 HR 消息、不自动确认面试时间。
## Step 11 已实现：最小 LangGraph StateGraph

Step 11 新增 `POST /agent/langgraph_workflow_preview`，把 Step 10 的普通 Python workflow baseline 迁移成最小 LangGraph `StateGraph`。

代码位置：

- `app/services/langgraph_workflow_service.py`
- `app/routes/agent_routes.py`

State 核心字段：

- `application_id`
- `hr_message`
- `candidate_profile_loaded`
- `application_loaded`
- `company_name`
- `job_title`
- `job_match`
- `hr_intent`
- `hr_reply`
- `workflow_steps`
- `approval_required`
- `approved_by_user`
- `next_action`
- `error_message`
- `debug`

Nodes：

- `load_profile_node`
- `load_application_node`
- `run_job_match_node`
- `analyze_hr_intent_node`
- `generate_reply_draft_node`
- `require_user_approval_node`
- `handle_error_node`

Edges / Conditional Edges：

```text
START
-> load_profile_node
-> conditional: error_message ? handle_error_node : load_application_node
-> conditional: error_message ? handle_error_node : run_job_match_node
-> analyze_hr_intent_node
-> generate_reply_draft_node
-> require_user_approval_node
-> END

handle_error_node -> END
```

只读边界：

- `analyze_job_match(update_application=False)`
- `generate_hr_reply(update_application=False)`
- 不写 `status`
- 不写 `next_action`
- 不写 `last_hr_message`
- 不写 `match_score`

当前仍然不调用 DeepSeek / LLM，不实现 RAG / Embedding，不使用 Playwright，不连接真实招聘平台，不自动投递，不自动发送 HR 消息，不自动确认面试时间。
## Step 11.5: LangGraph 可观测性

为了让 Swagger 返回结果能直接体现 LangGraph 编排，`/agent/langgraph_workflow_preview` 新增了三个观测字段：

- `graph_structure`  
  展示当前 StateGraph 的 nodes、普通 edges 和 conditional edges。
- `state_snapshots`  
  在关键 node 执行后记录轻量 state，例如 profile 是否已加载、application 是否已加载、是否已有 job_match / hr_intent / hr_reply、是否进入 approval。
- `edge_trace`  
  记录本次请求实际走过的边，包括 conditional edge 的 decision、to node 和 reason。

这三个字段让接口返回同时体现：

- Node：业务步骤如何拆分。
- Edge：普通流程如何串联。
- Conditional Edge：缺少 profile / application 时如何进入 `handle_error_node`。
- State：每个 node 后状态如何变化。
- Human-in-the-loop：`require_user_approval_node` 设置 `approval_required=true`、`approved_by_user=false` 后停止到 `END`。

这只是观测增强，不新增业务能力，不写数据库，不调用 LLM，不自动发送 HR 消息，不自动投递。
## Step 12 对 workflow 的影响

Step 12 增强的是 application / JD 上下文质量：创建或更新 application 时会生成 `source_type`、`jd_summary`、`jd_keywords`、`jd_required_skills`、年限要求、地点要求和远程类型。

这些字段可以被后续 `job_match`、普通 `workflow_preview` 和 LangGraph `workflow_preview` 复用，但 Step 12 不改变现有 LangGraph workflow 结构，不新增 Node / Edge / Conditional Edge，也不调用 LLM / RAG / Playwright。
## Step 13: Application Review As Future Workflow Node

Step 13 的 `POST /application_review` 可以作为后续 workflow 中“跟进决策节点”的候选能力。当前它先作为独立只读 API 存在，不改变普通 Python workflow 或 LangGraph workflow 的结构。

该节点未来可以接在 `job_match` 和 `hr_intent` 之后，用于生成 `review_score`、`review_level`、`confidence`、`evidence`、`recommended_action` 和 Human-in-the-loop 所需的确认信息。`confidence` 是规则证据充分程度，不是模型概率；`evidence` 用于解释规则判断，也为未来 LLM enhanced review 提供上下文。当前实现不调用 LLM / RAG / Playwright，不连接真实招聘平台，不自动投递，不自动发送 HR 消息，也不自动修改 application status。

## Step 14: LLM Enhance Review As Future Node

`POST /application_review/llm_enhance` 未来可以作为 LangGraph 中的 `llm_enhance_review_node` 候选能力。当前它先作为独立只读 API 存在，不改变 LangGraph workflow 结构。

该能力只在规则版 review 之后做解释增强，不从零判断岗位，不写数据库，不自动发送 HR 消息，不自动投递，不自动确认面试，也不自动修改 application status。
