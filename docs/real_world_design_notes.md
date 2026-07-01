# Real World Design Notes

本文档用于沉淀 AI Job Agent 与配套 RAG 项目中更接近真实企业开发的问题拆解和设计取舍。它不是 API 文档，也不是 README 的功能清单，而是面试时解释“为什么这样设计”的复习材料。

## 总说明

这个项目的目标不是单纯堆 Demo 功能，而是模拟 AI 应用开发 / 大模型应用开发岗位中常见的工程设计问题：事实来源怎么治理、业务状态怎么流转、LLM 不能做什么、哪些动作必须 Human-in-the-loop。

每个功能都应该能回答这些问题：

- 解决什么真实业务问题
- 为什么不能简单粗暴地做
- 业务数据有什么特点
- 当前方案怎么设计
- 边界和风险是什么
- 怎么测试验收
- 面试时怎么表达

## 案例一：RAG 项目的规则型 chunk 设计

> 说明：这个案例来自配套的 RAG 企业知识库项目，用来说明 RAG 业务资料处理思路；不要理解为当前 AI Job Agent 已经实现 RAG / Embedding / 向量检索。

### 真实业务问题

企业制度、报销规则、请假规则、医药 SOP 这类资料，经常不是普通散文式段落，而是一条条可执行的业务规则。一条规则本身就是一个完整业务判断单元，里面可能同时包含适用场景、金额区间、审批人、例外条件和处理流程。

如果检索只命中规则的一半，回答就可能漏掉关键条件。例如报销制度里只命中“可报销金额”，但漏掉“需要部门负责人审批”；或医药 SOP 里只命中操作步骤，却漏掉适用人群和禁忌条件。

### 简单做法的问题

普通段落切分、固定长度 chunk、固定 overlap 并不适合所有文档。它们容易把完整规则切断，导致：

- 检索结果只包含部分条件
- Reranker 看到的是不完整证据
- LLM 基于残缺上下文生成看似合理但实际缺条件的回答
- 回答中漏审批人、漏金额区间、漏处理条件

### 当前设计

在配套 RAG 项目中，规则型资料应该优先按业务语义识别 chunk 边界，而不是只按文本长度切分。对于企业规则类、制度类、SOP 类文档，可以结合以下信号尽量保证一条规则完整进入一个 chunk：

- 规则编号，例如 `1.1`、`第 3 条`、`SOP-001`
- 标题和小标题
- 关键词，例如“适用范围”“审批流程”“报销标准”“注意事项”
- 金额区间，例如“500 元以下”“5000 元以上”
- 适用场景，例如“差旅报销”“病假申请”“药品入库”

metadata 可以包含：

- `rule_id`
- `category`
- `amount_range`
- `source`

这个设计体现的是：根据业务语义决定 chunk 边界，而不是只按文本长度切分。

### 边界和风险

- 规则型 chunk 不等于所有文档都按规则切分，普通说明文档仍可使用段落或长度策略。
- 规则编号和标题识别可能不完美，需要保留人工抽查和测试集。
- metadata 是检索和解释的辅助信息，不应该被写成不存在的业务事实。
- 该设计属于 RAG 项目能力，不属于当前 AI Job Agent 的已实现能力。

### 测试验收

- 准备包含金额区间、审批人、例外条件的规则型测试文档。
- 检查 chunk 是否保留完整制度条款。
- 用问题命中规则，观察返回上下文是否包含完整判断条件。
- 对比固定长度切分与规则级切分的回答完整性。
- 重点检查是否漏掉审批人、金额区间、适用场景和限制条件。

### 面试表达

“我没有简单使用固定长度 chunk，而是针对企业规则类资料做了规则级切分，尽量保证一条制度条款完整进入一个 chunk，避免因为 chunk 被切断导致检索结果缺失关键条件。这里体现的是根据业务语义设计 chunk 边界，而不是只按 token 长度处理文档。”

## 案例二：AI Job Agent 的 candidate_profile 事实源治理

### 真实业务问题

HR 回复草稿不能直接依赖 JD 或 LLM 自己发挥。JD 只能代表岗位需求，不能证明候选人已经实现过某项技术；LLM 擅长生成表达，但不应该被当作事实来源。

在求职场景里，一旦把未实现能力写进 HR 回复，就会造成面试风险。例如把岗位要求中的 RAG 写成候选人项目经验，或把后续规划写成已经落地的功能。

### 简单做法的问题

简单把 JD、README、聊天上下文全部丢给 LLM 生成回复，会带来几个问题：

- 把 JD 技术要求误写成候选人能力
- 把不同项目技术栈混在一起
- 把未来规划说成已实现能力
- 把 Demo 项目夸大成企业级生产系统
- 生成对外承诺，但没有 Human-in-the-loop 确认

典型错误包括：

- 把 RAG 项目说成用了 LangGraph
- 把 AI Job Agent 当前说成已实现 RAG / Embedding / 向量检索
- 把未实现规划说成已实现能力

### 当前设计

AI Job Agent 把 `candidate_profile` 作为 HR 回复草稿的主要事实源，并通过以下字段约束生成边界：

- `resume_text`：候选人对外简历事实
- `project_context`：按项目分段的项目事实和可展开内容
- `truth_boundaries`：不能夸大的能力、不能混淆的技术栈、不能自动承诺的动作

事实源层级如下：

- JD = 岗位需求
- 简历 = 候选人对外事实
- `candidate_profile` = HR 回复事实源
- README / GitHub = 项目技术事实参考
- LLM = 生成表达，不是事实来源

README / GitHub 项目资料可以用于帮助更新简历和 `candidate_profile`，但 HR 对外回复应优先以简历和 `candidate_profile` 为准。JD 只能提供岗位关注点，不能作为“我已经做过某技术”的依据。

### 边界和风险

- 当前系统生成的是 HR 回复草稿，不自动发送 HR 消息。
- `candidate_profile` 内容需要用户人工维护和确认，不能由系统擅自写入真实经历。
- LLM enhanced review 只能参考规则结果和事实源，不能把推断当作事实。
- 不能把 AI Job Agent 写成已实现 RAG / Embedding / 向量检索。
- 不能把 Demo 项目写成企业级生产系统。

### 测试验收

- 准备包含岗位要求但候选人未实现能力的 JD，检查回复是否避免把 JD 当作个人经验。
- 准备包含 RAG 和 LangGraph 的项目上下文，检查是否保持项目边界。
- 检查 HR 项目介绍是否优先引用 `resume_text` 和 `project_context`。
- 检查 `truth_boundaries` 中禁止表达是否没有出现在最终草稿中。
- 检查系统是否只生成草稿，不触发外部发送。

### 面试表达

“我把 candidate_profile 作为 HR 回复的事实源，里面包含 resume_text、project_context 和 truth_boundaries。JD 只作为岗位关注点，不作为候选人能力事实来源，避免 LLM 把岗位要求或未来规划说成已实现经验。这个设计本质上是事实源分层：LLM 负责表达，不负责创造事实。”

## 案例三：AI Job Agent 的 interview_availability_slots 状态管理

### 真实业务问题

面试时间不能让 LLM 自己编。面试时间属于现实承诺，一旦发送给 HR，就可能影响候选人和企业双方日程。如果系统随便生成“明天下午可以”，但用户实际没空，就会造成外部沟通风险。

因此，面试时间类回复必须从用户明确提供的可用时间中读取，并且后续状态要可追踪。

### 简单做法的问题

如果让 LLM 根据 HR 消息直接生成面试时间，可能出现：

- 编造不存在的可用时间
- 重复推荐已经确认的时间段
- 同一时间段被重复创建，导致 booked 后仍被再次推荐
- 无法追踪草稿到底引用了哪个时间段
- 在用户未确认前形成对外承诺

### 当前设计

当前项目把可用面试时间结构化为 `interview_availability_slots`，并维护状态：

- `available`
- `held`
- `booked`
- `expired`

HR reply draft 只能读取 `status=available` 的 slots。用户确认某个面试时间后，可以把 slot 标记为 `booked`，后续草稿不再推荐该时间段。

系统还做了 duplicate slot 防重，避免同一 `date + start_time + end_time + timezone` 被重复创建，导致一个时间段已经 booked 后仍从重复记录里被推荐。`available_slots_used` 会返回 `slot_id`，方便追踪草稿到底使用了哪个可用时间。

### 边界和风险

- 当前不接 Google Calendar / 飞书日历。
- 当前不做外部日历冲突检测。
- 当前不自动发送 HR 消息。
- 当前不自动确认面试。
- booking 只是内部状态标记，不代表已经和 HR 完成确认。
- 状态流转仍需要用户人工确认，保持 Human-in-the-loop。

### 测试验收

- 创建一个 `available` slot，检查面试回复草稿是否只引用该时间段。
- 将 slot 标记为 `booked`，检查后续草稿不再推荐。
- 尝试创建重复 slot，检查是否被拒绝。
- 检查 `available_slots_used` 是否包含 `slot_id`。
- 在没有 available slot 时，检查系统是否要求用户先确认日程，而不是编造时间。

### 面试表达

“我没有让 LLM 自己生成面试时间，而是设计了 interview_availability_slots。系统只会读取 available 时间段生成草稿；用户确认后把 slot 标记为 booked，后续不会再推荐。当前不自动发送 HR 消息，也不接外部日历，后续可以扩展日历冲突检测。”

## 案例四：HR 回复确认后的状态更新

### 真实业务问题

生成 HR 回复草稿不等于用户已经发送或处理了消息。如果生成草稿时就修改 application，系统会把 AI 建议错误地当成现实动作，后续提醒和状态判断也会失真。

### 简单做法的问题

- 不能因为 LLM 返回 `safe_to_send=true` 就标记为已回复。
- 不能在草稿生成时自动修改 `status / next_action`。
- 不能由系统自动发送消息或自动确认面试。
- 不能无条件覆盖 `offer / rejected / closed` 等终态。

### 当前设计

`/application_review/hr_reply_draft` 保持只读。用户人工审核并自行处理回复后，主动调用 `POST /applications/{application_id}/confirm_hr_reply`，系统才把 application 更新为 `hr_replied`，设置下一步动作，并把确认采用的草稿、`sent_channel=manual` 和备注追加到现有 `notes`。该设计复用现有字段，没有新增数据库表或字段。

### 边界和风险

- 确认接口记录的是用户声明的人工处理结果，不代表系统实际发送了消息。
- 系统不连接 Boss、邮箱、微信或飞书。
- 系统不自动投递、不自动发送 HR 消息、不自动确认面试。
- 终态 application 返回 409，避免状态被盲目覆盖。
- 当前使用 `notes` 保存简要确认记录，还不是完整 audit log。

### 测试验收

- 对比生成草稿前后的 application，确认关键字段未变化。
- 调用确认接口后检查 `status=hr_replied`、`next_action` 和 notes 记录。
- 检查 404、空草稿 422、终态 409 和重复确认。
- 检查 debug 始终包含 `auto_send_message=false`、`auto_apply=false`、`auto_confirm_interview=false` 和 `confirmed_by_user=true`。

### 面试表达

“我把生成草稿和状态更新拆开，草稿只是 AI 建议，只有用户确认后才写 application 状态，避免 LLM 生成内容直接变成现实动作。确认接口只记录用户已经人工处理，不负责发送消息；终态也有保护，后续如果需要更完整追踪，再扩展 audit log。”

## 案例五：API Surface Governance / 接口面治理

### 真实业务问题

项目经过多轮迭代后，容易同时存在基础版、增强版和 workflow preview 接口。如果没有明确分层，Demo 使用者和后续维护者会误把旧接口当成当前主流程。

### 简单做法的问题

- 直接删除旧接口会破坏已有测试、脚本和兼容调用。
- 所有接口不加区分地暴露，会让功能边界和推荐调用顺序变得模糊。
- 只靠 README 说明，Swagger 使用者仍可能选错入口。

### 当前设计

Swagger 使用中英文 summary / description 标记接口用途，并通过 tag 区分 profile、applications、application review、interview availability、agent 和 Legacy HR 接口。`/hr/analyze`、`/hr/reply`、`/agent/workflow_preview` 保留兼容并标记 Deprecated；当前 Demo 主流程统一记录在 `docs/api_surface_guide.md`。

### 边界和风险

- Deprecated 只表示不推荐新流程使用，不代表接口已经删除。
- API surface 治理不改变底层业务逻辑或安全边界。
- workflow preview 仍然只是预览，不代表真实外部执行。

### 测试验收

- 检查 Swagger 中主流程接口是否有中英文说明。
- 检查 Legacy 接口是否显示 Deprecated 和替代入口。
- 检查 Demo 文档是否指向 `/application_review/hr_reply_draft` 和 `confirm_hr_reply`。
- 运行原有 smoke test，确认旧接口继续兼容且业务行为没有变化。

### 面试表达

“我对迭代后的接口做了 API surface 治理，区分主流程、Legacy 和 Preview 接口。旧接口没有直接删除，而是在 Swagger 标记 Deprecated 并说明替代入口，既保持兼容，也避免 Demo 或后续维护时误用旧接口。”

## 后续可继续沉淀的工程设计点

- HR intent routing：不同 HR 意图走不同回复策略。
- `application_review` 规则评分：不是让 LLM 直接判断岗位值不值得投，而是先有可解释规则 baseline。
- LangGraph workflow preview：节点、edge、state、human approval、`state_snapshots` 的可观测设计。
- LangGraph checkpoint / persistence：后续支持 `thread_id`、resume、time travel。
- MCP read-only tools：后续如果接入 MCP，应只暴露安全只读能力，不暴露自动发送和自动投递。
- JD structured parsing：把 JD 解析成 `years`、`salary`、`skills`、`location`、`remote_type` 等结构化字段。
- LLM fallback：LLM 不可用时保持保守回复，不影响核心安全流程。
