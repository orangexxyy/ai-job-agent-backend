# API Examples

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
