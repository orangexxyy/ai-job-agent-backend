# Application Action History Design

## 1. 目标

`application_action_history` 用于记录 AI Job Agent 内部发生过的关键系统动作和状态变化，为后续 Agent Loop、automation policy 和问题排查提供最小可追踪基础。

当前只接入三类动作：

- `application_created`
- `hr_reply_confirmed`
- `interview_slot_booked`

它不是完整 approval system，不是合规审计系统，也不替代招聘平台聊天记录。

## 2. 为什么 notes 不够

`applications.notes` 适合保存人工备注和简短上下文，但无法稳定回答：谁触发了动作、动作前后状态是什么、是否由用户确认、是否发生外部副作用。把所有事件继续追加到 notes，也不利于按 action type 查询和后续 Agent Loop 排障。

action history 使用结构化字段记录动作类型、来源、状态前后值、确认标志和外部动作标志；`detail_json` 只保存必要辅助信息。

## 3. 数据结构

表名：`application_action_history`

核心字段：

- `application_id`：可空；slot booking 未绑定 application 时允许为空。
- `action_type`：当前动作类型。
- `action_source`：当前使用 `user`，预留 system / llm / rule_engine / test。
- `before_status / after_status`：动作前后的状态。
- `before_next_action / after_next_action`：动作前后的下一步动作。
- `user_confirmed`：是否有明确用户确认。
- `external_action_performed`：当前强制为 false。
- `risk_level`：当前使用 low / medium。
- `summary`：简短动作摘要。
- `detail_json`：精简 JSON 辅助信息。
- `created_at`：UTC ISO 时间。

## 4. 隐私和内容控制

- application 创建记录不保存完整 `jd_text`，只保存公司、岗位、来源类型和少量 JD keyword preview。
- HR 回复确认只保存最多 120 字 preview 和 SHA-256 hash，不把 action history 当作完整聊天记录。
- slot booking 只保存 slot id、日期、时间、时区和短备注。
- 不保存真实简历原文、API key、`.env`、LLM 思考过程或完整 HR 聊天。

## 5. 三类动作

### application_created

用户通过 API 手动创建投递记录后写入。`before_status=null`，`after_status` 为创建状态，`user_confirmed=true`，`external_action_performed=false`。

### hr_reply_confirmed

仅在 `confirm_hr_reply` 首次实际更新 application 后写入。记录状态和 next_action 前后值、发送渠道、草稿 preview/hash、HR message preview 和 note preview。重复确认返回 `already_confirmed=true` 时不重复写入。

这只代表用户确认回复已人工处理，不代表系统发送了 HR 消息。

### interview_slot_booked

用户把 available / held slot 标记为 booked 后写入。请求带 `application_id` 时关联对应 application；否则历史记录的 application_id 为空。

booking 只是内部时间占用标记，不连接真实日历，也不自动确认面试。

## 6. 查询接口

`GET /applications/{application_id}/action_history`

- 只读查询。
- 按 id 倒序返回。
- `limit` 默认 50，最大 100。
- 不修改 application。
- 不代表任何外部动作已经执行。

## 7. 当前边界

- 不是完整 approval log。
- 不是完整 audit compliance。
- 不记录所有 application PATCH。
- 不记录完整聊天或 LLM chain-of-thought。
- 不自动发送、不自动投递、不自动确认面试。
- 当前 `external_action_performed` 必须始终为 false。

## 8. 后续演进

Step 19A 只做策略判断，不默认写 action history；后续 Agent Loop 中真正被采纳的 policy decision 才适合记录。

- 增加更多受控 action type 和统一 action context。
- 为 Step 19 automation_policy 提供风险等级、确认要求和允许动作的历史依据。
- 为 Step 20 Agent Loop / checkpoint 提供失败排查、重复动作检测和状态恢复线索。
- 如果进入生产场景，再单独设计事务一致性、审计留存、权限、脱敏和合规策略。
## Step 22: auto_reply_simulated_sent

Step 22 通过最终回复门禁时新增 `auto_reply_simulated_sent`。该动作表示 Agent 在内部完成一次模拟发送决策，不是外部平台发送回执：`action_source=agent`、`user_confirmed=false`、`external_action_performed=false`，且 application 状态和 next_action 前后保持一致。确认型、blocked 和无候选回复场景不写该动作。
