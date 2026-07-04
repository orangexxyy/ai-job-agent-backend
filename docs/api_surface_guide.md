# API Surface Guide

本文档用于说明 AI Job Agent 当前 Demo 的推荐 API 主流程，并区分主流程接口、Legacy 兼容接口和 Debug / Preview 接口。Swagger 中的 summary / description 使用中英文双语，方便项目演示和面试阅读。

当前主流程的实测结果见 [Mainline Acceptance Report](mainline_acceptance_report.md)。

## 当前 Demo 推荐顺序

1. `GET /profile`：读取候选人档案 / Read candidate profile
2. `POST /applications`：创建投递记录 / Create application record
3. `GET /applications/{application_id}/action_history`：确认 application_created 已记录 / Verify application_created history
4. `POST /application_review`：规则版岗位复盘 / Rule-based application review
5. `POST /application_review/hr_reply_draft`：生成带 application 上下文的 HR 回复草稿 / Generate HR reply draft with application context
6. `POST /applications/{application_id}/confirm_hr_reply`：用户确认已人工处理回复后更新内部状态 / Confirm HR reply and update application state
7. `GET /applications/{application_id}/action_history`：确认 hr_reply_confirmed 已记录 / Verify hr_reply_confirmed history
8. `POST /interview_availability_slots`：创建可用面试时间段 / Create interview availability slot
9. `POST /interview_availability_slots/{slot_id}/book`：用户确认后锁定内部时间段 / Book interview slot after user confirmation
10. `POST /agent/langgraph_workflow_preview`：预览 LangGraph 工作流状态 / Preview the LangGraph workflow

如果尚未保存候选人档案，应先调用 `POST /profile`。列表查询、单条查询和手动维护可以配合使用 `GET /applications`、`GET /applications/{application_id}`、`PATCH /applications/{application_id}` 和 `GET /interview_availability_slots`。

## 接口分层

### 主流程接口

主流程接口是面试 Demo 和后续维护时优先使用的业务入口：

| API | 中文说明 | English |
| --- | --- | --- |
| `GET /profile` | 读取候选人档案 | Read candidate profile |
| `POST /profile` | 保存候选人档案 | Save candidate profile |
| `POST /applications` | 创建投递记录 | Create application record |
| `GET /applications` | 查询投递记录列表 | List application records |
| `GET /applications/{application_id}` | 查询单个投递记录 | Get application record |
| `PATCH /applications/{application_id}` | 更新投递记录 | Update application record |
| `GET /applications/{application_id}/action_history` | 查询投递记录的关键动作历史 | List action history for one application |
| `POST /application_review` | 规则版岗位复盘 | Rule-based application review |
| `POST /application_review/llm_enhance` | LLM 增强岗位复盘 | LLM-enhanced application review |
| `POST /application_review/hr_reply_draft` | 生成 HR 回复草稿（当前主流程） | Generate HR reply draft with application context |
| `POST /applications/{application_id}/confirm_hr_reply` | 用户确认 HR 回复后更新内部状态 | Confirm HR reply and update application state |
| `POST /interview_availability_slots` | 创建可用面试时间段 | Create interview availability slot |
| `GET /interview_availability_slots` | 查询可用面试时间段 | List interview availability slots |
| `PATCH /interview_availability_slots/{slot_id}` | 更新面试时间段状态 | Update interview availability slot |
| `POST /interview_availability_slots/{slot_id}/book` | 用户确认后锁定面试时间段 | Book interview slot after user confirmation |
| `POST /agent/langgraph_workflow_preview` | LangGraph 工作流预览 | LangGraph workflow preview |

`POST /application_review/hr_reply_draft` 只生成草稿，不自动发送 HR 消息，也不修改 application 状态。用户人工审核并自行处理后，才调用 `confirm_hr_reply` 记录内部状态。

`confirm_hr_reply` 当前仅覆盖 HR 回复确认后的 application 状态更新，不应理解为通用 action approval、完整 approval log 或完整 audit log。

`GET /applications/{application_id}/action_history` 是当前主流程的只读辅助查询接口，用于追踪 `application_created`、`hr_reply_confirmed` 和 `interview_slot_booked`。其中 `external_action_performed` 当前始终为 false；该接口不等同完整 approval log 或 audit compliance。

### Legacy 接口

Legacy 接口保留是为了兼容早期测试和调用方式，不建议作为当前 Demo 主入口：

| API | 定位 | 当前替代入口 |
| --- | --- | --- |
| `POST /hr/analyze` | 旧版 HR 意图分析接口 / Legacy HR intent analyzer | `POST /application_review` |
| `POST /hr/reply` | 旧版 HR 回复草稿接口 / Legacy HR reply draft generator | `POST /application_review/hr_reply_draft` |
| `POST /agent/workflow_preview` | 旧版普通 Python workflow preview | `POST /agent/langgraph_workflow_preview` |

这些接口没有删除，Swagger 中使用 `deprecated=true` 和双语说明标记其兼容定位。

### Debug / Preview 接口

`POST /agent/langgraph_workflow_preview` 用于展示 node、edge、state、`node_debug`、`edge_trace`、`state_snapshots` 和 Human-in-the-loop 审批边界。它是 workflow preview，不代表系统执行了真实外部动作。

`POST /job_match` 可作为规则匹配调试和解释接口使用，但当前 Demo 主线通常通过 `application_review` 复用其结果。

## 安全边界

- 不自动发送 HR 消息。
- 不自动投递。
- 不自动确认面试。
- 不连接 Boss、邮箱、微信或飞书。
- 草稿生成不修改 application 状态。
- 状态更新必须来自用户明确调用确认接口。
- `safe_to_send=true` 不是“系统已发送”的证明。
- workflow preview 不是自动执行 workflow。

## Step 19A Automation Policy

`POST /agent/automation_policy/evaluate` 是当前 Agent 主线辅助接口，只返回 low / medium / high / blocked 策略判断，不执行动作、不写 action history。`external_action_allowed` 始终为 false。

传入 `application_id` 时，evaluator 会只读结合 application 条件和 candidate_profile 的薪资、城市、外包驻场、远程、加班等偏好，返回 `preference_risk_flags`；不会返回 profile 原文。

## Step 20 Agent Loop Simulation

`POST /agent/loop/simulate` 是当前 Agent 主线接口。它只读观察 application、profile、available slots 和 action history，识别 intent、调用 automation policy 并返回模拟计划；不写数据库、不 book slot、不调用 LLM 或外部平台。

## Swagger 阅读建议

- 优先查看 `profile`、`applications`、`application_review`、`interview_availability_slots` 和 `agent` 分组。
- `hr` 分组是 Legacy 接口，不作为当前主流程。
- Swagger 的 Deprecated 标记表示不推荐作为新调用入口，不表示接口已经删除或不可用。

## Step 21 Supervised Auto Reply Simulation

`POST /agent/auto_reply/simulate` 是只读模拟接口。它复用 Step 20 的 intent、policy 和 plan，只在低风险内部处理或 available slot 建议场景生成规则版 `reply_candidate`。中高风险场景停在用户确认，平台自动化场景被阻断；接口不调用 LLM、不写库、不执行外部动作。
## Step 22 Final Reply Send Gate Simulation

`POST /agent/reply_send_gate/simulate` 复用 Step 21，并增加最终文本检查和门禁决策。只有 low，或无需确认的 medium 场景通过检查后，才记录 `auto_reply_simulated_sent` history。该接口会写内部 history，但不修改 application、不 book slot、不调用 LLM，也不执行真实发送或平台操作。
