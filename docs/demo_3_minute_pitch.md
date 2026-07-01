# AI Job Agent 3 分钟项目讲法

## 项目定位

AI Job Agent 是一个面向 AI 应用开发求职场景的 Human-in-the-loop 后端 Demo。它不是自动海投或自动招聘系统，目标是把候选人事实、岗位信息、HR 消息、回复草稿和跟进状态组织成一条可解释、可人工确认的流程。

## 真实业务问题

真实求职中，简历事实、项目资料、JD、HR 消息和投递状态通常分散在多个地方。直接让 LLM 生成回复容易出现三个问题：把 JD 要求当成候选人经验、混淆不同项目技术栈、把草稿建议直接变成现实承诺。面试时间也是现实承诺，不能让模型随意编造。

## 核心流程

项目先用 `candidate_profile` 管理 `resume_text`、`project_context` 和 `truth_boundaries`，作为 HR 回复的事实源；再用 `applications` 记录公司、岗位、JD、来源和状态。JD 会经过规则解析，提取关键词、技能、年限、地点和工作方式等字段。

在分析层，`job_match` 和 `application_review` 先提供可解释的规则 baseline，返回 score、confidence 和 evidence。需要增强说明时，可以调用独立的 LLM enhanced review，但 LLM 只负责表达和查漏补缺，不负责创造事实。

在回复层，当前主流程使用 `/application_review/hr_reply_draft` 生成回复策略和 HR 草稿。这个接口保持只读，不修改 application，也不发送消息。用户人工审核并自行处理后，再调用 `confirm_hr_reply` 把 application 更新为 `hr_replied`。Step 17 只覆盖这一条 HR 回复确认闭环，不是通用 approval 系统。

## 关键工程设计

第一是事实源治理：JD 代表岗位需求，candidate profile 才是候选人事实源，LLM 不是事实来源。

第二是状态与副作用分离：生成草稿和写状态是两个动作，避免 AI 建议直接变成现实动作。

第三是面试时间结构化：`interview_availability_slots` 维护 available、held、booked、expired 状态，草稿只引用 available 时间，用户确认后再标记 booked。

第四是 LangGraph workflow preview：通过 Node、Edge、State、`node_debug`、`edge_trace` 和 `state_snapshots` 展示编排与可观测性，并停在 Human-in-the-loop 审批边界。

第五是 API surface 治理：Swagger 区分当前主流程、Legacy 和 Preview 接口，旧接口保留兼容但不作为 Demo 主入口。

## 安全边界

当前系统不自动发送 HR 消息、不自动投递、不自动确认面试，也不连接 Boss、邮箱、微信、飞书或外部日历。LangGraph 仍是 workflow preview，没有生产级 checkpoint / resume；项目也没有通用 audit log、MCP server 或 automation_policy。

## 后续扩展

下一步可以先补轻量 action history / audit log，再做 LangGraph checkpoint / persistence demo 和 MCP read-only server。更后面才考虑 automation_policy，并且薪资、到岗、面试、offer 和外部发送等高风险动作仍然需要人工确认。

这个项目希望展示的重点不是“功能很多”，而是我能把事实源、规则 baseline、LLM 增强、状态流转、可观测性和 Human-in-the-loop 安全边界组合成一条真实可解释的 AI 应用工程链路。
