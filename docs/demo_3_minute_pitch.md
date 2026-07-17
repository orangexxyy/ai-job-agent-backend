# AI Job Agent 3 分钟项目讲法

## 可直接练习的版本

AI Job Agent 是一个面向 AI 应用开发求职场景的 Human-in-the-loop 后端 Demo。它不做自动海投，也不连接真实招聘平台，而是把候选人事实、岗位信息、HR 消息、风险判断、回复候选和人工确认组织成一条可解释的受控型 Agent Workflow。

我先解决事实源问题。`candidate_profile` 保存简历事实、项目上下文、truth boundaries 和用户已确认的求职偏好；`applications` 保存岗位、JD、来源和流程状态；面试可用时间单独用 slots 管理。这里我明确区分：JD 是岗位要求，profile 才是候选人事实，LLM 不能把岗位要求改写成候选人经历。

在决策链上，系统先识别 HR 消息意图，再通过规则版 Automation Policy 结合 application 和 candidate profile 判断风险。比如最低薪资、外包驻场、单休加班、隐私材料和面试时间都不能只靠关键词或让模型自行决定。Agent Loop 根据风险生成下一步计划；满足条件时只生成 `reply_candidate`，最后还要经过 Final Send Gate 检查现实承诺和敏感动作。

Step 30A 进一步把求职偏好做成可动态维护的事实源。前端 Candidate Preference Form 只允许更新薪资、城市、外包、驻场、远程、工作制、出差和隐私材料等白名单字段，保存前重新读取完整 profile，避免覆盖简历和项目事实。明确偏好可以生成礼貌拒绝、进一步确认或薪资范围说明；偏好为空或选择“我自己回答”时不生成候选。

这里最重要的边界是：候选文本不是发送授权。薪资在期望范围内也只表达可以继续沟通，不直接说接受；面试时间只引用 available slot，不自动确认；身份证、银行卡等材料只提示先核实公司、用途和渠道，再由用户决定是否手动提供。敏感候选始终要求人工审核，`auto_send_simulated=false`、`external_action_performed=false`，不会自动投递、发送 HR 消息或确认面试。

测试上，我用 API smoke test 和 Demo runner 覆盖低、中、高风险及 blocked 场景，也覆盖明确偏好、空偏好、自己回答、薪资底线、外包驻场、单休、隐私材料和 available slot。Action History 只记录内部状态或模拟结果，不是生产级 audit log。

这个项目想展示的不是一个完全自主 Agent，而是我能把 FastAPI、SQLite、规则 baseline、LLM 只读增强、LangGraph workflow preview、事实源治理、风险策略和 Human-in-the-loop 边界组合成一条真实、可测试、可解释的 AI 应用工程链路。

## 讲解节奏提示

- 前 30 秒：项目定位、解决的问题、明确不是自动海投。
- 30–90 秒：事实源、风险判断和 Agent Workflow 主链。
- 90–135 秒：重点讲 Step 30A 的偏好白名单与回复候选。
- 135–165 秒：讲 Final Send Gate、测试矩阵和外部动作边界。
- 最后 15 秒：总结技术价值，并承认当前仍是本地 Demo。

## 必须保持真实的边界

- LangGraph 是 workflow preview，不是带 checkpoint / interrupt / resume 的生产编排。
- LLM enhance 是可选只读增强，不替代规则结论，也不是事实来源。
- Action History 是轻量内部记录，不是多用户、不可篡改的生产审计。
- 当前没有生产级鉴权、多租户、版本回滚、Playwright 或真实招聘平台接入。
- 当前不能自动投递、自动发送 HR 消息、自动确认面试或上传隐私材料。
