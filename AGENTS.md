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
