# API Examples

当前 Demo 的推荐接口顺序和 Legacy / Preview 分类见 [API Surface Guide](api_surface_guide.md)。`/hr/analyze` 与 `/hr/reply` 示例仅用于兼容旧版调用，新的 Demo 流程应使用 `/application_review/hr_reply_draft`，并在用户人工处理后调用 `/applications/{application_id}/confirm_hr_reply`。

## API Smoke Test Harness

`scripts/api_smoke_test.py` is a local API integration smoke test harness. It assumes the FastAPI server is already running and does not start uvicorn by itself.

Start the API server first:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Run the smoke test:

```bash
python scripts/api_smoke_test.py
```

Or pass a custom local base URL:

```bash
python scripts/api_smoke_test.py --base-url http://127.0.0.1:8001
```

The harness covers:

- `GET /health`
- `POST /profile`
- `GET /profile`
- `POST /applications`
- `GET /applications/{application_id}`
- `PATCH /applications/{application_id}`
- invalid application status handling
- `POST /job_match`
- `POST /hr/analyze`
- old `POST /hr/reply` without `application_id`
- new `POST /hr/reply` with `application_id`
- missing `application_id` handling

It temporarily writes a test `candidate_profile`, attempts to restore the original profile, creates one `HARNESS Demo Company <timestamp>` application, and attempts to mark that application as `closed` at the end. It does not call DeepSeek / LLM, does not apply to jobs, and does not send HR messages.

## POST /job_match

Analyzes one application record with local rule-based scoring. This endpoint is a candidate-side prioritization helper. It does not call DeepSeek / LLM and does not represent a recruitment decision.

```bash
curl -X POST http://127.0.0.1:8001/job_match \
  -H "Content-Type: application/json" \
  -d "{\"application_id\":1,\"update_application\":true}"
```

Expected key result:

```json
{
  "success": true,
  "message": "job match analyzed",
  "data": {
    "application_id": 1,
    "match_score": 82,
    "match_level": "strong_match",
    "recommendation": "建议优先跟进",
    "dimensions": [
      {
        "name": "role_fit",
        "score": 23,
        "max_score": 25,
        "matched_signals": ["RAG", "Agent"],
        "missing_signals": []
      }
    ],
    "application_updated": true,
    "application_update_fields": {
      "match_score": 82,
      "next_action": "优先跟进，并准备 AI 应用 / RAG / Agent 项目讲法",
      "risk_flags": []
    },
    "debug": {
      "scoring_version": "rule_based_v1",
      "used_sources": ["candidate_profile", "application"],
      "llm_used": false
    }
  }
}
```

When `update_application=true`, only `match_score`, `next_action`, and `risk_flags` are written back to the application. `status` and `last_hr_message` are not modified.

Missing application result:

```json
{
  "success": false,
  "message": "application not found",
  "data": null
}
```

Missing profile result:

```json
{
  "success": false,
  "message": "candidate_profile not found. Please create profile first.",
  "data": null
}
```

## GET /health

```bash
curl http://127.0.0.1:8000/health
```

Response:

```json
{
  "status": "ok",
  "service": "ai_job_agent"
}
```

## POST /profile

```bash
curl -X POST http://127.0.0.1:8000/profile \
  -H "Content-Type: application/json" \
  -d "{\"expected_salary_min\":15000,\"expected_salary_max\":20000,\"minimum_salary\":13000,\"salary_note\":\"Prefer roles aligned with AI application development.\",\"availability_note\":\"About one week, negotiable.\",\"preferred_cities\":[\"Hangzhou\",\"Shanghai\",\"Chongqing\",\"Remote\"],\"acceptable_cities\":[\"Other cities are negotiable if the AI role and salary fit.\"],\"relocation_policy\":\"Long-term relocation is not preferred, but strong AI role fit is negotiable.\",\"outsourcing_policy\":\"Formal roles are preferred; high-quality AI outsourcing projects can be discussed.\",\"onsite_policy\":\"Normal office work is acceptable; long-term onsite client placement needs discussion.\",\"remote_policy\":\"Remote or hybrid work is acceptable.\",\"overtime_policy\":\"Project-based overtime is acceptable; long-term intense overtime is not preferred.\",\"business_trip_policy\":\"Short business trips are negotiable; frequent long-term travel is not preferred.\",\"target_roles\":[\"AI Application Developer\",\"LLM Application Developer\",\"Python Backend + AI\"],\"available_projects\":[\"FastAPI + RAG enterprise knowledge base\",\"Medical document RAG\",\"Coze + Feishu workflow\"],\"truth_boundaries\":[\"No complete production-grade intelligent recruitment system experience\",\"No LoRA fine-tuning experience\",\"No complete complex multi-agent platform experience\"],\"resume_text\":\"\",\"project_context\":\"\"}"
```

Response:

```json
{
  "success": true,
  "profile_id": 1,
  "message": "candidate_profile saved"
}
```

## GET /profile

```bash
curl http://127.0.0.1:8000/profile
```

Response when a profile exists:

```json
{
  "success": true,
  "message": "candidate_profile found",
  "data": {
    "id": 1,
    "expected_salary_min": 15000,
    "expected_salary_max": 20000,
    "minimum_salary": 13000,
    "salary_note": "Prefer roles aligned with AI application development.",
    "availability_note": "About one week, negotiable.",
    "preferred_cities": ["Hangzhou", "Shanghai", "Chongqing", "Remote"],
    "acceptable_cities": ["Other cities are negotiable if the AI role and salary fit."],
    "relocation_policy": "Long-term relocation is not preferred, but strong AI role fit is negotiable.",
    "outsourcing_policy": "Formal roles are preferred; high-quality AI outsourcing projects can be discussed.",
    "onsite_policy": "Normal office work is acceptable; long-term onsite client placement needs discussion.",
    "remote_policy": "Remote or hybrid work is acceptable.",
    "overtime_policy": "Project-based overtime is acceptable; long-term intense overtime is not preferred.",
    "business_trip_policy": "Short business trips are negotiable; frequent long-term travel is not preferred.",
    "target_roles": ["AI Application Developer", "LLM Application Developer", "Python Backend + AI"],
    "available_projects": ["FastAPI + RAG enterprise knowledge base", "Medical document RAG", "Coze + Feishu workflow"],
    "truth_boundaries": ["No complete production-grade intelligent recruitment system experience", "No LoRA fine-tuning experience", "No complete complex multi-agent platform experience"],
    "resume_text": "",
    "project_context": "",
    "created_at": "2026-06-02T00:00:00+00:00",
    "updated_at": "2026-06-02T00:00:00+00:00"
  }
}
```

Response when no profile exists:

```json
{
  "success": false,
  "message": "candidate_profile not found",
  "data": null
}
```

## POST /hr/analyze

The first version is rule-based and does not call an LLM.

### Salary, Availability, Relocation

```bash
curl -X POST http://127.0.0.1:8000/hr/analyze \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"你期望薪资多少？一周能到岗吗？接受外地吗？\",\"company_name\":\"某智能招聘公司\",\"job_title\":\"AI应用开发工程师\"}"
```

Expected key result:

```json
{
  "success": true,
  "message": "hr message analyzed",
  "data": {
    "intents": ["salary_expectation", "availability", "relocation"],
    "primary_intent": "salary_expectation",
    "need_profile": true,
    "need_llm": false,
    "risk_level": "medium"
  }
}
```

### Project Experience And Business Proposal

```bash
curl -X POST http://127.0.0.1:8000/hr/analyze \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"你做过智能招聘相关项目吗？如果我们想做简历筛选系统，你有什么方案？\"}"
```

Expected key result:

```json
{
  "success": true,
  "data": {
    "intents": ["project_experience", "business_proposal"],
    "need_profile": true,
    "need_resume_context": true,
    "need_project_context": true,
    "need_llm": true,
    "risk_level": "high"
  }
}
```

### Interview Schedule

```bash
curl -X POST http://127.0.0.1:8000/hr/analyze \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"方便明天下午视频面试吗？\"}"
```

Expected key result:

```json
{
  "success": true,
  "data": {
    "intents": ["interview_schedule"],
    "need_profile": true,
    "need_application_history": true,
    "risk_level": "medium",
    "suggested_next_action": "Prepare a schedule reply draft, but the interview time must be confirmed by the user."
  }
}
```

### GitHub Request

```bash
curl -X POST http://127.0.0.1:8000/hr/analyze \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"可以发一下你的GitHub项目地址吗？\"}"
```

Expected key result:

```json
{
  "success": true,
  "data": {
    "intents": ["github_request"],
    "need_profile": true,
    "need_llm": false,
    "risk_level": "medium"
  }
}
```

## POST /hr/reply

The first version is template-based. It reads `candidate_profile`, reuses `/hr/analyze` logic, applies rule-based truth boundary checks, and returns a draft for human approval. It does not call an LLM and does not send any message.

### Project Context Enhanced Reply

For `project_experience`, `technical_question`, and `business_proposal` intents, `/hr/reply` can use local profile context from `resume_text`, `project_context`, and `available_projects`. This is keyword-based snippet selection only. It is not RAG, does not use Embedding/vector search, and does not call an LLM.

```bash
curl -X POST http://127.0.0.1:8001/hr/reply \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"Which RAG or Agent related projects have you built?\",\"company_name\":\"Example AI Company\",\"job_title\":\"AI Application Developer\",\"extra_context\":\"\"}"
```

Expected key result:

```json
{
  "success": true,
  "message": "hr reply draft generated",
  "data": {
    "primary_intent": "project_experience",
    "reply_draft": "关于项目经历，我目前更适合从自己做过的 AI 应用 / RAG / Agent Demo 项目角度来说明...",
    "safe_to_send": false,
    "context_used": ["project_context", "resume_text"],
    "selected_context_snippets": [
      {
        "source": "project_context",
        "text": "RAG project uses FastAPI, txt/PDF/Excel ingestion, FAISS + BM25 + RRF hybrid retrieval..."
      }
    ],
    "context_reply_mode": "profile_context_enhanced",
    "debug": {
      "need_project_context": true,
      "need_llm": true
    }
  }
}
```

When profile context is missing, the endpoint returns a conservative fallback asking the user to supplement `resume_text / project_context`; it does not fabricate candidate experience.

### With application_id Context

When `application_id` is provided, `/hr/reply` loads the matching application record, uses its company and job title as context, returns `application_context`, and safely updates only `last_hr_message` and `next_action`. It does not send messages, confirm interviews, or update application `status`.

```bash
curl -X POST http://127.0.0.1:8001/hr/reply \
  -H "Content-Type: application/json" \
  -d "{\"application_id\":1,\"message\":\"方便明天下午视频面试吗？\",\"company_name\":\"\",\"job_title\":\"\",\"extra_context\":\"\"}"
```

Request body:

```json
{
  "application_id": 1,
  "message": "方便明天下午视频面试吗？",
  "company_name": "",
  "job_title": "",
  "extra_context": ""
}
```

Expected key result:

```json
{
  "success": true,
  "message": "hr reply draft generated",
  "data": {
    "application_id": 1,
    "application_context": {
      "id": 1,
      "company_name": "Example AI Company",
      "job_title": "AI Application Developer",
      "status": "saved",
      "job_source": "Manual",
      "job_url": "https://example.com/job/123",
      "next_action": "Review JD fit",
      "last_hr_message": "",
      "jd_text_preview": "Build AI application workflows with FastAPI and LLM tools."
    },
    "application_updated": true,
    "application_update_fields": {
      "last_hr_message": "方便明天下午视频面试吗？",
      "next_action": "确认面试时间"
    },
    "primary_intent": "interview_schedule",
    "safe_to_send": true
  }
}
```

Missing application result:

```bash
curl -X POST http://127.0.0.1:8001/hr/reply \
  -H "Content-Type: application/json" \
  -d "{\"application_id\":999999,\"message\":\"方便明天下午视频面试吗？\"}"
```

```json
{
  "success": false,
  "message": "application not found",
  "data": null
}
```

### Salary, Availability, Relocation

```bash
curl -X POST http://127.0.0.1:8000/hr/reply \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"你期望薪资多少？一周能到岗吗？接受外地吗？\",\"company_name\":\"某智能招聘公司\",\"job_title\":\"AI应用开发工程师\"}"
```

Expected key result:

```json
{
  "success": true,
  "message": "hr reply draft generated",
  "data": {
    "intents": ["salary_expectation", "availability", "relocation"],
    "primary_intent": "salary_expectation",
    "safe_to_send": true,
    "used_sources": ["candidate_profile", "hr_intent_rules", "truth_boundary_rules"],
    "debug": {
      "need_profile": true,
      "need_llm": false
    }
  }
}
```

### Outsourcing

```bash
curl -X POST http://127.0.0.1:8000/hr/reply \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"这个岗位是外包，能接受吗？\"}"
```

Expected key result:

```json
{
  "success": true,
  "data": {
    "intents": ["outsourcing"],
    "safe_to_send": true,
    "reply_draft": "The draft should use outsourcing_policy from candidate_profile."
  }
}
```

### Interview Schedule

```bash
curl -X POST http://127.0.0.1:8000/hr/reply \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"方便明天下午视频面试吗？\"}"
```

Expected key result:

```json
{
  "success": true,
  "data": {
    "intents": ["interview_schedule"],
    "safe_to_send": true,
    "suggested_followup": "面试时间需要用户最终确认。"
  }
}
```

### High-Risk Project Or Business Proposal

```bash
curl -X POST http://127.0.0.1:8000/hr/reply \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"你做过完整智能招聘系统吗？如果我们要做自动简历筛选和自动招聘决策，你能做吗？\"}"
```

Expected key result:

```json
{
  "success": true,
  "data": {
    "risk_level": "high",
    "safe_to_send": false,
    "cannot_claim": ["..."],
    "suggested_followup": "This intent should be handled by future LLM/RAG-enhanced reply generation."
  }
}
```

## POST /applications

Creates a manual application tracking record. This endpoint does not apply to a job, connect to a recruitment platform, scrape a JD, send an HR message, or call an LLM.

```bash
curl -X POST http://127.0.0.1:8000/applications \
  -H "Content-Type: application/json" \
  -d "{\"company_name\":\"Example AI Company\",\"job_title\":\"AI Application Developer\",\"job_source\":\"Manual\",\"job_url\":\"https://example.com/job/123\",\"jd_text\":\"Build AI application workflows with FastAPI and LLM tools.\",\"status\":\"saved\",\"match_score\":null,\"hr_contact_name\":\"\",\"hr_contact_channel\":\"\",\"last_hr_message\":\"\",\"next_action\":\"Review JD fit\",\"next_action_due_date\":\"\",\"notes\":\"Manual tracking record only.\",\"risk_flags\":[]}"
```

Response:

```json
{
  "success": true,
  "message": "application created",
  "data": {
    "company_name": "Example AI Company",
    "job_title": "AI Application Developer",
    "job_source": "Manual",
    "job_url": "https://example.com/job/123",
    "jd_text": "Build AI application workflows with FastAPI and LLM tools.",
    "status": "saved",
    "match_score": null,
    "hr_contact_name": "",
    "hr_contact_channel": "",
    "last_hr_message": "",
    "next_action": "Review JD fit",
    "next_action_due_date": "",
    "notes": "Manual tracking record only.",
    "risk_flags": [],
    "id": 1,
    "created_at": "2026-06-10T00:00:00+00:00",
    "updated_at": "2026-06-10T00:00:00+00:00"
  }
}
```

Invalid status example:

```bash
curl -X POST http://127.0.0.1:8000/applications \
  -H "Content-Type: application/json" \
  -d "{\"company_name\":\"Example AI Company\",\"job_title\":\"AI Application Developer\",\"status\":\"unknown\"}"
```

Expected key result:

```json
{
  "success": false,
  "message": "invalid status 'unknown'. allowed values: applied, closed, hr_contacted, interview_done, interview_scheduled, offer, rejected, saved",
  "data": null
}
```

## GET /applications

Lists application records ordered by `updated_at DESC, id DESC`. Optional filters are `status`, `company_name`, `job_title`, and `limit`. `limit` defaults to 50 and has a maximum of 100.

```bash
curl "http://127.0.0.1:8000/applications?status=saved&company_name=AI&limit=50"
```

Response:

```json
{
  "success": true,
  "message": "applications listed",
  "data": [
    {
      "id": 1,
      "company_name": "Example AI Company",
      "job_title": "AI Application Developer",
      "status": "saved",
      "risk_flags": [],
      "created_at": "2026-06-10T00:00:00+00:00",
      "updated_at": "2026-06-10T00:00:00+00:00"
    }
  ]
}
```

## GET /applications/{application_id}

```bash
curl http://127.0.0.1:8000/applications/1
```

Response when the record exists:

```json
{
  "success": true,
  "message": "application found",
  "data": {
    "id": 1,
    "company_name": "Example AI Company",
    "job_title": "AI Application Developer",
    "status": "saved",
    "risk_flags": []
  }
}
```

Response when the record does not exist:

```json
{
  "success": false,
  "message": "application not found",
  "data": null
}
```

## PATCH /applications/{application_id}

Updates only the fields included in the request body.

```bash
curl -X PATCH http://127.0.0.1:8000/applications/1 \
  -H "Content-Type: application/json" \
  -d "{\"status\":\"hr_contacted\",\"last_hr_message\":\"HR asked about availability.\",\"next_action\":\"Prepare human-approved reply draft\",\"risk_flags\":[\"needs_manual_review\"]}"
```

Response:

```json
{
  "success": true,
  "message": "application updated",
  "data": {
    "id": 1,
    "company_name": "Example AI Company",
    "job_title": "AI Application Developer",
    "status": "hr_contacted",
    "last_hr_message": "HR asked about availability.",
    "next_action": "Prepare human-approved reply draft",
    "risk_flags": ["needs_manual_review"]
  }
}
```
## POST /agent/workflow_preview

`/agent/workflow_preview` 是 Step 10 的规则版工作流预览接口。它会串联 `candidate_profile`、`application`、`job_match`、可选 HR intent 和可选 HR reply draft，但只做预览，不写入 application。

它不是 LangGraph，不调用 DeepSeek / LLM，不实现 RAG，不使用 Playwright，不自动投递，不自动发送 HR 消息，不自动确认面试时间。

```bash
curl -X POST http://127.0.0.1:8001/agent/workflow_preview \
  -H "Content-Type: application/json" \
  -d "{\"application_id\":1,\"hr_message\":\"方便介绍一下你做过的 RAG 或 Agent 项目吗？\"}"
```

Request body:

```json
{
  "application_id": 1,
  "hr_message": "方便介绍一下你做过的 RAG 或 Agent 项目吗？"
}
```

Expected key result:

```json
{
  "success": true,
  "message": "workflow preview generated",
  "data": {
    "workflow_mode": "rule_based_preview",
    "application_id": 1,
    "workflow_steps": [
      {
        "name": "load_candidate_profile",
        "status": "completed"
      },
      {
        "name": "require_user_approval",
        "status": "waiting"
      }
    ],
    "state_summary": {
      "has_candidate_profile": true,
      "has_application": true,
      "has_hr_message": true,
      "reply_draft_generated": true
    },
    "approval_required": true,
    "approved_by_user": false,
    "debug": {
      "llm_used": false,
      "langgraph_used": false,
      "rag_used": false,
      "auto_apply": false,
      "auto_send_message": false,
      "database_write_intended": false
    }
  }
}
```

Missing application result:

```json
{
  "success": false,
  "message": "application not found",
  "data": null
}
```
## POST /agent/langgraph_workflow_preview

`/agent/langgraph_workflow_preview` 是 LangGraph `StateGraph` 版 workflow preview。Step 16 后，它会串联 application review、HR reply package 和 Human-in-the-loop 审批节点。

它不实现 RAG，不使用 Playwright，不自动投递，不自动发送 HR 消息，不自动确认面试时间，也不写入 application。规则版 application review 节点不调用 LLM；HR reply package 节点可能在配置 API key 后通过 Step 15 调用一次 DeepSeek-compatible LLM，没有 API key 时会返回 `rule_fallback`。

```bash
curl -X POST http://127.0.0.1:8001/agent/langgraph_workflow_preview \
  -H "Content-Type: application/json" \
  -d "{\"application_id\":1,\"hr_message\":\"方便介绍一下你做过的 RAG 或 Agent 项目吗？\"}"
```

Step 16 后，该接口会在 LangGraph 中串联 application review 和 HR reply package。它仍然是 preview，不自动发送、不自动投递、不自动确认面试，也不自动修改 application 状态。

Expected key result:

```json
{
  "success": true,
  "message": "langgraph workflow preview generated",
  "data": {
    "workflow_mode": "langgraph_preview",
    "workflow_engine": "langgraph_stategraph",
    "application_id": 1,
    "workflow_steps": [
      {
        "name": "load_candidate_profile",
        "status": "completed"
      },
      {
        "name": "run_application_review",
        "status": "completed"
      },
      {
        "name": "generate_hr_reply_package",
        "status": "completed"
      },
      {
        "name": "require_user_approval",
        "status": "waiting"
      }
    ],
    "application_review": {
      "review_engine": "rule_based_application_review",
      "confidence": "medium",
      "evidence": []
    },
    "reply_strategy_for_user": {
      "summary": "先确认岗位风险点，再决定是否继续沟通。"
    },
    "hr_reply_draft": {
      "draft_type": "confirm_details",
      "draft_source": "rule_fallback",
      "draft_text": "您好，这个岗位我可以进一步了解。想先确认一下外包、驻场地点、合同主体和项目周期等信息。"
    },
    "hr_reply_package": {
      "draft_source": "rule_fallback",
      "llm_used": false,
      "human_review_required": true
    },
    "node_debug": {
      "run_application_review_node": {
        "llm_used": false,
        "database_read": true,
        "database_write": false,
        "external_api_called": false,
        "status": "success"
      },
      "generate_hr_reply_package_node": {
        "llm_used": false,
        "database_read": true,
        "database_write": false,
        "external_api_called": false,
        "status": "success",
        "draft_source": "rule_fallback"
      }
    },
    "approval_required": true,
    "approved_by_user": false,
    "debug": {
      "langgraph_used": true,
      "application_review_used": true,
      "hr_reply_draft_used": true,
      "rag_used": false,
      "playwright_used": false,
      "auto_apply": false,
      "auto_send_message": false,
      "auto_confirm_interview": false,
      "database_write_intended": false
    }
  }
}
```
### LangGraph observability fields

`POST /agent/langgraph_workflow_preview` 还会返回 LangGraph 可观测性字段，方便从 Swagger 直接看出它和普通 Python workflow 的区别。

```json
{
  "graph_structure": {
    "nodes": [
      "load_profile_node",
      "load_application_node",
      "run_application_review_node",
      "generate_hr_reply_package_node",
      "require_user_approval_node",
      "handle_error_node"
    ],
    "edges": [
      "START -> load_profile_node",
      "run_application_review_node -> generate_hr_reply_package_node",
      "require_user_approval_node -> END"
    ],
    "conditional_edges": [
      {
        "from": "load_profile_node",
        "condition": "error_message exists ? handle_error_node : load_application_node"
      }
    ]
  },
  "state_snapshots": [
    {
      "after_node": "load_profile_node",
      "candidate_profile_loaded": true,
      "application_loaded": false,
      "has_job_match": false,
      "approval_required": false,
      "error_message": null
    },
    {
      "after_node": "require_user_approval_node",
      "approval_required": true,
      "approved_by_user": false
    }
  ],
  "edge_trace": [
    {
      "from": "load_profile_node",
      "decision": "continue",
      "to": "load_application_node",
      "reason": "error_message is empty"
    },
    {
      "from": "require_user_approval_node",
      "decision": "stop_for_human",
      "to": "END",
      "reason": "approval_required is true and approved_by_user is false"
    }
  ]
}
```
## Step 12: POST /applications with JD parsing

创建 application 时可以传入 `source` 和 `jd_text`。系统会用本地规则生成 `source_type` 和 JD 结构化字段。

这不是 LLM 语义理解，不调用 DeepSeek，不做 RAG / Embedding，不抓取岗位。

```bash
curl -X POST http://127.0.0.1:8001/applications \
  -H "Content-Type: application/json" \
  -d "{\"company_name\":\"星辰智能科技\",\"job_title\":\"AI 应用开发工程师\",\"source\":\"BOSS直聘\",\"jd_text\":\"岗位职责：负责基于 Python、FastAPI、RAG、LangGraph 的企业 AI 应用开发。任职要求：熟悉 LLM API、向量检索、Prompt Engineering，有 1-3 年后端开发经验，可接受杭州现场办公。\",\"status\":\"saved\",\"notes\":\"适合 AI 应用开发方向，后续重点跟进。\"}"
```

Expected key result:

```json
{
  "success": true,
  "message": "application created",
  "data": {
    "source": "BOSS直聘",
    "job_source": "BOSS直聘",
    "source_type": "boss",
    "jd_summary": "该岗位主要涉及 Python、FastAPI、LLM、RAG、LangGraph、Prompt Engineering 等方向。经验要求为 1-3年。地点要求包含 杭州。工作方式倾向 onsite。该摘要由本地规则生成，仅用于求职者侧快速筛选。",
    "jd_keywords": ["Python", "FastAPI", "LLM", "RAG", "LangGraph", "Prompt Engineering"],
    "jd_required_skills": ["LLM", "Prompt Engineering"],
    "jd_years_requirement": "1-3年",
    "jd_location_requirement": "杭州",
    "jd_remote_type": "onsite"
  }
}
```

## Step 12: PATCH /applications/{application_id} jd_text

当 PATCH 更新 `jd_text` 时，系统会重新解析 JD 字段，但不会自动修改未传入的 `status`。

```bash
curl -X PATCH http://127.0.0.1:8001/applications/1 \
  -H "Content-Type: application/json" \
  -d "{\"jd_text\":\"岗位职责：支持 remote 远程协作，负责 Docker、React 和 FastAPI 相关 AI 应用开发。\"}"
```

Expected key result:

```json
{
  "success": true,
  "message": "application updated",
  "data": {
    "jd_keywords": ["FastAPI", "Docker", "React"],
    "jd_remote_type": "remote"
  }
}
```
## Step 13: Application Review / Follow-up Decision

`POST /application_review` 基于 application、JD 解析字段、`job_match` 和可选 HR message 生成只读跟进建议。

### 普通 follow-up review

```bash
curl -X POST http://127.0.0.1:8001/application_review \
  -H "Content-Type: application/json" \
  -d "{\"application_id\":1,\"update_application\":false}"
```

示例返回：

```json
{
  "success": true,
  "message": "application reviewed",
  "data": {
    "application_id": 1,
    "review_mode": "rule_based",
    "review_score": 72,
    "review_level": "normal_priority",
    "confidence": "medium",
    "recommended_action": "可以继续跟进，建议补充确认薪资、工作方式和岗位真实职责。",
    "evidence": [
      {
        "type": "job_match",
        "text": "job_match 返回 match_score=78",
        "source": "job_match",
        "confidence": "high"
      },
      {
        "type": "jd_keyword",
        "text": "JD 命中 Python、FastAPI、RAG、LangGraph",
        "source": "jd_keywords",
        "confidence": "high"
      }
    ],
    "risk_flags": [],
    "missing_information": ["薪资范围未明确", "是否外包/驻场未明确"],
    "suggested_next_message_type": "confirm_details",
    "human_review_required": true,
    "llm_used": false,
    "debug": {
      "llm_used": false,
      "rag_used": false,
      "playwright_used": false,
      "auto_apply": false,
      "auto_send_message": false,
      "auto_update_status": false,
      "review_engine": "rule_based_application_review"
    }
  }
}
```

### 高风险外包 / 驻场 follow-up review

```bash
curl -X POST http://127.0.0.1:8001/application_review \
  -H "Content-Type: application/json" \
  -d "{\"application_id\":1,\"hr_message\":\"这个岗位是外包，需要长期驻场，可以接受吗？\",\"update_application\":false}"
```

预期重点：

- `review_level` 通常会降为 `cautious_follow_up`、`low_priority` 或 `not_recommended`
- `risk_flags` 会包含外包 / 驻场相关风险
- `evidence` 会包含 `risk_signal`，用于解释风险来自 `hr_message`、`jd_text`、`notes` 或 `last_hr_message`
- `suggested_next_message_type` 应为 `confirm_details`
- `debug.auto_apply`、`debug.auto_send_message`、`debug.auto_update_status` 都是 `false`

说明：

- `confidence` 是规则证据充分程度，不是 LLM 概率。
- `evidence` 用于解释规则判断，也为未来 LLM enhanced review 提供上下文。
- 未来 LLM 只能参考规则结果，不能把规则推断当作事实，最终仍然 Human-in-the-loop。

## Step 14: LLM Enhanced Application Review

### 无 API key 场景

```bash
curl -X POST http://127.0.0.1:8001/application_review/llm_enhance \
  -H "Content-Type: application/json" \
  -d "{\"application_id\":1,\"hr_message\":\"这个岗位需要长期驻场，你能接受吗？\",\"include_raw_prompt\":false}"
```

预期结构：

```json
{
  "success": true,
  "message": "api_key_missing",
  "data": {
    "application_id": 1,
    "rule_review": {"review_mode": "rule_based"},
    "llm_enhanced_review": null,
    "llm_used": false,
    "llm_error": "api_key_missing",
    "human_review_required": true,
    "debug": {
      "review_engine": "llm_enhanced_application_review",
      "base_review_engine": "rule_based_application_review",
      "rag_used": false,
      "playwright_used": false,
      "auto_apply": false,
      "auto_send_message": false,
      "auto_update_status": false,
      "database_write_intended": false
    }
  }
}
```

### 配置 API key 后的手动测试

`.env` 示例：

```text
DEEPSEEK_API_KEY=你的 key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

启动服务后调用同一接口，预期：

- `llm_used=true`
- `llm_enhanced_review` 存在
- LLM 输出只解释规则 review，不执行外部动作
- application status 不会被自动修改

## Step 15: LLM HR Reply Draft

### 外包 / 驻场场景

```bash
curl -X POST http://127.0.0.1:8001/application_review/hr_reply_draft \
  -H "Content-Type: application/json" \
  -d "{\"application_id\":1,\"hr_message\":\"这个岗位是外包项目，需要长期驻场客户现场，你能接受吗？\",\"draft_tone\":\"professional\",\"include_raw_prompt\":false}"
```

无 API key 或 LLM 调用失败时，预期返回保守 fallback：

```json
{
  "success": true,
  "message": "HR reply draft generated",
  "data": {
    "application_id": 1,
    "draft_source": "rule_fallback",
    "draft_type": "confirm_details",
    "reply_strategy_for_user": {
      "summary": "建议先确认岗位关键信息，不要直接答应。",
      "why_this_draft_type": "HR 消息包含外包和长期驻场，因此草稿类型为 confirm_details。",
      "key_risks": ["疑似外包", "疑似长期驻场"],
      "questions_to_confirm": ["合同主体", "驻场周期", "薪资范围", "社保缴纳主体"],
      "conflict_warnings": [],
      "conservative_next_step": "先向 HR 确认关键信息，再决定是否继续推进。"
    },
    "hr_reply_draft": {
      "draft_text": "您好，这个方向我可以进一步了解一下。为了判断是否合适，想先确认一下岗位的用工性质、工作方式、薪资范围和具体职责，谢谢。",
      "draft_goal": "确认岗位关键信息后再判断是否继续推进",
      "must_confirm_before_send": ["确认草稿内容符合本人真实意愿"],
      "risk_notes": ["草稿不会自动发送，必须人工审核"],
      "safe_to_send": false
    },
    "draft_text": "您好，这个方向我可以进一步了解一下。为了判断是否合适，想先确认一下岗位的用工性质、工作方式、薪资范围和具体职责，谢谢。",
    "safe_to_send": false,
    "human_review_required": true,
    "llm_used": false,
    "llm_error": "api_key_missing",
    "debug": {
      "draft_engine": "llm_hr_reply_draft",
      "analysis_and_draft_combined": true,
      "step14_llm_enhance_called": false,
      "auto_send_message": false,
      "auto_apply": false,
      "auto_update_status": false,
      "database_write_intended": false
    }
  }
}
```

配置 API key 后，`draft_source` 可以为 `llm`，`reply_strategy_for_user` 和 `hr_reply_draft` 来自模型 JSON。Step 15 默认不调用 Step 14，避免重复 LLM 调用。无论是否使用 LLM，接口都不会自动发送 HR 消息，也不会自动修改 application status。

## Step 16.7: Interview Availability Slots

`interview_availability_slots` 用于手动维护面试可用时间段。它不接 Google Calendar，不自动确认面试，不自动发送 HR 消息。

### POST /interview_availability_slots

```bash
curl -X POST http://127.0.0.1:8001/interview_availability_slots \
  -H "Content-Type: application/json" \
  -d "{\"date\":\"2026-06-20\",\"start_time\":\"14:00\",\"end_time\":\"16:00\",\"timezone\":\"Asia/Shanghai\",\"status\":\"available\",\"note\":\"Demo 可面试时间\"}"
```

Expected key result:

```json
{
  "success": true,
  "message": "interview availability slot created",
  "data": {
    "id": 1,
    "date": "2026-06-20",
    "start_time": "14:00",
    "end_time": "16:00",
    "timezone": "Asia/Shanghai",
    "status": "available"
  }
}
```

### GET /interview_availability_slots

默认只返回 `status=available`：

```bash
curl http://127.0.0.1:8001/interview_availability_slots
```

也可以查询其他状态：

```bash
curl "http://127.0.0.1:8001/interview_availability_slots?status=expired"
```

### PATCH /interview_availability_slots/{slot_id}

```bash
curl -X PATCH http://127.0.0.1:8001/interview_availability_slots/1 \
  -H "Content-Type: application/json" \
  -d "{\"status\":\"expired\",\"note\":\"Demo 后过期\"}"
```

## Step 16.7: HR Reply Draft Boundaries

### Project intro fact boundary

当 HR 问“你做过 RAG 或 Agent 项目吗？”时，`/application_review/hr_reply_draft` 会要求区分两个项目：

- RAG 企业知识库项目：可以说 FastAPI、文档入库、FAISS + BM25 + RRF、Reranker、low_confidence、SQLite 多轮会话。
- AI Job Agent：可以说 candidate profile、application tracking、JD parsing、job_match、application_review、HR reply draft、LangGraph workflow preview。

不能说：

- RAG 项目使用 LangGraph。
- AI Job Agent 使用 RAG / Embedding / 向量检索。
- 自动发送 HR 消息、自动投递、企业级生产系统。

如果草稿出现明显混淆，系统会使用安全 fallback，并在 `debug.project_fact_boundary_fallback=true` 记录。

### Interview schedule with slots

无可用 slots 时：

```json
{
  "application_id": 1,
  "hr_message": "明天下午三点方便视频面试吗？",
  "draft_tone": "professional",
  "include_raw_prompt": false
}
```

返回中重点看：

```json
{
  "draft_type": "interview_schedule",
  "availability_missing": true,
  "available_slots_used": [],
  "safe_to_send": false,
  "human_review_required": true
}
```

有可用 slots 时，草稿只能提供 `available_slots_used` 中的时间段供 HR 参考，仍然不会自动确认面试。

## Step 17: Confirm HR Reply After User Approval

`POST /application_review/hr_reply_draft` 仍然只生成草稿，不写 application。用户人工审核并自行处理回复后，才调用：

该接口当前只记录“本轮 HR 回复已由用户处理 / 手动发送”及对应 application 状态，不是通用人工确认接口，也不提供完整 approval log / audit log。

```bash
curl -X POST http://127.0.0.1:8001/applications/1/confirm_hr_reply \
  -H "Content-Type: application/json" \
  -d '{"draft_text":"您好，感谢您的邀请……","hr_message":"最近什么时候方便视频面试？","sent_channel":"manual","next_action":"wait_for_hr_response","note":"用户已人工确认并手动发送给 HR"}'
```

成功响应的关键字段：

```json
{
  "success": true,
  "message": "HR reply confirmed by user",
  "data": {
    "application_id": 1,
    "status": "hr_replied",
    "next_action": "wait_for_hr_response",
    "sent_channel": "manual",
    "confirmation_recorded": true,
    "already_confirmed": false,
    "debug": {
      "auto_send_message": false,
      "auto_apply": false,
      "auto_confirm_interview": false,
      "database_write_intended": true,
      "confirmed_by_user": true
    }
  }
}
```

不存在的 application 返回 404，空白 `draft_text` 返回 422，`offer / rejected / closed` 终态返回 409。重复提交相同草稿不会重复追加记录，而是返回 `already_confirmed=true`。
