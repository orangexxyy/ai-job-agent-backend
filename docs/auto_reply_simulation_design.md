# Step 21 Supervised Auto Reply Simulation

## 定位

`POST /agent/auto_reply/simulate` 在 Step 20 Agent Loop Simulation 之上增加规则版候选回复生成。它解决的是“低风险场景能否先准备一段可审核文本”，不是自动发送系统。

## 调用链

```text
request
-> simulate_agent_loop
-> intent + automation policy + available slot preview
-> supervised reply guard
-> rule-based reply_candidate or blocked reason
```

Step 21 不复制 Step 20 的意图或风险判断。只有 `auto_handle_internal` 等低风险内部处理场景，或带 available slots 的 `propose_slots_with_notification` 场景，才可能产生 `reply_candidate`。

## 可生成场景

- 项目经验：从 `candidate_profile.available_projects / project_context` 提取有限事实，避免夸大。
- 学历和基础信息：只参考 `candidate_profile.resume_text`；不承诺提交证明材料。
- 简历或项目链接：只生成“可以提供”的候选表达，不上传或发送附件。
- 普通跟进：生成礼貌的继续沟通候选文本。
- 面试时间：只引用 `status=available` 的 slot，表述为建议时间，最终仍需双方确认。

## 必须停止的场景

薪资、外包、驻场、单休、加班、隐私材料、offer、入职和合同等现实承诺必须先由用户确认。平台验证码、自动登录、批量投递等动作直接 blocked。确认型或 blocked 场景默认不返回 `reply_candidate`，避免出现“我接受”“我马上发”等承诺。

## 安全边界

- `external_action_allowed=false`
- 不发送 HR 消息，不投递，不上传附件
- 不修改 application，不写 action history
- 不 book slot，不自动确认面试
- 不登录招聘平台，不处理验证码
- 不调用 LLM，仅使用规则模板

## 验收

`scripts/api_smoke_test.py` 覆盖项目、学历、学历证明、薪资、单休、外包驻场、面试时间和平台验证码八类场景，并比较调用前后的 application、action history 和 available slots 快照，确认模拟过程只读。
