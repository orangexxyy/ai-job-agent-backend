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
