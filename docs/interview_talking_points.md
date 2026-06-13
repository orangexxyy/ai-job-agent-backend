# Interview Talking Points

## 一句话介绍

AI Job Agent 是一个面向 AI应用开发求职场景的 Human-in-the-loop Agent Demo，用于管理求职档案、投递记录、HR 消息、岗位匹配和回复草稿。

## 为什么做这个项目

这个项目想解决几个真实求职流程里的问题：

- 求职信息分散在简历、聊天记录、岗位 JD 和表格里，容易丢上下文。
- HR 消息回复容易临时发挥，可能遗漏薪资、到岗、城市、项目边界等关键信息。
- 岗位匹配不能只凭感觉，需要一个可解释的求职者侧优先级判断。
- 后续想学习企业级 Agent Workflow / LangGraph，需要一个真实但边界清晰的业务场景。

## Step 1-8 怎么讲

### Step 1：candidate_profile

做了候选人求职档案，包含薪资、城市、到岗时间、目标岗位、项目经历和 truth boundaries。  
这样 HR 回复和岗位匹配都有稳定事实来源，而不是每次临时拼回答。  
边界是：不编造候选人经历，不把未填写的信息当成事实。  
面试表达：我先把“候选人事实层”建起来，这是后续 Agent 决策和草稿生成的基础。

### Step 2：hr_analyze

做了规则版 HR Intent Analyzer，用来识别薪资、到岗、外地、面试时间、项目经历、技术问题等 intent。  
第一版不用 LLM，是为了可解释、稳定、低成本，也方便写测试。  
边界是：它只做意图识别，不做外部沟通。  
面试表达：我先用规则建立 baseline，后续可以再替换成 LLM 或 hybrid intent analyzer。

### Step 3：hr_reply

做了基于 `candidate_profile` 的 HR 回复草稿生成，并接入 truth boundary 检查。  
它能根据薪资、到岗、城市、外包、面试时间等 intent 生成保守草稿。  
边界是：只返回草稿，不自动发送，不调用 LLM。  
面试表达：这是 Human-in-the-loop 设计，系统负责准备草稿，用户负责最终确认。

### Step 4：applications

做了投递记录模块，记录公司、岗位、JD、来源、状态、HR 最新消息和下一步动作。  
这样系统可以围绕具体 application 组织上下文。  
边界是：只支持手动记录和更新，不连接真实招聘平台，不自动投递。  
面试表达：我把“岗位上下文”独立建模，后续才能做 job_match 和 application-aware reply。

### Step 5：application_id context

让 `/hr/reply` 支持可选 `application_id`。  
传入 application 后，系统优先使用该投递记录里的公司和岗位，并返回白名单字段构造的 `application_context`。  
边界是：只安全更新 `last_hr_message` 和 `next_action`，不自动改 status，不自动发送消息。  
面试表达：这一步把“单条 HR 消息”绑定到“具体投递记录”，回复更贴近上下文。

### Step 6：API smoke test harness

新增 `scripts/api_smoke_test.py`，一键验收主链路 API。  
它覆盖 health、profile、applications、hr_analyze、hr_reply、job_match 等接口。  
边界是：它是开发验收工具，不是业务功能。  
面试表达：我用 smoke test 保证每一步迭代后主链路不被破坏。

### Step 7：job_match

新增规则版岗位匹配评分。  
它根据 candidate_profile 和 application 的 JD / job_title / notes 给出求职者侧优先级分数。  
边界是：分数不代表招聘方录用概率，不做招聘决策。  
面试表达：job_match 是可解释的跟进优先级工具，帮助用户决定先看哪些岗位。

### Step 8：profile context enhanced reply

增强 `/hr/reply`，对项目经历、技术问题、业务方案类 intent 使用 `resume_text` / `project_context` 做片段选择。  
这让回答更具体，但仍然保守，不夸大为生产级经验。  
边界是：这不是 RAG，不做 Embedding，不调用 LLM，只是规则版片段选择。  
面试表达：我先做了轻量 context selection，为后续 RAG 或 LangGraph 编排预留接口和数据结构。

## 关键设计取舍

### 为什么先规则版，不直接 LLM

规则版更稳定、可解释、成本低，适合做 baseline。  
求职场景还涉及事实边界和外发风险，第一版应该先保证不会胡说、不会误发。  
后续可以把规则版作为 guardrail，再引入 LLM 做增强。

### 为什么不自动发送 HR 消息

HR 沟通属于真实外部承诺，可能涉及薪资、到岗、面试时间和履历事实。  
系统可以生成草稿，但发送动作必须由用户确认。  
这也是 Human-in-the-loop 的核心边界。

### 为什么 job_match 不代表招聘决策

`job_match` 是求职者侧优先级评分，只表示“这个岗位是否值得我优先跟进”。  
它不掌握招聘方内部标准，也不应该输出“是否录用”的结论。  
所以它是决策辅助，不是招聘决策系统。

### 为什么 context enhanced reply 不是 RAG

当前只是从 `resume_text` / `project_context` 中做关键词片段选择。  
没有向量库、Embedding、召回、rerank 或知识库索引。  
它是 profile context enhanced reply，不是 RAG。

### 为什么要有 smoke test harness

这个项目每一步都会新增接口和状态更新。  
Smoke test 可以快速验证主链路，避免修改一个模块时破坏另一个模块。  
它也适合面试演示，证明项目是可运行、可验收的。

### 为什么后续适合 LangGraph

当前流程已经有多个节点：load profile、load application、job match、intent analyze、reply draft、truth boundary、user approval。  
后续加入更多条件分支和人工确认后，LangGraph 比普通 service 串联更适合表达状态流转。

## 面试官可能追问与回答

**Q：你这个是不是自动投递系统？**  
A：不是。当前是 Human-in-the-loop 的求职 Agent Demo，可以生成分析结果和草稿，但外发消息、投递简历、确认面试时间都必须人工确认。

**Q：为什么不直接用 LLM？**  
A：第一版先做规则 baseline，保证稳定、可解释、低成本。求职场景涉及履历真实性和外部沟通风险，规则版能先把边界守住。

**Q：job_match 分数代表什么？**  
A：代表求职者侧的跟进优先级，不代表招聘方录用概率，也不是招聘决策。

**Q：context enhanced reply 是 RAG 吗？**  
A：不是。它只是基于 `resume_text` / `project_context` 的规则片段选择，没有 Embedding、向量检索或 reranker。

**Q：为什么要用 LangGraph？**  
A：当流程变成多节点、多条件分支、多状态流转，并且需要人工确认节点时，LangGraph 更适合编排和审计。

**Q：现在有没有连接真实招聘平台？**  
A：没有。当前只做本地后端 Demo 和手动记录，不连接真实平台，也不绕过平台规则。

**Q：会不会自动发送 HR 消息？**  
A：不会。系统只生成草稿和建议，发送必须由用户确认。

**Q：如果 HR 问项目经历，系统怎么避免夸大？**  
A：回复只基于 `candidate_profile`、`resume_text`、`project_context` 和 truth boundaries。没有上下文时会提示补充，不编造经历。

**Q：你怎么保证改动后接口还能跑？**  
A：我写了 `scripts/api_smoke_test.py`，覆盖 profile、applications、job_match、hr_analyze、hr_reply 等主链路。

**Q：后续如何升级到企业级 Agent？**  
A：可以把现有 service 包装成工具节点，用 LangGraph 管理 State、Conditional Edge、人工确认和失败回退，再逐步接入 RAG 或 LLM。

## 项目亮点总结

- Human-in-the-loop 边界清晰。
- `applications` 做了投递状态管理。
- `/hr/reply` 支持 `application_id` 上下文。
- 规则版 `job_match` 可解释。
- `profile context enhanced reply` 能利用简历和项目上下文。
- truth boundary 防止夸大经历。
- API smoke test harness 保证主链路可验收。
- 后续适合升级为 LangGraph workflow。

## 不夸大边界

不能说：

- 已实现自动投递。
- 已连接真实招聘平台。
- 已自动发送 HR 消息。
- 已实现完整生产级 Agent。
- 已实现完整 RAG 项目经历库。
- 评分代表招聘结果。
- 候选人做过完整生产级智能招聘系统。

可以说：

- 当前是可运行的后端 Demo。
- 当前是规则版 baseline。
- 当前强调 Human-in-the-loop。
- 当前为后续 LangGraph / RAG / dry-run automation 做了结构准备。
## Step 10: workflow_preview 面试表达

Step 10 做了一个规则版 `POST /agent/workflow_preview`，它不是 LangGraph，而是先把已有 service 能力串成可运行的 workflow baseline。

可以这样介绍：

> 我先没有急着上 LangGraph，而是实现了一个 rule-based workflow preview。它会读取 candidate_profile 和 application，复用 job_match，再根据可选 HR message 复用 HR intent 和 HR reply draft，最后停在 Human-in-the-loop 审批节点。这个接口只做预览，不写 application，不发消息，不投递。

面试官可能追问：

**Q：这是不是已经实现 LangGraph 了？**  
A：不是。当前是普通 Python service 编排，用来验证节点边界、状态结构和 Human-in-the-loop 流程。后续可以把这些 service 包装成 LangGraph nodes。

**Q：workflow_preview 会不会改投递状态？**  
A：不会。它调用 `analyze_job_match(update_application=False)` 和 `generate_hr_reply(update_application=False)`，只返回预览结果，不写 `status`、`next_action`、`last_hr_message` 或 `match_score`。

**Q：为什么要先做 preview？**  
A：先用最小可运行链路验证业务流程和安全边界，再上 LangGraph，会更容易控制复杂度，也方便 smoke test 覆盖主链路。
## Step 11: LangGraph 面试表达

Step 11 新增了最小 `LangGraph StateGraph` demo：`POST /agent/langgraph_workflow_preview`。

可以这样讲：

> 我先在 Step 10 用普通 Python service 串出 workflow baseline，确认业务节点和只读边界。Step 11 再把同一条链路迁移到 LangGraph StateGraph，用 State 承载 application、HR message、job_match、hr_reply 和 approval 状态，用 Node 表达每个业务步骤，用 Conditional Edge 处理 profile 或 application 缺失的错误分支。

重点表达：

- LangGraph 版本复用已有 service，不重写业务逻辑。
- `job_match` 和 `hr_reply` 都以 `update_application=False` 运行，保证 workflow preview 不写数据库。
- `require_user_approval_node` 总是设置 `approval_required=true`、`approved_by_user=false`。
- 当前是最小 demo，没有 LLM、RAG、Playwright、真实招聘平台和自动发送。

可能追问：

**Q：为什么先做普通 Python workflow，再做 LangGraph？**  
A：先用普通 Python baseline 验证业务链路和 safety boundary，再迁移到 LangGraph，更容易保证行为一致，也方便对比两种实现。

**Q：LangGraph 版本和 Step 10 版本有什么区别？**  
A：业务能力相同，都是只读预览；区别是 Step 11 用 `StateGraph` 显式表达 State、Node、Edge 和 Conditional Edge，更适合后续扩展复杂分支和 Human-in-the-loop。
## Step 11.5: LangGraph observability 面试讲法

可以这样讲：

> 普通 Python workflow 和 LangGraph workflow 的业务结果接近，但 LangGraph 版本额外暴露了图结构、状态快照和边决策。`graph_structure` 展示 Node / Edge / Conditional Edge，`state_snapshots` 展示每个关键 Node 后 state 如何变化，`edge_trace` 展示本次请求实际走过的路径。这能更直观地说明我不是只写了一个顺序函数，而是在用 StateGraph 表达 Agent 编排。

重点强调：

- `graph_structure` 展示编排设计。
- `state_snapshots` 展示状态流转。
- `edge_trace` 展示条件分支和执行路径。
- `require_user_approval_node` 是 Human-in-the-loop 停止点。
- 当前仍不调用 LLM、不写数据库、不自动发送、不自动投递。
## Workflow / LangGraph 阶段总结入口

更完整的 Workflow / LangGraph 阶段总结见 [workflow_langgraph_summary.md](workflow_langgraph_summary.md)。面试复习时可以先读该总结，再回到本文件挑选适合自己的表达。
## Step 12: JD parsing 面试说法

Step 12 做的是 rule-based JD parsing baseline，用来提升手动录入 application 的数据质量。

可以这样介绍：

> 我在 applications 模块中加入了岗位来源标准化和 JD 轻量解析。创建或更新 application 时，系统会基于本地规则生成 source_type、jd_summary、jd_keywords、jd_required_skills、年限要求、地点要求和远程类型。这些字段可以帮助求职者侧快速筛选岗位，也能给后续 job_match 和 workflow preview 提供更规范的岗位上下文。

需要强调边界：

- 这不是语义理解，只是规则关键词抽取。
- 不是招聘决策，不代表录用概率。
- 不调用 LLM，不做 RAG / Embedding。
- 不抓取岗位，不连接真实招聘平台。
- 不自动投递，不自动发送 HR 消息。
## Step 13: Application Review / Follow-up Decision

Step 13 新增的是 rule-based application review，不是重新实现一套 `job_match`。它先复用已有 `job_match` 结果，再结合 application 状态、JD 解析字段、HR intent、风险词和缺失信息，给出下一步是否优先跟进、谨慎确认或暂缓投入的建议。

面试中可以这样表达：

- 我把岗位匹配和跟进决策拆开：`job_match` 负责基础匹配评分，`application_review` 负责综合当前投递状态和 HR 上下文给出 follow-up 建议。
- 这一层先用 rule-based baseline，是为了让评分依据可解释，方便调试和面试展示。
- 我在返回里加入了 `confidence` 和 `evidence`：`confidence` 表示规则证据充分程度，不是模型概率；`evidence` 用来说明每个结论背后的来源，比如 JD 关键词、HR 消息风险词、job_match 分数或 application status。
- 当前不调用 LLM，不做 RAG / Embedding，不连接招聘平台，也不会自动发送 HR 消息或自动投递。
- 未来如果接 LLM enhanced review，也只能参考 `llm_ready_context`、`confidence` 和 `evidence`，不能把规则推断当作事实，并继续保持 Human-in-the-loop。

## Step 14: LLM Enhanced Application Review

Step 14 的表达重点：

- LLM 不从零判断岗位，而是基于规则版 `review_score`、`review_level`、`confidence`、`evidence` 做解释增强和查漏补缺。
- Prompt 明确要求区分原始事实、规则推断和 LLM 建议，避免把规则推断说成事实。
- 没有 API key 时接口不会崩溃，会返回 `rule_review` 和 `llm_used=false / api_key_missing`。
- 即使 LLM 返回增强分析，也不自动发送 HR 消息、不自动投递、不自动确认面试、不自动修改状态，最终仍然 Human-in-the-loop。
