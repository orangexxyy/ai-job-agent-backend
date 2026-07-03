# Automation Policy Evaluator Design

## 为什么需要

Automation Policy 在未来 Agent Loop 执行动作前，先判断风险、Agent 权限、用户确认和通知要求。Agent 可以生成或分析，不等于可以真实发送、投递或操作平台；当前 `external_action_allowed` 始终为 false。

## 风险等级

- low：项目介绍、技术栈等非承诺内容，可内部生成草稿。
- medium：面试时间提议、booking slot、关闭机会等内部状态动作，需要通知或确认。
- high：薪资、外包驻场、offer、到岗、合同、隐私资料、真实投递和外部发送，必须人工确认。
- blocked：验证码、平台验证、自动登录、批量投递、绕过风控。以 `risk_level=high`、`block_external_action` 和 `blocked_by` 表达。

优先级为 `blocked > high > medium > low`。

## 支持动作

`generate_hr_reply_draft`、`send_hr_reply`、`propose_interview_slots`、`book_interview_slot`、`apply_job`、`close_application`、`handle_platform_verification`。

## 与 Action History 和 Agent Loop 的关系

Step 18A 记录真正发生的关键内部状态变化。Step 19A 只评估策略，不默认写 action history，避免产生预判噪声。Step 20 可增加 `automation_policy_node`，在候选动作前调用 evaluator；真正被采纳的动作才适合记录 history。

## 当前边界

- 纯规则，不调用 LLM。
- 不写数据库或 action history。
- 不改变 HR draft、confirm reply、book slot 或 LangGraph preview 行为。
- 不发送、不投递、不确认面试、不登录招聘平台。
- 不处理验证码或绕过平台限制。

## Candidate Preference Guardrails

Automation Policy 不仅判断 HR 消息关键词，还会在有 `application_id` 时只读加载 application 和 candidate_profile，把薪资、城市、外包、驻场、远程、加班、出差和岗位方向偏好作为策略边界。

当前规则可标记 `below_minimum_salary`、`salary_at_minimum`、`salary_below_expected`、`single_day_off`、`overtime_risk`、`outsourcing_risk`、`onsite_risk`、`relocation_risk`、`city_not_acceptable`、`remote_policy_conflict` 和 `role_mismatch`。硬偏好冲突优先于普通 HR 关键词，并返回 `recommend_close_or_confirm` 或要求用户确认；系统不会自动关闭岗位。

面试表达：

> 我没有只按 HR 消息关键词判断风险，还把 candidate_profile 中的求职偏好作为策略边界。例如低于最低薪资、单休、外包驻场、城市不匹配这类条件，即使 HR 问得很普通，也会被 policy 标记为 medium/high risk，并要求用户确认。这样 Agent 后续自动化时不会为了推进流程而忽略候选人的真实底线。
