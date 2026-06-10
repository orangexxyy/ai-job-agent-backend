# Task Plan

## Current Stage

Step 4: Applications tracking.

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

## Next Suggested Steps

1. Step 5 option A: add focused tests for `/applications`, `/hr/analyze`, and `/hr/reply`.
2. Step 5 option B: expand truth boundary rules before adding richer technical/project answers.
3. Step 5 option C: enhance `/hr/reply` with LLM Service plus `project_context`, while keeping human approval and no automatic sending.
4. Step 6: add job match scoring after the manual application records are stable.

## Do Not Do Yet

- Do not connect to real recruitment platforms.
- Do not implement Playwright.
- Do not implement automatic HR sending.
- Do not implement automatic job application.
- Do not implement RAG.
- Do not implement a frontend.
- Do not implement `/job_match` or `/business_proposal` in Step 4.
- Do not call DeepSeek or any LLM from `/hr/analyze`, `/hr/reply`, or `/applications`.
- Do not automatically send HR messages.
- Do not scrape job posts.
- Do not fabricate application, resume, salary, education, or project history facts.
