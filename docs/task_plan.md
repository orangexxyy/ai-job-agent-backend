# Task Plan

## Current Stage

Step 17.1: clean up the documented API surface and add bilingual Swagger metadata.

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

## Completed In Step 9

- Added `docs/agent_workflow_design.md`.
- Added `docs/interview_talking_points.md`.
- Added `docs/demo_script.md`.
- Organized Step 1-8 into an Agent Workflow design view.
- Documented future LangGraph State, Nodes, Conditional Edges, and Human-in-the-loop approval boundaries.
- Added interview-facing talking points, common Q&A, design tradeoffs, project highlights, and truthful capability boundaries.
- Added a Swagger demo script with endpoint order, test JSON, talking points, and troubleshooting notes.
- Updated `README.md` with Step 9 documentation entry links and roadmap changes.
- This step is docs-only: no business code changes, no new API endpoints, no database tables, no LangGraph implementation, no RAG, no Playwright, no LLM calls.

## Completed In Step 9.5

- Added `docs/project_structure.md`.
- Added `docs/code_reading_guide.md`.
- Added concise docstrings to key public service functions.
- Standardized key function docstrings to Chinese-first wording while keeping technical terms in English.
- Documented route / schema / service / database layering.
- Documented why future workflow / LangGraph nodes should call service functions directly instead of calling internal HTTP APIs.
- Updated `README.md` with code structure and reading guide links.
- Updated `AGENTS.md` with long-term code documentation and project structure maintenance rules.
- This step does not add business features, APIs, database tables, RAG, LangGraph code, Playwright, or LLM calls.

## Next Suggested Steps

1. Step 18: error handling and retry policy.
2. Step 19: checkpoint / resume / approval interrupt design.
3. Step 20: review history / audit log.
4. Later: Playwright dry-run job collection with manual confirmation and no automatic application.

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
- Do not implement LangGraph code in Step 9.
## Completed In Step 10

- Added `POST /agent/workflow_preview`.
- Added `app/schemas/agent_schema.py`, `app/routes/agent_routes.py`, and `app/services/workflow_service.py`.
- The preview workflow loads `candidate_profile` and the target `application`.
- The preview workflow reuses `analyze_job_match(update_application=False)`.
- When `hr_message` is provided, the preview workflow reuses `analyze_hr_message` and `generate_hr_reply(update_application=False)`.
- Added `workflow_steps`, `state_summary`, `job_match`, optional `hr_intent`, optional `hr_reply`, `approval_required`, and `approved_by_user`.
- Added smoke test coverage for `/agent/workflow_preview`.
- Verified the preview workflow is read-only for application state: no `status`, `next_action`, `last_hr_message`, or `match_score` write-back.
- This step is rule-based workflow preview only, not LangGraph.
- It does not call DeepSeek / LLM, does not implement RAG, Embedding, Playwright, frontend, automatic application, automatic HR sending, or automatic interview confirmation.
## Completed In Step 11

- Added `POST /agent/langgraph_workflow_preview`.
- Added `app/services/langgraph_workflow_service.py`.
- Added minimal LangGraph `StateGraph` workflow preview.
- Reused Step 10 service capabilities: `get_candidate_profile`, `get_application`, `analyze_job_match`, `analyze_hr_message`, and `generate_hr_reply`.
- Added `WorkflowState` with application context, HR context, workflow steps, approval state, next action, error message, and debug flags.
- Added nodes: `load_profile_node`, `load_application_node`, `run_job_match_node`, `analyze_hr_intent_node`, `generate_reply_draft_node`, `require_user_approval_node`, and `handle_error_node`.
- Added conditional edges for missing `candidate_profile` and missing `application`.
- Kept `POST /agent/workflow_preview` unchanged for comparison with the LangGraph version.
- Added smoke test coverage for LangGraph workflow preview and read-only application verification.
- The LangGraph preview does not write application data, does not call DeepSeek / LLM, does not implement RAG / Embedding / Playwright, does not connect to recruitment platforms, does not auto-apply, and does not auto-send HR messages.
## Completed In Step 11.5

- Enhanced `POST /agent/langgraph_workflow_preview` observability.
- Added optional response fields: `graph_structure`, `state_snapshots`, and `edge_trace`.
- `graph_structure` exposes LangGraph nodes, normal edges, and conditional edges.
- `state_snapshots` records lightweight state changes after key nodes.
- `edge_trace` records the actual execution path and conditional decisions.
- Updated smoke test assertions for LangGraph observability fields.
- This step does not add business capability, does not add a new API, does not write application data, and does not call DeepSeek / LLM / RAG / Playwright.
## Completed In Step 11.6

- Docs-only: added `docs/workflow_langgraph_summary.md`.
- Summarized Step 10 ordinary Python `workflow_preview`, Step 11 LangGraph `workflow_preview`, and Step 11.5 LangGraph observability.
- Added the summary as a review and interview-preparation entry for README and docs.
- This step does not add business capabilities, APIs, schemas, database changes, LLM calls, RAG, Playwright, automatic sending, or automatic application.

## Completed In Step 11.7

- Docs-only: fixed `README.md` current stage from Step 9 to Step 11.6.
- Added Step 10, Step 11, Step 11.5, and Step 11.6 summaries to the README current stage section.
- Added `/agent/workflow_preview` and `/agent/langgraph_workflow_preview` to the README API list.
- Added `Step Completion Documentation Checklist` to `AGENTS.md`.
- This step does not modify business code, schemas, database structure, APIs, smoke tests, LLM calls, RAG, Playwright, automatic sending, or automatic application.

## Completed In Step 12

- Added `app/services/jd_parser_service.py` for local rule-based JD parsing.
- Added `source_type` normalization for application source / job_source.
- Added optional application fields: `jd_summary`, `jd_keywords`, `jd_required_skills`, `jd_years_requirement`, `jd_location_requirement`, and `jd_remote_type`.
- Application create/update now auto-generates JD structured fields when `source` / `job_source` or `jd_text` changes.
- Added compatible SQLite `ALTER TABLE ADD COLUMN` migration during database initialization.
- Updated smoke test to cover source normalization, JD parsing fields, and PATCH `jd_text` re-parsing.
- This step does not add automatic application, real recruitment platform access, scraping, DeepSeek / LLM calls, RAG / Embedding, Playwright, automatic HR sending, or automatic interview confirmation.

## Completed In Step 12.1

- Docs-only: synchronized the README Roadmap with the current Step 12 completion state.
- Moved future planning to Step 13 and later.
- Clarified that Playwright dry-run is a later optional direction, not Step 12.
- This step does not add business capabilities, APIs, schemas, database changes, smoke test changes, LLM calls, RAG / Embedding, Playwright, automatic sending, or automatic application.

## Completed In Step 13

- Added `POST /application_review`.
- Added `app/schemas/application_review_schema.py`, `app/routes/application_review_routes.py`, and `app/services/application_review_service.py`.
- Added a rule-based follow-up decision baseline on top of existing `job_match`, application state, JD parsed fields, optional HR intent, risk flags, and missing information.
- Returned `review_score`, `review_level`, `confidence`, `evidence`, `recommended_action`, `risk_flags`, `missing_information`, `suggested_next_message_type`, `decision_factors`, `llm_ready_context`, and debug safety flags.
- Added `confidence` as rule evidence sufficiency, not model probability.
- Added structured `evidence` for job_match, JD keywords, risk signals, missing information, HR intent, and application status.
- Added `confidence` and `evidence_summary` to `llm_ready_context` for future optional LLM enhanced review context.
- Reused `analyze_job_match(application_id, update_application=False)` so review does not write `match_score`, `next_action`, or `risk_flags`.
- Kept the API read-only for application state in this step: it does not update `status`, send HR messages, apply to jobs, or confirm interviews.
- Added smoke test coverage for normal application review, high-risk outsourcing / onsite review, and status read-only verification.
- This step does not call DeepSeek / LLM, does not implement RAG / Embedding, does not implement Playwright, does not connect to recruitment platforms, does not scrape jobs, does not auto-apply, and does not auto-send HR messages.

## Completed In Step 14

- Added `POST /application_review/llm_enhance`.
- Added `app/services/application_review_llm_service.py`.
- Implemented minimal DeepSeek-compatible Chat Completions support in `app/services/llm_service.py`.
- The LLM enhanced review first calls the rule-based `review_application(update_application=False)`.
- The prompt requires the model to distinguish raw facts, rule inference, and LLM suggestions.
- Returned `rule_review`, optional `llm_enhanced_review`, `llm_used`, `llm_error`, `human_review_required`, and safety debug fields.
- When `DEEPSEEK_API_KEY` is missing, the API keeps `rule_review`, returns `llm_used=false`, and reports `api_key_missing` without crashing.
- Added smoke test coverage for `/application_review/llm_enhance` without requiring a real API key.
- This step does not generate a full HR reply draft, does not write application review history, does not update application status / next_action / risk_flags, does not auto-send messages, does not auto-apply, does not confirm interviews, does not implement RAG / Embedding / Playwright, and does not connect to recruitment platforms.

## Completed In Step 15

- Added `POST /application_review/hr_reply_draft`.
- Added `app/services/hr_reply_draft_llm_service.py`.
- The endpoint converts application review and optional LLM enhanced review into a human-reviewable HR reply draft.
- Added draft types: `confirm_details`, `project_intro`, `interview_schedule`, `salary_expectation`, `polite_decline`, and `general_follow_up`.
- Added conservative `rule_fallback` draft when API key is missing, network fails, or LLM JSON parsing fails.
- Returned `draft_source`, `draft_type`, `draft_text`, `draft_goal`, `must_confirm_before_send`, `risk_notes`, `safe_to_send`, `human_review_required`, `rule_review`, optional `llm_enhanced_review`, `llm_used`, and `llm_error`.
- Added smoke test coverage for `/application_review/hr_reply_draft` without requiring a real API key.
- This step does not send HR messages, does not auto-apply, does not confirm interviews, does not update application status / next_action / risk_flags, does not add review history tables, does not implement RAG / Embedding / Playwright, and does not connect to recruitment platforms.

## Refined In Step 15

- Changed `/application_review/hr_reply_draft` to return both `reply_strategy_for_user` and `hr_reply_draft`.
- Step 15 now defaults to `review_application(update_application=False)` directly and no longer calls Step 14 `/application_review/llm_enhance` by default.
- Added debug flags: `analysis_and_draft_combined=true` and `step14_llm_enhance_called=false`.
- Adjusted `draft_type` resolution to prioritize HR intent, then `suggested_next_message_type`, risk / missing information, and application status.
- Kept Step 14 as an independent user-facing analysis enhancement endpoint.
- This refinement does not add sending, automatic application, status updates, review history, RAG / Embedding, Playwright, or recruitment platform access.

## Completed In Step 16

- Enhanced `POST /agent/langgraph_workflow_preview`.
- Replaced the older LangGraph node chain with: `load_profile_node`, `load_application_node`, `run_application_review_node`, `generate_hr_reply_package_node`, `require_user_approval_node`, and `handle_error_node`.
- Added `application_review` to the LangGraph response by reusing `review_application(update_application=False)`.
- Added `hr_reply_package`, `reply_strategy_for_user`, and `hr_reply_draft` to the LangGraph response by reusing Step 15 `generate_hr_reply_draft_from_review`.
- Added `node_debug` to show each node's LLM usage, database read/write boundary, external API call flag, status, and draft source.
- Kept Step 14 `/application_review/llm_enhance` as an independent endpoint; Step 16 does not require calling it.
- Updated smoke test coverage for the new LangGraph node chain and read-only boundary.
- The workflow may call DeepSeek-compatible LLM only through Step 15 HR reply package when an API key is configured; without API key it falls back to `rule_fallback`.
- This step does not write application data, does not update application status / next_action / risk_flags / last_hr_message, does not send HR messages, does not auto-apply, does not confirm interviews, does not add review history tables, does not implement RAG / Embedding / Playwright, and does not connect to recruitment platforms.

## Completed In Step 16.5

- Docs-only: added `docs/architecture_review_step16.md`.
- Summarized current project positioning, completed capabilities, core APIs, and Step 13 / 14 / 15 / 16 responsibility boundaries.
- Documented the current LangGraph node chain, plus `state`, `node`, `edge`, `node_debug`, and `edge_trace`.
- Explained why Step 15 does not call Step 14 by default.
- Documented Human-in-the-loop safety boundaries and why the project is not yet production-grade or enterprise-grade.
- Updated `docs/demo_script.md` with three validation routes: outsourcing / onsite risk confirmation, project experience reply, and interview time scenario.
- Updated `docs/interview_talking_points.md` with 30-second and 2-minute project introductions, LangGraph rationale, no-auto-send rationale, Step 14 vs Step 15, and enterprise gap discussion.
- Updated `README.md` current stage, architecture summary, limitations, and architecture document entry.
- Adjusted Next Suggested Steps to Step 17-20.
- This step does not add business capabilities, APIs, schemas, database changes, smoke test changes, LLM calls, RAG / Embedding, Playwright, automatic sending, or automatic application.

## Completed In Step 16.7

- Fixed project introduction fact boundary for `project_intro` HR reply drafts.
- Added explicit separation between the RAG enterprise knowledge base project and AI Job Agent project.
- Added lightweight project fact boundary fallback when generated project intro drafts mix forbidden claims, such as "AI Job Agent uses RAG retrieval" or "RAG project uses LangGraph".
- Added `interview_availability_slots` SQLite table for manually maintained interview availability.
- Added `POST /interview_availability_slots`, `GET /interview_availability_slots`, and `PATCH /interview_availability_slots/{slot_id}`.
- Updated `interview_schedule` HR reply draft logic to read available slots.
- When no available slots exist, interview schedule drafts ask to confirm the user's calendar first and do not invent time ranges.
- When available slots exist, interview schedule drafts can only offer those slots and still require human confirmation.
- Updated smoke test coverage for project fact boundaries, interview schedule with / without slots, and LangGraph approval safety.
- This step does not connect Google Calendar, does not connect recruitment platforms, does not auto-send HR messages, does not auto-apply, does not auto-confirm interviews, does not implement RAG / Embedding, and does not make the project production-grade.

## Completed In Step 16.7B

- Hardened `interview_availability_slots` duplicate handling.
- `POST /interview_availability_slots` now rejects duplicate `date + start_time + end_time + timezone` slots with 409 Conflict.
- `GET /interview_availability_slots` still defaults to `status=available` and now supports `status=all`.
- HR reply draft continues to use only `status=available` slots.
- `available_slots_used` includes slot `id` and deduplicates historical duplicate slots by time range.
- Added `POST /interview_availability_slots/{slot_id}/book` to mark an available / held slot as `booked` after user confirmation.
- Booking a slot is only an internal state marker: it does not send HR messages, does not auto-confirm interviews, does not update application status, and does not connect external calendars.
- Updated smoke test coverage for duplicate prevention, slot id visibility, booked slot exclusion, and safety flags.
- This step does not connect Google Calendar, Feishu Calendar, OAuth, real recruitment platforms, automatic calendar conflict detection, automatic HR sending, automatic application, or automatic interview confirmation.

## Completed In Step 16.8

- Docs-only: added `docs/real_world_design_notes.md`.
- Documented three real-world engineering design cases: rule-level chunk design in the companion RAG project, `candidate_profile` fact-source governance, and `interview_availability_slots` state management.
- Added the document as a README entry for resume and interview review.
- This step does not add business capabilities, APIs, database changes, LLM calls, RAG / Embedding, MCP, Google Calendar, automatic HR sending, automatic application, or automatic interview confirmation.

## Completed In Step 17

- Added `POST /applications/{application_id}/confirm_hr_reply` for explicit user confirmation after an HR reply is handled manually.
- Kept `/application_review/hr_reply_draft` read-only; draft generation does not update application state.
- Confirmation updates `status=hr_replied`, `next_action`, optional `last_hr_message`, `updated_at`, and appends the confirmed draft plus `sent_channel=manual` to existing `notes`.
- Reused existing application fields and added no database columns or tables.
- Added 404 handling for missing applications, 422 handling for blank drafts, duplicate confirmation protection, and 409 protection for terminal statuses.
- Updated smoke test coverage for the read-only draft boundary, confirmation writes, safety debug fields, error handling, repeat confirmation, and terminal-state protection.
- This step does not auto-send HR messages, auto-apply, auto-confirm interviews, or connect to recruitment or communication platforms.

## Completed In Step 17.1

- Added bilingual Swagger summary / description metadata for the current main-flow APIs.
- Marked `/hr/analyze`, `/hr/reply`, and `/agent/workflow_preview` as deprecated Legacy interfaces without deleting them.
- Added OpenAPI tag metadata for health, profile, applications, application review, interview availability, agent, HR Legacy, and job match groups.
- Added `docs/api_surface_guide.md` to distinguish main-flow, Legacy, and Debug / Preview APIs.
- Updated README, Demo, API examples, interview talking points, code reading guidance, and real-world design notes.
- This step changes API documentation only. It does not change business logic, database structure, external communication, automatic application, or automatic interview confirmation.

## Completed In Resume-Input-01

- Added `scripts/extract_resume_text.py` for local resume text extraction.
- Supports `.docx`, text-based `.pdf`, `.txt`, and `.md` input files.
- Generates `docs/input/current_resume.txt` without rewriting, summarizing, or calling LLM.
- Generates `docs/input/resume_extract_report.md` with input path, file type, output path, extracted character count, PDF page count when applicable, suspected scanned-PDF flag, and next-step suggestions.
- Added `docs/input/resume_source/sample_resume.md` as a minimal local test fixture.
- Added `python-docx` and `pypdf` to `requirements.txt` for docx and text-based PDF extraction.
- Documented that `current_resume.txt` can later support `candidate_profile.resume_text`, `project_context`, and `truth_boundaries`.
- This step does not write database data, does not update `candidate_profile`, does not modify HR reply logic, does not call LLM, does not do OCR, and does not add frontend upload.
