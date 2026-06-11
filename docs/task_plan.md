# Task Plan

## Current Stage

Step 8: profile context enhanced HR reply.

## Completed In Step 1

- FastAPI application skeleton
- SQLite initialization
- `candidate_profile` table design
- `GET /health`
- `POST /profile`
- `GET /profile`
- Pydantic schemas for profile input and output
- Placeholder LLM service
- `.env.example`
- `requirements.txt`
- Initial `README.md`
- Initial `AGENTS.md`
- Initial docs

## Completed In Step 2

- Added `POST /hr/analyze`.
- Added rule-based HR message intent classification.
- Added support for multiple intents in one HR message.
- Added `primary_intent`, source requirement flags, `risk_level`, `matched_keywords`, and `suggested_next_action`.
- Kept the analyzer local and deterministic: no DeepSeek call, no LLM call, no API token usage.

## Completed In Step 3

- Added `POST /hr/reply`.
- Reused the rule-based HR intent analyzer from Step 2.
- Loaded `candidate_profile` from SQLite before drafting.
- Generated profile-based reply drafts for salary, availability, location, relocation, outsourcing, onsite, remote, overtime, business trip, interview schedule, resume request, and GitHub request.
- Added rule-based truth boundary checks.
- Returned `safe_to_send`, `used_sources`, `truth_boundary`, `cannot_claim`, `suggested_followup`, `agent_steps`, and debug data.
- Kept high-risk project, technical, and business proposal questions conservative and not safe to send.
- Did not call DeepSeek or any LLM.

## Completed In Step 4

- Added `applications` SQLite table.
- Added `POST /applications` for manual application record creation.
- Added `GET /applications` for listing records with optional `status`, `company_name`, `job_title`, and `limit` filters.
- Added `GET /applications/{application_id}` for reading one application record.
- Added `PATCH /applications/{application_id}` for partial updates.
- Added status validation for `saved`, `applied`, `hr_contacted`, `interview_scheduled`, `interview_done`, `offer`, `rejected`, and `closed`.
- Stored `risk_flags` as a JSON string in SQLite and returned it as `list[str]` in the API.
- Kept application tracking manual only: no auto-apply, scraping, real recruitment platform connection, Playwright, RAG, DeepSeek, or LLM calls.

## Completed In Step 5

- Added optional `application_id` to `POST /hr/reply`.
- When `application_id` is provided, `/hr/reply` loads the matching `applications` record.
- Application `company_name` and `job_title` take priority over request-level company and job title context.
- Added `application_context` to the reply response for debugging and interview demo visibility.
- Added `application_id`, `application_updated`, and `application_update_fields` to the reply response.
- After generating a reply draft, safely updates only `last_hr_message` and `next_action` on the application record.
- Keeps application `status` unchanged; the API does not automatically schedule interviews or change application state.
- Returns `success=false`, `message="application not found"`, and `data=null` when the provided application does not exist.
- Kept the feature local and deterministic: no DeepSeek call, no LLM call, no Playwright, no RAG, no frontend, no automatic sending, and no automatic application.

## Completed In Step 6

- Added `scripts/api_smoke_test.py` as a local API integration smoke test harness.
- The harness assumes FastAPI is already running and defaults to `http://127.0.0.1:8001`.
- Added optional `--base-url` support for testing another local base URL.
- Covered the main API chain: `/health`, `/profile`, `/applications`, `/hr/analyze`, and `/hr/reply`.
- Added application-context `/hr/reply` verification for `application_id`, `application_context`, `application_updated`, and `application_update_fields`.
- Added invalid status verification for `/applications/{application_id}`.
- Added missing application verification for `/hr/reply`.
- The harness backs up the current single-user `candidate_profile`, writes a test profile, and attempts to restore the original profile at the end.
- The harness creates one `HARNESS Demo Company <timestamp>` application and attempts to mark it `closed` at the end.
- This is a development verification tool, not a business feature.
- It does not add business endpoints, call DeepSeek, call any LLM, send HR messages, apply to jobs, use Playwright, implement RAG, or add a frontend.

## Completed In Step 7

- Added `POST /job_match`.
- Added `JobMatchRequest`, `JobMatchDimension`, `JobMatchData`, and `JobMatchResponse`.
- Added rule-based `analyze_job_match(application_id, update_application=True)`.
- The matcher loads `candidate_profile` and the target `applications` record.
- The matcher combines `job_title`, `jd_text`, and `notes` as the job text for scoring.
- Added four scoring dimensions: `role_fit`, `tech_stack_fit`, `project_relevance`, and `preference_fit`.
- Added `match_score`, `match_level`, Chinese recommendation text, matched signals, missing signals, risk flags, and suggested next action.
- Added safe application write-back when `update_application=true`.
- Write-back is limited to `match_score`, `next_action`, and `risk_flags`.
- The matcher does not update `status` or `last_hr_message`.
- Added `/job_match` coverage to `scripts/api_smoke_test.py`.
- This is a candidate-side job prioritization helper, not a recruitment decision system.
- It does not call DeepSeek, call any LLM, implement RAG, apply to jobs, send HR messages, connect to recruitment platforms, use Playwright, add ML models, or add a frontend.

## Completed In Step 8

- Enhanced `POST /hr/reply` for `project_experience`, `technical_question`, and `business_proposal` intents.
- Added local context snippet selection from `candidate_profile.resume_text`, `candidate_profile.project_context`, and `candidate_profile.available_projects`.
- Added `context_used`, `selected_context_snippets`, and `context_reply_mode` to HR reply responses.
- Added conservative fallback when no profile context snippets are available.
- Kept existing truth boundary checks and forced project/technical/business proposal replies to remain human-reviewed.
- Added `app/services/context_reply_service.py` for lightweight keyword-based context selection and conservative reply rendering.
- Updated `scripts/api_smoke_test.py` to cover context-enhanced HR replies.
- This is not RAG, not Embedding, not vector search, and not an LLM call.
- The feature does not fabricate candidate experience and does not claim complete production-grade recruitment systems, automatic HR sending, or automatic recruitment decisions.

## Next Suggested Steps

1. Step 9: add RAG for project experience material.
2. Step 10: add Playwright dry-run job collection with no auto-apply.
3. Step 11: design user-confirmed semi-automation.

## Do Not Do Yet

- Do not connect to real recruitment platforms.
- Do not implement Playwright.
- Do not implement automatic HR sending.
- Do not implement automatic job application.
- Do not implement RAG.
- Do not implement Embedding or vector search.
- Do not implement a frontend.
- Do not implement LLM-based or recruitment-decision job matching in Step 8.
- Do not implement a standalone `/business_proposal` endpoint in Step 8.
- Do not call DeepSeek or any LLM from `/hr/analyze`, `/hr/reply`, or `/applications`.
- Do not automatically send HR messages.
- Do not automatically confirm interview times.
- Do not automatically update application status from `/hr/reply`.
- Do not add conversations or messages tables.
- Do not add business endpoints for the smoke test harness.
- Do not scrape job posts.
- Do not fabricate application, resume, salary, education, or project history facts.
