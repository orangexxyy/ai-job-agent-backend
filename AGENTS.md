# AI Coding Agent Rules

This project is an AI Job Agent for human-in-the-loop job search assistance. Future Codex, Claude Code, or other AI coding tools must follow these rules.

## Hard Boundaries

- Do not copy third-party project source code.
- Do not connect to real recruitment platforms unless the user explicitly asks in a later approved phase.
- Do not implement CAPTCHA bypass, anti-crawling bypass, risk-control bypass, or platform restriction bypass.
- Do not automatically send HR messages.
- Do not automatically apply to jobs.
- Do not fabricate candidate experience, education, address, work years, salary, or project history.
- Do not commit real API keys.
- Put API keys only in `.env`.

## Workflow Rules

- Explain the plan before each meaningful change.
- Implement one small feature at a time.
- Keep Step 1 focused on the FastAPI skeleton and `candidate_profile`.
- Update `README.md` and `docs/task_plan.md` when important behavior changes.
- Provide test commands after changes.
- Prefer simple, readable implementations before adding frameworks or abstractions.

## Current Scope

Allowed in Step 1:

- FastAPI skeleton
- SQLite initialization
- `candidate_profile` save and read
- Placeholder LLM service wrapper
- Basic docs

Not allowed in Step 1:

- `/job_match` full logic
- `/business_proposal` full logic
- `/hr/reply` full logic
- Playwright
- RAG
- Frontend
- Real DeepSeek calls

## Project-scoped Autonomy Mode / 项目范围内自主开发模式

AI Coding tools may work with higher autonomy inside the project directory:

```text
D:\software\Code\ai_job_agent
```

This autonomy only applies inside this project, only within the currently confirmed Step scope, and only while respecting the boundaries below.

### Allowed Autonomous Actions

- Read all non-sensitive files in this project.
- Create and modify relevant ordinary code files inside this project directory for the current Step.
- Create and modify relevant documentation files for the current Step.
- Create and update test files or test examples for the current Step.
- Modify `app/routes`, `app/services`, `app/schemas`, `docs`, and `README.md` when they are related to the current Step.
- Fix import errors, type errors, syntax errors, and path errors.
- Run local commands such as:
  - `python -m py_compile ...`
  - `python -m uvicorn app.main:app --reload`
  - `python -m pytest`
- Update `docs/task_plan.md` and `docs/api_examples.md`.
- Complete small changes autonomously within the currently confirmed Step scope without asking the user about every related file.

### Actions That Require User Confirmation

- Add third-party dependencies or modify `requirements.txt`.
- Modify database table structure or run data migrations.
- Delete files, delete directories, clear the database, or delete the `data` directory.
- Create, modify, or read `.env`.
- Write any API Key, token, account, or password.
- Access real recruitment platforms.
- Implement Playwright automation.
- Implement automatic job application.
- Implement automatic HR message sending.
- Implement automatic interview time confirmation.
- Change the overall project architecture or perform a large-scale refactor.
- Run `git commit`, `git push`, or create a remote repository.
- Describe unimplemented features as implemented capabilities.
- Generate resume, README, or interview wording that may exaggerate the user's experience.

### Step Completion Output Requirements

After each Step, output:

- modified file list
- core implementation summary
- test commands
- current unimplemented boundaries
- suggested next step

### Long-term Principles

- Do one Step at a time.
- Any feature involving real external communication, job-search commitments, salary negotiation, interview time confirmation, or automatic message sending must stay human-in-the-loop.
- The project may reference third-party GitHub projects for feature ideas, but must not copy source code.
- The project should primarily support AI application development / LLM application development job-search presentation.
- All resume, README, interview, and project-presentation wording must remain truthful and must not exaggerate implemented capabilities or user experience.

## Code Documentation and Project Structure Rules

1. Project docstrings and project documentation should use Chinese by default, while keeping technical terms such as FastAPI, SQLite, LLM, RAG, LangGraph, Playwright, and Human-in-the-loop in English.

2. Variable names, function names, class names, and file names must remain in English.

3. Every new public service function must include a concise Chinese docstring explaining the function purpose, main inputs, main outputs, and whether it writes to the database or has other side effects.

4. Every time an existing core service function's responsibility changes, update its docstring in the same change.

5. If a function touches Human-in-the-loop boundaries, database writes, external communication, LLM, RAG, LangGraph, Playwright, automatic application, or automatic HR messaging, mention the relevant boundary in the docstring or a nearby concise comment.

6. Every time a new route, schema, service, or workflow file is added, update `docs/project_structure.md`.

7. If a new file changes the recommended code reading order, update `docs/code_reading_guide.md`.

8. Every time an API endpoint is added or changed, update `README.md`, `docs/api_examples.md`, and `docs/demo_script.md`.

9. If the API endpoint belongs to the main workflow path, update `scripts/api_smoke_test.py`.

10. Every time a new project Step is added, update the current stage section in `README.md` and update `docs/task_plan.md`.

11. Every time Agent workflow or LangGraph-related capability is added, update `docs/agent_workflow_design.md` and `docs/interview_talking_points.md`.

12. Keep comments concise. Do not comment every line. Focus comments and docstrings on core functions, complex business rules, state transitions, permission boundaries, and Human-in-the-loop boundaries.

13. Do not implement code without updating the corresponding documentation, unless the task is explicitly a one-off experiment and will not enter the main project line.

## Step Completion Documentation Checklist

After every project Step, AI coding tools must check and update the related documentation before reporting completion.

Required checks:

1. `README.md` current stage must match the latest completed Step.

2. `README.md` API list must include any newly added or changed API endpoints.

3. `README.md` documentation entry section must include important new docs.

4. `docs/task_plan.md` must record the completed Step and its truthful boundaries.

5. `docs/api_examples.md` must be updated if an API endpoint is added or changed.

6. `docs/demo_script.md` must be updated if the demo flow changes.

7. `docs/interview_talking_points.md` must be updated if the Step affects interview explanation or project presentation.

8. `docs/code_reading_guide.md` must be updated if important files, modules, or reading order change.

9. `docs/agent_workflow_design.md` must be updated if the Step affects Agent workflow or LangGraph workflow design.

10. `scripts/api_smoke_test.py` must be updated if a main-chain API is added or changed.

Step completion output must include:

- which documents were updated
- which documents were checked and did not need updates
- whether `README.md` current stage is synchronized
- whether there are newly untracked files
- `git diff --stat`

These checks do not permit exaggerating unfinished capabilities. Documentation must keep Human-in-the-loop boundaries clear and must not describe DeepSeek / LLM, RAG, Playwright, real recruitment platform access, automatic application, automatic HR messaging, or automatic interview confirmation as implemented unless they truly are.
