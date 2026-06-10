# AI Job Agent

AI Job Agent is a human-in-the-loop assistant for AI application and LLM application job search workflows. The project helps a candidate keep profile facts explicit, answer HR questions safely, and prepare future job matching and proposal workflows without becoming an automatic mass-apply bot.

## Current Stage

Step 4 builds on the runnable FastAPI skeleton with rule-based HR intent analysis, profile-based HR reply draft generation, and manual application tracking:

- `GET /health`
- `POST /profile`
- `GET /profile`
- `POST /hr/analyze`
- `POST /hr/reply`
- `POST /applications`
- `GET /applications`
- `GET /applications/{application_id}`
- `PATCH /applications/{application_id}`
- SQLite initialization
- `candidate_profile` table
- `applications` table
- DeepSeek configuration placeholders
- Documentation for project boundaries and next steps

The first version of `/hr/analyze` uses local keyword rules only. The first version of `/hr/reply` uses those rules plus `candidate_profile` templates. Neither endpoint calls DeepSeek, calls any LLM, or consumes API tokens.

`/hr/reply` only returns a reply draft for human approval. It does not send messages. For project experience, technical solution, and business proposal questions, Step 3 returns a conservative high-risk draft instead of a complete answer.

The first version of `/applications` supports manual recording and updating of application records. It does not apply to jobs, connect to real recruitment platforms, scrape job posts, send HR messages, or run matching logic. These records are intended to support later job matching, HR communication history, interview status tracking, and job-search review workflows.

## Tech Stack

- Python
- FastAPI
- Pydantic
- SQLite
- python-dotenv
- requests
- DeepSeek-compatible configuration placeholder

## Setup

```bash
pip install -r requirements.txt
```

Create a local `.env` from `.env.example` if needed. Do not commit real API keys.

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Open:

```text
http://127.0.0.1:8001/docs
```

## Environment Variables

```text
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DATABASE_PATH=data/ai_job_agent.db
```

Step 3 still does not make real DeepSeek calls. `app/services/llm_service.py` only provides a placeholder wrapper for later work.

## API Examples

Health check:

```bash
curl http://127.0.0.1:8001/health
```

Save profile:

```bash
curl -X POST http://127.0.0.1:8001/profile \
  -H "Content-Type: application/json" \
  -d "{\"expected_salary_min\":15000,\"expected_salary_max\":20000,\"minimum_salary\":13000,\"preferred_cities\":[\"Hangzhou\",\"Shanghai\"],\"target_roles\":[\"AI Application Developer\"],\"available_projects\":[\"FastAPI + RAG knowledge base\"],\"truth_boundaries\":[\"No production-grade multi-agent platform experience\"]}"
```

Read profile:

```bash
curl http://127.0.0.1:8001/profile
```

Analyze HR message intent:

```bash
curl -X POST http://127.0.0.1:8001/hr/analyze \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"What salary package do you expect? Are you available within one week? Can you relocate?\",\"company_name\":\"Example AI Company\",\"job_title\":\"AI Application Developer\"}"
```

Generate HR reply draft:

```bash
curl -X POST http://127.0.0.1:8001/hr/reply \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"What salary package do you expect? Are you available within one week? Can you relocate?\",\"company_name\":\"Example AI Company\",\"job_title\":\"AI Application Developer\"}"
```

Create an application record:

```bash
curl -X POST http://127.0.0.1:8001/applications \
  -H "Content-Type: application/json" \
  -d "{\"company_name\":\"Example AI Company\",\"job_title\":\"AI Application Developer\",\"job_source\":\"Manual\",\"job_url\":\"https://example.com/job/123\",\"jd_text\":\"Build AI application workflows with FastAPI and LLM tools.\",\"status\":\"saved\",\"next_action\":\"Review JD fit\",\"notes\":\"Manual tracking record only.\",\"risk_flags\":[]}"
```

List application records:

```bash
curl "http://127.0.0.1:8001/applications?status=saved&limit=50"
```

Update application status:

```bash
curl -X PATCH http://127.0.0.1:8001/applications/1 \
  -H "Content-Type: application/json" \
  -d "{\"status\":\"hr_contacted\",\"last_hr_message\":\"HR asked about availability.\"}"
```

## Explicit Boundaries

Step 4 does not:

- Automatically apply to jobs
- Automatically send HR messages
- Connect to real recruitment platforms
- Implement Playwright
- Implement RAG
- Implement a frontend
- Scrape job posts
- Call DeepSeek or any LLM from `/applications`
- Implement job matching scores or business proposal logic
- Fabricate resume experience, education, salary, address, work years, or project history
- Bypass CAPTCHA, anti-crawling, risk control, or platform restrictions
- Generate complete high-risk project, technical, or business proposal answers

Interview times, salary negotiation, whether to accept a role, and all outbound messages require final user confirmation.

## Roadmap

- Step 5: truth boundary expansion or LLM/project-context enhanced reply drafts
- Step 6: job match scoring
- Step 7: business proposal generation
- Step 8: project-experience RAG
- Step 9: Playwright dry-run job collection with no auto-apply
- Step 10: user-confirmed semi-automation

