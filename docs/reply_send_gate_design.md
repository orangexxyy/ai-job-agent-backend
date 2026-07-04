# Step 22 Final Reply Send Gate Simulation

## 定位

`POST /agent/reply_send_gate/simulate` 用于模拟最终回复发送门禁。它不连接招聘平台，也不真实发送消息；`auto_send_simulated` 只表示规则允许 Agent 在项目内部完成一次模拟处理。

## 分层职责

```text
Step 20 Agent Loop -> intent / policy / plan
Step 21 Auto Reply -> read-only reply_candidate
Step 22 Send Gate -> final safety check / decision / simulated history
```

Step 22 不改变 Step 21 的只读性质。只有门禁判断为 `auto_send_simulated` 或 `notify_and_auto_send_simulated` 时，Step 22 才写入一条 `auto_reply_simulated_sent` action history。

## 最终文本检查

门禁检查薪资、工作条件、隐私材料、offer / 入职 / 合同和平台操作风险。命中平台操作表达时 blocked；其他承诺表达进入用户确认。门禁失败时不会写“已模拟发送”历史。

## 决策枚举

- `auto_send_simulated`
- `notify_and_auto_send_simulated`
- `requires_user_confirmation`
- `blocked`
- `no_reply_available`

## Action History

通过门禁时写入 `action_type=auto_reply_simulated_sent`、`action_source=agent`、`user_confirmed=false`、`external_action_performed=false`。application 状态和 next_action 前后保持一致。

history 用于解释内部模拟结果，不是外部发送回执。Step 22 不修改 application，不 book slot，不调用 LLM，不上传附件，也不执行招聘平台操作。

## Human-in-the-loop 边界

薪资、工作条件、隐私材料、offer、合同和其他现实承诺仍由用户决定。即使低风险候选文本通过门禁，本项目也只记录 simulated send，不会真实发送。`external_action_allowed` 和 `external_action_performed` 始终为 false。
