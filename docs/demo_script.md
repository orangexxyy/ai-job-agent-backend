# Demo Script

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
2. `POST /profile`
3. `GET /profile`
4. `POST /applications`
5. `GET /applications/{application_id}`
6. `POST /job_match`
7. `POST /hr/analyze`
8. `POST /hr/reply` 不带 `application_id`
9. `POST /hr/reply` 带 `application_id`
10. `POST /hr/reply` 项目经历问题，展示 `selected_context_snippets`
11. `python scripts/api_smoke_test.py`

## 每个接口的演示目的

- `/health`：证明服务已启动。
- `/profile`：建立候选人稳定求职档案。
- `/applications`：建立具体投递上下文。
- `/job_match`：展示可解释岗位匹配评分和求职者侧优先级。
- `/hr/analyze`：展示规则版 HR intent analyzer。
- `/hr/reply`：展示基于 profile 的保守回复草稿。
- `/hr/reply + application_id`：展示绑定具体投递记录后的上下文回复。
- `/hr/reply 项目经历问题`：展示基于 `resume_text / project_context` 的增强回复。
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

4. 展示从“分析建议”到“回复策略 + HR 回复草稿”的区别：`reply_strategy_for_user` 给用户看，`hr_reply_draft` 是给 HR 的草稿。
5. 强调草稿不会自动发送，`safe_to_send=true` 也不代表自动发送。
6. 强调 Step 15 默认不调用 Step 14，`debug.step14_llm_enhance_called=false`，避免重复 LLM 调用。

重点检查：

- 草稿是否没有直接答应外包 / 驻场
- 是否提出确认合同主体、驻场周期、薪资范围、职责等问题
- `debug.auto_send_message=false`
- application status 不变
