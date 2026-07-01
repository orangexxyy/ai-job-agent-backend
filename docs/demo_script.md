# Demo Script

## Step 17: 用户确认 HR 回复后的状态更新

演示目标：展示“AI 生成草稿”和“用户确认后写状态”是两个独立动作。

1. 调用 `POST /application_review/hr_reply_draft` 生成 HR 回复草稿。
2. 调用 `GET /applications/{application_id}`，确认生成草稿没有修改 `status / next_action / notes`。
3. 用户人工审核草稿，并在外部渠道自行处理或手动发送。
4. 调用 `POST /applications/{application_id}/confirm_hr_reply`，提交确认采用的 `draft_text`。
5. 再次查询 application，观察 `status=hr_replied`、`next_action=wait_for_hr_response`，以及 `notes` 中的人工确认记录。

确认请求示例：

```json
{
  "draft_text": "您好，感谢您的邀请……",
  "hr_message": "最近什么时候方便视频面试？",
  "sent_channel": "manual",
  "next_action": "wait_for_hr_response",
  "note": "用户已人工确认并手动发送给 HR"
}
```

演示时强调：确认接口只记录内部状态，不连接 Boss / 邮箱 / 微信 / 飞书，不自动发送消息，不自动投递，也不自动确认面试。

## Step 16.7B: interview availability booking demo

演示目标：

- 手动维护 `interview_availability_slots`。
- 重复的 `date + start_time + end_time + timezone` 不会被重复创建。
- `GET /interview_availability_slots` 默认只返回 `status=available`。
- HR reply draft 只引用 available slots，并在 `available_slots_used` 中返回 slot `id`。
- 用户确认后，可调用 `POST /interview_availability_slots/{slot_id}/book` 将内部 slot 标记为 `booked`。
- booked slot 不再被 HR reply draft 使用。

演示边界：

- 不发送 HR 消息。
- 不自动确认面试给 HR。
- 不自动修改 application status。
- 不接 Google Calendar / 飞书日历。
- 不做 OAuth、外部日历同步或自动冲突检测。

建议演示顺序：

1. `POST /interview_availability_slots` 创建一个 available slot。
2. 再次创建相同 slot，观察 409 Conflict。
3. 调用 `POST /application_review/hr_reply_draft`，观察 `available_slots_used[0].id`。
4. 调用 `POST /interview_availability_slots/{slot_id}/book`。
5. 再次调用 HR reply draft，确认该 booked slot 不再出现。

## 演示准备

启动 FastAPI：

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

打开 Swagger：

```text
http://127.0.0.1:8001/docs
```

运行 smoke test：

```bash
python scripts/api_smoke_test.py
```

如果本机系统 Python 缺依赖，可以使用项目虚拟环境：

```bash
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

## 推荐演示顺序

1. `GET /health`
2. `GET /profile`，如未保存则先调用 `POST /profile`
3. `POST /applications`
4. `GET /applications/{application_id}`
5. `POST /application_review`
6. `POST /application_review/hr_reply_draft`
7. 用户人工审核并自行处理回复
8. `POST /applications/{application_id}/confirm_hr_reply`
9. `POST /interview_availability_slots`
10. `POST /interview_availability_slots/{slot_id}/book`
11. `POST /agent/langgraph_workflow_preview`

当前 Demo 主流程不要使用 `/hr/reply`。该接口是 Legacy 兼容入口，当前 HR 回复草稿入口是 `/application_review/hr_reply_draft`；人工处理后再调用 `confirm_hr_reply` 更新内部状态。
14. `python scripts/api_smoke_test.py`

## 每个接口的演示目的

- `/health`：证明服务已启动。
- `/profile`：建立候选人稳定求职档案。
- `/applications`：建立具体投递上下文。
- `/job_match`：展示可解释岗位匹配评分和求职者侧优先级。
- `/hr/analyze`、`/hr/reply`：Legacy 接口，可用于兼容性说明，不作为推荐 Demo 主流程。
- `/application_review/hr_reply_draft`：展示当前主流程的 application context、回复策略和 HR 草稿。
- `/applications/{application_id}/confirm_hr_reply`：展示用户确认后才更新内部状态。
- `api_smoke_test.py`：展示主链路自动验收能力。

## 建议测试 JSON

### POST /profile

```json
{
  "expected_salary_min": 15000,
  "expected_salary_max": 20000,
  "minimum_salary": 13000,
  "salary_note": "优先考虑 AI 应用开发方向，具体薪资结合岗位职责沟通。",
  "availability_note": "一周左右可协调",
  "preferred_cities": ["杭州", "上海", "远程"],
  "acceptable_cities": ["AI 方向匹配的其他城市可沟通"],
  "relocation_policy": "长期外地驻场不优先，AI 方向强匹配可沟通",
  "outsourcing_policy": "优先正式岗位，AI 项目质量高可进一步了解",
  "onsite_policy": "正常办公室工作可接受，长期客户现场需进一步沟通",
  "remote_policy": "远程或混合办公可接受",
  "overtime_policy": "项目阶段性加班可沟通，长期高强度加班不优先",
  "business_trip_policy": "短期出差可沟通，长期频繁出差不优先",
  "target_roles": ["AI应用开发工程师", "大模型应用开发工程师"],
  "available_projects": [
    "FastAPI + RAG 企业知识库问答系统",
    "AI Job Agent 智能求职助手"
  ],
  "truth_boundaries": [
    "没有做过完整生产级智能招聘系统",
    "不会自动发送 HR 消息"
  ],
  "resume_text": "候选人做过 FastAPI + RAG 企业知识库问答系统 Demo，支持文档入库、混合检索、SQLite 会话记录。候选人也做过 AI Job Agent，用于 HR 意图识别、回复草稿和投递记录管理。",
  "project_context": "RAG 项目基于 FastAPI，支持 txt/PDF/Excel 入库、FAISS + BM25 + RRF 混合检索、reranker、low_confidence、SQLite 会话。AI Job Agent 项目支持 candidate_profile、applications、HR reply、job_match 和 API smoke test harness。"
}
```

### POST /applications

```json
{
  "company_name": "Demo AI Company",
  "job_title": "AI Application Developer",
  "job_source": "Manual",
  "job_url": "https://example.com/job/demo",
  "jd_text": "Build AI application workflows with Python, FastAPI, RAG, Agent, LLM and human approval.",
  "status": "saved",
  "next_action": "Review JD fit",
  "notes": "Manual demo record only.",
  "risk_flags": []
}
```

记下返回的 `data.id`，后续用作 `application_id`。

### POST /job_match

```json
{
  "application_id": 1,
  "update_application": true
}
```

演示重点：

- `match_score`
- `match_level`
- `dimensions`
- `risk_flags`
- `application_update_fields`

强调：这个评分是求职者侧优先级，不是招聘决策。

### POST /hr/analyze

```json
{
  "message": "你期望薪资多少？一周能到岗吗？接受外地吗？",
  "company_name": "Demo AI Company",
  "job_title": "AI Application Developer"
}
```

演示重点：

- `intents`
- `primary_intent`
- `risk_level`
- `need_profile`

### POST /hr/reply

```json
{
  "message": "你期望薪资多少？一周能到岗吗？接受外地吗？",
  "company_name": "Demo AI Company",
  "job_title": "AI Application Developer",
  "extra_context": ""
}
```

演示重点：

- `reply_draft`
- `safe_to_send`
- `truth_boundary`
- `suggested_followup`

### POST /hr/reply + application_id

```json
{
  "application_id": 1,
  "message": "方便明天下午视频面试吗？",
  "company_name": "",
  "job_title": "",
  "extra_context": ""
}
```

演示重点：

- `application_context`
- `application_updated`
- `application_update_fields.last_hr_message`
- `application_update_fields.next_action`

强调：不会自动修改 `status`，不会自动确认面试时间。

### POST /hr/reply 项目经历问题

```json
{
  "message": "你做过哪些 RAG 或 Agent 相关项目？能简单介绍一下吗？",
  "company_name": "Demo AI Company",
  "job_title": "AI Application Developer",
  "extra_context": ""
}
```

演示重点：

- `context_used`
- `selected_context_snippets`
- `context_reply_mode`
- `reply_draft`

强调：这是基于 `resume_text / project_context` 的规则片段选择，不是 RAG，不调用 LLM。

## 演示时要强调的点

- 不自动发送 HR 消息。
- 不自动投递。
- 不调用 LLM。
- 当前是规则版 baseline。
- 关键动作 Human-in-the-loop。
- `job_match` 是求职者侧优先级，不是招聘决策。
- `context enhanced reply` 不是 RAG。
- 后续可以用 LangGraph 编排这些节点。

## 演示失败排查

### 端口 8001 被占用

检查是否已有 uvicorn 进程占用端口。可以换端口，或停止旧服务后重启。

### smoke test 提示 API server is not reachable

说明 FastAPI 服务没有启动，或 `--base-url` 不对。先打开 Swagger 确认服务可访问。

### `.venv` 没激活

可以显式使用：

```bash
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

### requirements 没安装

运行：

```bash
pip install -r requirements.txt
```

### application_id 不存在

先调用 `POST /applications` 创建记录，并使用返回的 `data.id`。

### profile 未保存

先调用 `POST /profile`。如果缺少 profile，`/hr/reply` 和 `/job_match` 会返回明确错误。

### 中文显示异常

如果 PowerShell 输出中文乱码，可以优先在 Swagger 中查看 JSON 响应，或使用支持 UTF-8 的终端。
## Step 10 demo: POST /agent/workflow_preview

建议在 `POST /applications` 创建记录之后演示：

```json
{
  "application_id": 1,
  "hr_message": "方便介绍一下你做过的 RAG 或 Agent 项目吗？"
}
```

演示重点：

- `workflow_mode` 是 `rule_based_preview`
- `workflow_steps` 展示 load profile、load application、job match、HR intent、reply draft、等待用户确认
- `job_match` 来自现有规则评分能力，但 `update_application=False`
- `hr_reply` 来自现有回复草稿能力，但 `update_application=False`
- `approval_required=true` 且 `approved_by_user=false`
- `debug.llm_used=false`、`debug.langgraph_used=false`、`debug.rag_used=false`
- 不自动投递、不自动发送 HR 消息、不自动确认面试时间、不写入 application
## Step 11 demo: POST /agent/langgraph_workflow_preview

建议和 Step 10 的 `POST /agent/workflow_preview` 连续演示，用来对比普通 Python workflow 和 LangGraph StateGraph workflow。

```json
{
  "application_id": 1,
  "hr_message": "方便介绍一下你做过的 RAG 或 Agent 项目吗？"
}
```

演示重点：

- `workflow_mode` 是 `langgraph_preview`
- `workflow_engine` 是 `langgraph_stategraph`
- `workflow_steps` 对应 LangGraph nodes
- `debug.langgraph_used=true`
- `debug.llm_used=false`
- `approval_required=true`、`approved_by_user=false`
- `hr_reply.application_updated=false`
- 预览接口不写 application，不自动投递，不自动发送 HR 消息

对比讲法：

- Step 10 证明业务链路可以用普通 Python service 串起来。
- Step 11 把同一条链路迁移到 LangGraph StateGraph，显式表达 State、Node、Edge 和 Conditional Edge。
- 当前没有循环、没有 human interrupt resume，只做最小可运行 demo。
## Step 11.5 demo: LangGraph observability

演示顺序建议：

1. 先调用 `POST /agent/workflow_preview`，说明这是普通 Python workflow baseline。
2. 再调用 `POST /agent/langgraph_workflow_preview`，说明业务结果接近，但 LangGraph 版本额外暴露 workflow 编排结构。
3. 在返回结果里重点展开：
   - `graph_structure`
   - `state_snapshots`
   - `edge_trace`

讲法：

- `graph_structure` 用来展示 Node、Edge、Conditional Edge。
- `state_snapshots` 用来展示每个关键 Node 后 state 的变化。
- `edge_trace` 用来展示本次实际执行路径和条件判断。
- `require_user_approval_node` 到 `END` 的 trace 说明流程停在 Human-in-the-loop，不会自动发送或投递。
## Step 12 demo: JD 手动导入增强

演示顺序建议：

1. `POST /applications` 创建一条带 `source` 和 `jd_text` 的 application。
2. 查看返回中的 `source_type`、`jd_summary`、`jd_keywords`、`jd_required_skills`、`jd_years_requirement`、`jd_location_requirement`、`jd_remote_type`。
3. `PATCH /applications/{application_id}` 更新 `jd_text`，例如加入 `remote`、`Docker`、`React`。
4. 再次查看解析字段是否变化。
5. 调用 `POST /job_match` 或 `POST /agent/workflow_preview`，说明岗位上下文已经更规范。

演示时强调：

- JD 解析是本地规则 baseline。
- 不调用 LLM，不做 RAG / Embedding。
- 不抓取岗位，不连接真实招聘平台。
- 解析结果用于求职者侧快速筛选和 application 数据标准化，不是招聘决策。
## Step 13 Demo: Application Review / Follow-up Decision

演示目标：说明 `/application_review` 不是重新做 `job_match`，而是在已有 application、JD 解析字段、`job_match` 和 HR intent 基础上生成跟进建议。

1. 创建一条带 JD 的 application。
2. 调用 `POST /job_match`，确认岗位匹配评分仍然正常。
3. 调用 `POST /application_review`：

```json
{
  "application_id": 1,
  "update_application": false
}
```

4. 展示返回中的关键字段：

- `review_score`
- `review_level`
- `confidence`
- `evidence`
- `recommended_action`
- `risk_flags`
- `missing_information`
- `suggested_next_message_type`
- `decision_factors`

5. 再演示高风险 HR message：

```json
{
  "application_id": 1,
  "hr_message": "这个岗位是外包，需要长期驻场，可以接受吗？",
  "update_application": false
}
```

讲解重点：

- 外包 / 驻场风险会进入 `risk_flags`
- 风险证据会进入 `evidence`，并标出来源如 `hr_message`
- `review_level` 会变得更谨慎
- `suggested_next_message_type` 会倾向 `confirm_details`
- 接口不自动发送 HR 消息，不自动投递，不自动确认面试，也不自动修改 application status

补充说明：`confidence` 是规则证据充分程度，不是大模型概率；`evidence` 用来解释规则判断，也为未来可选 LLM enhanced review 提供结构化上下文。LLM 未来只能参考这些规则结果，不能把规则推断当作事实，最终仍然 Human-in-the-loop。

## Step 14 Demo: LLM Enhanced Application Review

演示顺序：

1. 先调用 `POST /application_review`，展示规则版 `review_score`、`review_level`、`confidence` 和 `evidence`。
2. 再调用 `POST /application_review/llm_enhance`：

```json
{
  "application_id": 1,
  "hr_message": "这个岗位需要长期驻场，你能接受吗？",
  "include_raw_prompt": false
}
```

3. 无 API key 时，展示 `rule_review` 仍然存在，`llm_used=false`，`llm_error=api_key_missing`。
4. 有 API key 时，展示 `llm_enhanced_review` 如何在规则结果基础上做解释、查漏补缺和保守建议。

讲解重点：

- LLM 不从零判断岗位，只参考规则版 review。
- LLM 不发送 HR 消息，不自动投递，不自动确认面试，不自动修改 application status。
- LLM 输出只是只读分析，最终仍然需要用户确认。

## Step 15 Demo: LLM HR Reply Draft

演示顺序：

1. 调用 `/application_review`，展示规则版分析建议。
2. 调用 `/application_review/llm_enhance`，展示 LLM 只读增强分析。
3. 调用 `/application_review/hr_reply_draft`，查看“回复策略 + HR 回复草稿”：

```json
{
  "application_id": 1,
  "hr_message": "这个岗位是外包项目，需要长期驻场客户现场，你能接受吗？",
  "draft_tone": "professional",
  "include_raw_prompt": false
}
```

## Step 16 demo: POST /agent/langgraph_workflow_preview

Step 16 的演示重点是说明 LangGraph workflow preview 已经把 Step 13 的 application review 和 Step 15 的 HR reply draft package 串起来，但仍然停在 Human-in-the-loop。

建议请求：

```json
{
  "application_id": 1,
  "hr_message": "这个岗位是外包项目，需要长期驻场客户现场，你能接受吗？"
}
```

演示重点：

- `workflow_steps` 包含 `run_application_review`、`generate_hr_reply_package` 和 `require_user_approval`。
- `application_review` 来自规则版 review，展示 `confidence`、`evidence`、`risk_flags` 和 `missing_information`。
- `reply_strategy_for_user` 和 `hr_reply_draft` 来自 HR reply package。
- `node_debug.run_application_review_node.llm_used=false`，说明规则 review 不调用 LLM。
- `node_debug.generate_hr_reply_package_node.database_write=false`，说明草稿生成不写 application。
- `approval_required=true`、`approved_by_user=false`，说明最终发送或状态更新仍然必须由用户确认。

强调：Step 16 不自动发送 HR 消息，不自动投递，不自动确认面试，不自动修改 application 状态；没有 API key 时会返回 `rule_fallback` 草稿。

## Step 16.5 Demo Route: 三条验收路线

### Demo 1：外包 / 驻场风险确认

目标：展示系统如何识别外包、驻场、客户现场等风险信号，并生成需要用户审核的保守回复草稿。

推荐流程：

1. 创建或使用已有 application，确保 JD 或 notes 中有 AI 应用开发相关信息。
2. 调用 `POST /application_review`：

```json
{
  "application_id": 1,
  "hr_message": "这个岗位是外包项目，需要长期驻场客户现场，你能接受吗？",
  "update_application": false
}
```

观察重点：

- `application_review.review_level`
- `application_review.confidence`
- `application_review.evidence`
- `application_review.risk_flags`
- `application_review.missing_information`

3. 调用 `POST /application_review/hr_reply_draft`：

```json
{
  "application_id": 1,
  "hr_message": "这个岗位是外包项目，需要长期驻场客户现场，你能接受吗？",
  "draft_tone": "professional",
  "include_raw_prompt": false
}
```

观察重点：

- `reply_strategy_for_user`
- `hr_reply_draft`
- `draft_source`
- `must_confirm_before_send`
- `safe_to_send`

4. 调用 `POST /agent/langgraph_workflow_preview`：

```json
{
  "application_id": 1,
  "hr_message": "这个岗位是外包项目，需要长期驻场客户现场，你能接受吗？"
}
```

观察重点：

- `application_review`
- `reply_strategy_for_user`
- `hr_reply_draft`
- `node_debug`
- `workflow_steps` 中的 `require_user_approval`
- `approval_required=true`
- `approved_by_user=false`

讲解边界：系统只提示风险、生成草稿和等待用户确认，不自动拒绝、不自动发送、不自动修改 application status。

### Demo 2：项目经验回复

目标：展示项目经历类 HR message 如何触发偏 `project_intro` 的回复草稿，同时强调不能夸大能力。

推荐请求：

```json
{
  "application_id": 1,
  "hr_message": "你做过 RAG 或 Agent 项目吗？",
  "draft_tone": "professional",
  "include_raw_prompt": false
}
```

推荐先调用：

- `POST /application_review/hr_reply_draft`
- `POST /agent/langgraph_workflow_preview`

观察重点：

- `hr_intent.primary_intent` 是否偏向 `project_experience`
- `hr_reply_draft.draft_type` 是否偏 `project_intro`
- `hr_reply_draft.risk_notes`
- `must_confirm_before_send`

讲解边界：回复只能基于 `candidate_profile.resume_text`、`project_context`、`available_projects` 等已有事实，不能把 Demo 说成完整生产级系统，不能编造企业落地经验。

Step 16.7 后还要重点确认项目技术栈不能混说：

- RAG 企业知识库项目可以说 FastAPI、文档入库、FAISS + BM25 + RRF、Reranker、low_confidence、SQLite 多轮会话。
- RAG 企业知识库项目不能说 LangGraph。
- AI Job Agent 可以说 candidate profile、application tracking、JD parsing、job_match、application_review、HR reply draft、LangGraph workflow preview。
- AI Job Agent 不能说 RAG 检索、Embedding、向量数据库、FAISS / BM25 / Reranker。
- 如果草稿出现“AI Job Agent 使用 RAG 检索”或“RAG 项目使用 LangGraph”这类混淆，系统会替换为安全 fallback，并在 `debug.project_fact_boundary_fallback=true` 中记录。

### Demo 3：面试时间场景

目标：展示系统可以生成面试时间沟通草稿，但不能自动确认具体面试安排。

Step 16.7 后，面试时间回复必须基于手动维护的 `interview_availability_slots`。

推荐请求：

```json
{
  "application_id": 1,
  "hr_message": "明天下午三点方便面试吗？",
  "draft_tone": "professional",
  "include_raw_prompt": false
}
```

推荐先调用：

- `POST /application_review/hr_reply_draft`
- `POST /agent/langgraph_workflow_preview`

观察重点：

- `hr_intent.primary_intent` 是否偏向 `interview_schedule`
- `hr_reply_draft.draft_type`
- `available_slots_used`
- `availability_source`
- `availability_missing`
- `must_confirm_before_send`
- `approval_required=true`
- `approved_by_user=false`

无可用 slots 时，系统只能回复类似：

> 这个时间我需要先确认一下日程，稍后回复您是否方便。

不能虚构“明天下午或后天上午都可以协调”等时间段。

有可用 slots 时，可以先创建：

```json
{
  "date": "2026-06-20",
  "start_time": "14:00",
  "end_time": "16:00",
  "timezone": "Asia/Shanghai",
  "status": "available",
  "note": "Demo 可面试时间"
}
```

然后再调用 `/application_review/hr_reply_draft`。草稿只能提供 slots 中的时间段供 HR 参考，仍然不能自动确认面试。

讲解边界：系统不能替用户自动确认“明天下午三点可以”，只能基于用户维护的 slots 生成需要人工确认的草稿。最终是否接受时间、是否发送回复，必须由用户人工决定。

4. 展示从“分析建议”到“回复策略 + HR 回复草稿”的区别：`reply_strategy_for_user` 给用户看，`hr_reply_draft` 是给 HR 的草稿。
5. 强调草稿不会自动发送，`safe_to_send=true` 也不代表自动发送。
6. 强调 Step 15 默认不调用 Step 14，`debug.step14_llm_enhance_called=false`，避免重复 LLM 调用。

重点检查：

- 草稿是否没有直接答应外包 / 驻场
- 是否提出确认合同主体、驻场周期、薪资范围、职责等问题
- `debug.auto_send_message=false`
- application status 不变
