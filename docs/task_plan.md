# Task Plan

## Current Stage

Step 5: `/hr/reply` application context.

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

## Next Suggested Steps

1. Step 6: add job match scoring after the manual application records are stable.
2. Step 7: use `resume_text` / `project_context` to enhance reply drafts while staying truthful.
3. Step 8: add RAG for project experience material.
4. Step 9: add Playwright dry-run job collection with no auto-apply.
5. Step 10: design user-confirmed semi-automation.

## Do Not Do Yet

- Do not connect to real recruitment platforms.
- Do not implement Playwright.
- Do not implement automatic HR sending.
- Do not implement automatic job application.
- Do not implement RAG.
- Do not implement a frontend.
- Do not implement `/job_match` or `/business_proposal` in Step 5.
- Do not call DeepSeek or any LLM from `/hr/analyze`, `/hr/reply`, or `/applications`.
- Do not automatically send HR messages.
- Do not automatically confirm interview times.
- Do not automatically update application status from `/hr/reply`.
- Do not add conversations or messages tables.
- Do not scrape job posts.
- Do not fabricate application, resume, salary, education, or project history facts.
