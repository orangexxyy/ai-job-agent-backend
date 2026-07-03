# AI Job Agent 主线收口验收报告

验收日期：2026-07-01

## 1. 验收结论

**PARTIAL PASS**

当前主线 API、内部状态流转、Human-in-the-loop 安全边界、Legacy 标记和测试数据清理均通过，可以用于面试 Demo。现有 smoke test 最终结果为 41 / 41 通过。

需要保留一项展示风险：使用真实 candidate profile 进行 LLM HR reply draft 验收时，草稿同时提到了 RAG 和 AI Job Agent，但没有稳定出现“企业知识库”完整措辞。事实边界检查通过，也没有混淆 LangGraph / RAG 技术栈；该问题属于 LLM 表达稳定性，不影响接口和安全闭环，但正式 Demo 前应预览草稿或使用稳定 fallback。

## 2. 当前主流程

1. `GET /profile`：确认候选人事实源字段是否存在。
2. `POST /applications`：创建手动投递记录并解析 JD。
3. `POST /application_review`：生成规则版岗位复盘。
4. `POST /application_review/hr_reply_draft`：生成可人工审核的 HR 回复草稿。
5. `POST /applications/{application_id}/confirm_hr_reply`：用户确认已处理 / 手动发送后更新内部状态。
6. `GET /applications/{application_id}/action_history`：只读追踪关键内部动作和状态变化。
7. `POST /interview_availability_slots` 与 `/book`：维护和锁定用户确认的面试时间段。
8. `POST /agent/langgraph_workflow_preview`：展示 LangGraph node、edge、state 和人工审批边界。

## 3. 每一步解决的真实问题

- profile：解决 HR 回复事实源不稳定、项目技术栈容易混淆的问题。
- applications + JD parsing：把公司、岗位、JD、来源和跟进状态集中到一条可追踪记录中。
- application_review：先建立可解释的规则 baseline，避免让 LLM 直接凭感觉判断岗位。
- hr_reply_draft：把回复策略和 HR 草稿组织出来，同时保留人工审核。
- confirm_hr_reply：把 AI 建议与现实状态变更拆开，仅在用户确认回复已处理后写 application。
- interview slots：避免 LLM 编造可用面试时间，并防止 booked 时间段被重复推荐。
- LangGraph preview：展示显式 Node / Edge / State、可观测字段和 Human-in-the-loop 停止点。

## 4. 验收结果表

| Step | Endpoint | Result | Key Evidence | Safety Boundary |
| --- | --- | --- | --- | --- |
| 健康检查 | `GET /health` | PASS | `status=ok` | 无外部动作 |
| Candidate profile | `GET /profile` | PASS | `target_roles`、`available_projects`、`resume_text`、`project_context`、`truth_boundaries` 均存在；未记录字段原文 | 只读，不覆盖真实 profile |
| Application 创建 | `POST /applications` | PASS | 创建成功并返回 id；`jd_summary`、`jd_keywords`、`jd_required_skills`、`source_type` 存在 | 手动测试数据 |
| 规则复盘 | `POST /application_review` | PASS | 返回 score、level、confidence、evidence、missing information、risk flags | 调用前后 status / next_action 未变化 |
| HR 回复草稿 | `POST /application_review/hr_reply_draft` | PARTIAL PASS | 返回 project_intro 草稿，包含 RAG 与 AI Job Agent；事实边界和只读检查通过，但“企业知识库”措辞不稳定 | `auto_send_message=false`，不写 application |
| 回复确认 | `POST /applications/{id}/confirm_hr_reply` | PASS | `status=hr_replied`、`next_action=wait_for_hr_response`、`confirmed_by_user=true` | 不自动发送、投递或确认面试 |
| Action history | `GET /applications/{id}/action_history` | PASS | Smoke test 验证三类 action、重复确认不重复写入、查询只读 | `external_action_performed=false` |
| 面试时间创建 | `POST /interview_availability_slots` | PASS | 唯一 slot 创建成功，`status=available` | 不接外部日历 |
| 面试时间草稿 | `POST /application_review/hr_reply_draft` | PASS | `available_slots_used` 包含本轮 slot id | `auto_confirm_interview=false` |
| 面试时间锁定 | `POST /interview_availability_slots/{id}/book` | PASS | slot 更新为 booked，默认 available 列表不再返回 | 仅内部状态，不向 HR 发送消息 |
| LangGraph preview | `POST /agent/langgraph_workflow_preview` | PASS | 返回 `node_debug`、`edge_trace`、`state_snapshots`、approval 标记 | Preview，不是生产级执行引擎 |
| Legacy 标记 | OpenAPI / API Surface Guide | PASS | `/hr/analyze`、`/hr/reply`、`/agent/workflow_preview` 标记 Deprecated / Legacy | 主流程不使用 Legacy 接口 |
| 测试清理 | `PATCH /applications/{id}` | PASS | 主线验收 application `id=35` 与复核 application `id=36` 最终均为 closed | 不删除数据库记录 |

## 5. Smoke Test

首次运行暴露了 smoke test slot 日期复用问题：脚本原先使用 `timestamp % 20` 生成日期，重复运行会与数据库中已有 slot 冲突。修复测试夹具唯一性、动态断言和 duplicate slot 清理后，最终结果：

```text
Total: 41
Passed: 41
Failed: 0
```

该修改只影响测试数据生成与断言，不改变业务逻辑或数据库结构。

## 6. 安全边界检查

- 不自动发送 HR 消息。
- 不自动投递。
- 不自动确认面试。
- 不连接 Boss、邮箱、微信或飞书。
- HR reply draft 保持只读，`safe_to_send` 不代表系统已经发送。
- Step 17 仅覆盖 HR 回复确认后的 application 状态更新，不是通用 approval log。
- LangGraph 当前是 workflow preview，不是生产级 checkpoint / resume。
- 本轮没有读取或记录真实简历、profile 原文或 `docs/input/*`。

## 7. Legacy 接口

- `POST /hr/analyze`：Legacy HR intent analyzer。
- `POST /hr/reply`：Legacy HR reply draft generator。
- `POST /agent/workflow_preview`：Legacy Python workflow preview。

这些接口继续保留兼容，但当前 Demo 主流程使用 `application_review/hr_reply_draft`、`confirm_hr_reply` 和 `agent/langgraph_workflow_preview`。

## 8. 当前未实现

- 真实招聘平台接入。
- 外部消息发送。
- 通用 approval log。
- 完整 action history / approval log / audit compliance；Step 18A 当前只实现三类轻量关键动作记录。
- LangGraph checkpoint / resume / persistence。
- MCP read-only server。
- automation_policy 与 `auto_low_risk`。
- 外部日历同步和冲突检测。
- 生产级权限、多租户、监控和完整 retry policy。

## 9. 后续建议

- Step 18A：轻量 action history 已完成，当前覆盖 application_created、hr_reply_confirmed、interview_slot_booked。
- Step 18B：action 写入一致性、错误处理与 retry policy。
- Step 19：automation_policy 设计；外部发送继续默认关闭。
- Step 20：Agent Loop / LangGraph checkpoint 与 persistence demo。
- Step 21：MCP read-only server demo，只暴露安全只读能力。
