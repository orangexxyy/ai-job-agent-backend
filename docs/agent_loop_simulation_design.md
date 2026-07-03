# Agent Loop Simulation Design

## 为什么 Step 20 才开始有 Agent 感

前置步骤分别建立了事实源、状态、规则复盘、Human-in-the-loop、action history 和 automation policy。Step 20 才能把这些能力串成 observe → classify → policy → plan 的单轮闭环，而不是让 LLM 直接决定现实动作。

## 单轮流程

1. observe：只读 application、candidate_profile、available slots 和最近 action history。
2. classify intent：规则识别项目、学历、隐私材料、薪资、外包、加班、面试和平台验证等意图。
3. propose action：把 intent 映射到现有 proposed_action_type。
4. evaluate policy：调用 Step 19A evaluator，结合候选人偏好判断风险与确认要求。
5. plan：返回模拟下一步、回复策略和只读 tool plan。

## 与 Step 18 / 19 的关系

Step 18 action history 提供最近关键动作的观察上下文；Step 19 automation policy 决定拟议动作能否内部处理、是否需要确认或必须阻断。Simulation 本身不新增 history。

## 为什么不写数据库或执行外部动作

当前目标是验证决策链路和安全边界，不是执行 Agent。所有 tool plan 都标记无数据库写入、无外部动作；不会调用 confirm reply、book slot、LLM 或招聘平台。

## 后续 supervised agent

后续可把 policy 作为每个候选动作的前置节点，引入 checkpoint、用户审批和受控执行器。只有明确批准且平台能力合法接入后，才讨论真实动作；高风险承诺继续 Human-in-the-loop。
