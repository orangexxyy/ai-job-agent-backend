# Workflow / LangGraph 阶段总结

本文档用于面试复习和项目展示，重点总结 AI Job Agent 在 Step 10、Step 11、Step 11.5 中完成的 workflow / LangGraph 相关工作。

当前项目仍然是 Human-in-the-loop 后端 Demo，不是自动海投工具，不自动发送 HR 消息，不连接真实招聘平台，也不做招聘决策。

## 1. 当前阶段完成了什么

本阶段主要完成了 AI Job Agent 从“多个独立接口”到“可编排 Agent Workflow”的升级。

在此之前，项目已经具备：

- `candidate_profile` 求职档案
- `applications` 投递记录
- HR intent 分析
- HR reply 草稿生成
- `job_match` 岗位匹配评分
- Human-in-the-loop 安全边界
- `scripts/api_smoke_test.py` 自动化接口验收

本阶段进一步完成：

- Step 10：普通 Python 版 `POST /agent/workflow_preview`
- Step 11：LangGraph 版 `POST /agent/langgraph_workflow_preview`
- Step 11.5：LangGraph workflow 可观测性增强

## 2. Step 10：普通 Python workflow_preview

Step 10 新增：

```text
POST /agent/workflow_preview
```

它把已有 service 能力串成一条只读预览流程：

```text
读取 candidate_profile
-> 读取 application
-> 执行 job_match
-> 分析 HR intent
-> 生成 HR reply draft
-> 等待用户人工确认
```

这个版本不使用 LangGraph，只用普通 Python 顺序调用 service。核心价值是先验证业务流程能跑通，再考虑引入 Agent 编排框架。

它体现了 service 层的价值：workflow 不需要通过 HTTP 调用自己的后端接口，而是直接复用内部 service function。

## 3. Step 11：LangGraph workflow_preview

Step 11 新增：

```text
POST /agent/langgraph_workflow_preview
```

它和普通 `workflow_preview` 执行的是同一条业务流程，但内部使用 LangGraph `StateGraph` 表达。

LangGraph 版本把流程拆成：

- State：流程中传递和逐步更新的数据。
- Node：每一个处理步骤。
- Edge：节点之间的固定连接。
- Conditional Edge：根据状态决定下一步走向。

当前实现的 Node 包括：

```text
load_profile_node
load_application_node
run_job_match_node
analyze_hr_intent_node
generate_reply_draft_node
require_user_approval_node
handle_error_node
```

当前图结构大致是：

```text
START
-> load_profile_node
-> 条件判断：失败则 handle_error_node，否则 load_application_node
-> 条件判断：失败则 handle_error_node，否则 run_job_match_node
-> analyze_hr_intent_node
-> generate_reply_draft_node
-> require_user_approval_node
-> END
```

这个版本说明：当前业务结果可以和普通 workflow 接近，但 LangGraph 更适合表达复杂流程中的分支、错误处理、人工确认、状态流转和后续恢复。

## 4. Step 11.5：LangGraph 可观测性增强

Step 11 刚完成时，虽然代码内部使用了 LangGraph，但 Swagger 返回结果中不容易直接看出 Node / Edge / State 的区别。

Step 11.5 增强了 LangGraph 版接口的返回结果，新增：

```text
graph_structure
state_snapshots
edge_trace
```

这些字段让 LangGraph 不只是在代码里被使用，也能在接口返回中被直接观察。

## 5. 普通 workflow 和 LangGraph workflow 的区别

普通 Python workflow：

- 适合简单线性流程。
- 代码直接、容易读。
- 按函数顺序一步步调用。
- 当前适合作为 rule-based workflow baseline。

LangGraph workflow：

- 适合复杂 Agent 流程。
- 把流程拆成 State / Node / Edge。
- 可以表达条件分支、错误处理、人工确认、状态恢复。
- 更适合后续企业级 Agent 编排扩展。

当前项目里的两者业务结果接近，是因为当前流程还比较线性。但 LangGraph 版本已经为后续复杂 Agent 扩展打好结构基础。

## 6. graph_structure / state_snapshots / edge_trace

### graph_structure

`graph_structure` 展示 LangGraph 图的静态结构，包括：

- 有哪些 Node
- 有哪些普通 Edge
- 有哪些 Conditional Edge

它用于从 API 返回中直接看到 workflow 的编排设计。

### state_snapshots

`state_snapshots` 展示每个关键 Node 执行后 State 的变化。

例如：

```text
load_profile_node 后：candidate_profile_loaded = true
load_application_node 后：application_loaded = true，company_name / job_title 有值
run_job_match_node 后：has_job_match = true
analyze_hr_intent_node 后：has_hr_intent = true
generate_reply_draft_node 后：has_hr_reply = true
require_user_approval_node 后：approval_required = true
```

它用于观察 State 如何在 Node 之间逐步被填充。

### edge_trace

`edge_trace` 展示本次请求实际走过的边，包括：

- 从哪个 Node 来
- 做了什么 decision
- 走向哪个 Node
- 为什么这么走

例如：

```text
load_profile_node -> load_application_node
reason: error_message is empty
```

它用于观察 Conditional Edge 和实际执行路径。

## 7. Human-in-the-loop 边界

当前 workflow 无论是普通 Python 版还是 LangGraph 版，都坚持：

- 不自动投递
- 不自动发送 HR 消息
- 不自动确认面试时间
- 不连接真实招聘平台
- 不调用 DeepSeek / LLM
- 不把 preview 状态写入 application

workflow 最终都会停在：

```text
require_user_approval_node
```

并返回：

```text
approval_required = true
approved_by_user = false
```

这说明系统只生成建议和草稿，最终动作必须由用户确认。

## 8. 当前 smoke test 结果

当前 `scripts/api_smoke_test.py` 已经覆盖：

- `candidate_profile`
- `applications`
- `job_match`
- HR analyze
- HR reply
- 普通 `workflow_preview`
- LangGraph `workflow_preview`
- LangGraph `graph_structure / state_snapshots / edge_trace`
- workflow preview 只读验证
- 不自动更新 application
- 不自动发送消息

当前最近一次验收结果：

```text
Total: 22
Passed: 22
Failed: 0
```

## 9. 面试表达

可以这样介绍这一阶段：

> 我在 AI Job Agent 项目中先实现了一个普通 Python 版 `workflow_preview`，把 profile、application、job_match、HR intent、reply draft 和人工确认串成完整流程。随后我用 LangGraph `StateGraph` 实现了同一条流程，把每一步拆成 Node，用 Edge 和 Conditional Edge 表达节点流转。为了方便调试和面试展示，我又增加了 `graph_structure`、`state_snapshots` 和 `edge_trace`，可以直接看到图结构、每个节点后的 State 变化，以及本次请求实际走过的边。

如果面试官问为什么要用 LangGraph，可以回答：

> 当前 Demo 流程还比较线性，所以普通 Python 和 LangGraph 的业务结果接近。但 LangGraph 的优势在于后续流程复杂后，可以更清晰地表达条件分支、错误处理、人工确认、中断恢复和状态管理。比如后续加入薪资谈判、面试时间确认、岗位风险判断、人工审批后继续执行，就更适合用 LangGraph 编排。

## 10. 当前未实现边界

当前项目已经具备：

- FastAPI 后端分层
- SQLite 数据管理
- 规则版 HR intent
- 规则版 HR reply
- 规则版 `job_match`
- 普通 workflow preview
- LangGraph workflow preview
- workflow 可观测性
- Human-in-the-loop 边界
- smoke test 自动化验收

当前尚未实现：

- DeepSeek / LLM 调用
- RAG / Embedding
- Playwright
- 真实招聘平台接入
- 自动投递
- 自动发送 HR 消息
- 自动确认面试时间
- 复杂 LangGraph 循环 / 中断恢复 / 持久化状态
- 前端页面

这些边界在 README、docs 和面试表达中都必须保持真实，不能夸大。

## 11. 下一步建议

当前不建议立刻堆很多新功能。更优先的是先完成一次 workflow / LangGraph 复习：

```text
1. 调用普通 workflow_preview
2. 调用 LangGraph workflow_preview
3. 对比 workflow_steps
4. 查看 graph_structure
5. 查看 state_snapshots
6. 查看 edge_trace
7. 对照源码理解 WorkflowState / Node / Edge / Conditional Edge
```

确认能讲清楚后，再进入 Step 12。

Step 12 可以考虑：

- 岗位 JD 手动导入增强
- 岗位来源字段标准化
- 更完整的 LangGraph 人工确认后续流程 Demo

当前更推荐先围绕 LangGraph 做复习和面试讲法沉淀，再决定是否扩展业务能力。
