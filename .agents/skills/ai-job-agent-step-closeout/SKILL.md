---
name: ai-job-agent-step-closeout
description: Close out an AI Job Agent project Step with test verification, documentation synchronization, Human-in-the-loop and factual-boundary review, privacy checks, Git diff/status inspection, and a standardized acceptance report. Use after implementing or documenting any Step, when asked to验收、收口、完成阶段、同步文档、检查事实边界，or before reporting a Step as complete in this repository.
---

# AI Job Agent Step Closeout

Run a consistent closeout for each project Step without overstating capabilities or exposing private data. This skill verifies and reports; it does not authorize unrelated changes, external actions, `git commit`, or `git push`.

## 1. Load Required Context

Read, in order:

1. Project-root `AGENTS.md`.
2. `README.md`.
3. `docs/task_plan.md`.
4. `WORK_HANDOFF_AI_JOB_AGENT.md` when it exists locally.

Treat the handoff file as private local context. Extract only task-relevant instructions, never reproduce personal content in public documentation or reports, ensure it is ignored by Git, and never stage or commit it.

When `WORK_HANDOFF_AI_JOB_AGENT.md` exists, run `git check-ignore --quiet -- WORK_HANDOFF_AI_JOB_AGENT.md`. If Git does not ignore it, report the privacy risk only. Do not modify `.gitignore` without explicit user approval.

## 2. Establish Scope and Baseline

- Confirm the Step number, requested behavior, and prohibited areas.
- Inspect `git status --short` before closeout and preserve pre-existing user changes.
- Separate files changed for the Step from unrelated existing changes.
- Do not read or modify `.env`, `data/`, `docs/input/`, real resumes, or private generated files.

## 3. Verify Tests

- Select checks proportional to the changed behavior and follow `AGENTS.md`.
- Run relevant syntax, unit, integration, or smoke checks unless the user explicitly forbids tests or the environment blocks them.
- Record every command and its result. Distinguish `passed`, `failed`, `blocked`, and `not run`.
- Never describe an unrun or failing check as passed.
- Do not call real recruitment platforms or perform external job-search actions during verification.

## 4. Failure Handling and Optional Bounded Remediation

Default to **verification-only**. Report failures and blockers without modifying code, tests, documentation, configuration, or data.

Enter the remediation loop only when the user explicitly asks to “修复并收口” or otherwise clearly authorizes fixes. In each remediation round:

1. Locate the failure from actual test output; do not infer or invent a passing result.
2. Determine whether the failure was introduced by the current Step.
3. Make only the smallest fix within the confirmed current Step scope.
4. Rerun the failed test and relevant regression tests.

Run at most two automated remediation rounds. Stop immediately and request user confirmation before any action that would:

- expand the current Step scope;
- modify unrelated pre-existing user changes;
- add or upgrade dependencies;
- change the database schema;
- read protected or private files;
- use the network or an external platform;
- weaken Human-in-the-loop or other safety boundaries.

If tests still fail after two remediation rounds, stop and report the blocker. Do not declare the Step complete. Remediation mode never authorizes staging, committing, or pushing.

## 5. Synchronize Documentation

Always check:

- `README.md`: current stage, API list, documentation links, limitations.
- `docs/task_plan.md`: completed Step and truthful boundaries.
- `docs/api_examples.md`: when an endpoint changes.
- `docs/demo_script.md`: when the demo flow changes.
- `docs/interview_talking_points.md`: when project presentation changes.
- `docs/code_reading_guide.md`: when important files or reading order change.
- `docs/project_structure.md`: when a route, schema, service, or workflow file is added.
- `docs/agent_workflow_design.md`: when Agent or LangGraph behavior changes.
- `scripts/api_smoke_test.py`: when a main-chain API changes.

List documents updated separately from documents checked but not needing updates. Keep documentation in Chinese by default and preserve established English technical terms.

## 6. Check Safety, Facts, and Privacy

- Confirm external messages, applications, interview confirmation, salary commitments, and platform operations remain Human-in-the-loop.
- Confirm simulated actions are not described as real actions.
- Describe the project as a rule-driven Human-in-the-loop Agentic Workflow, not a complete Tool-Using Agent or production-grade autonomous job-search Agent.
- Do not claim RAG, Embedding, Playwright, production authorization, real platform access, or autonomous execution unless they are actually implemented.
- Do not fabricate candidate experience, education, address, work years, salary, projects, test evidence, or feature status.
- Check changed paths and diffs for `.env`, API keys, tokens, passwords, private handoff content, real resumes, `docs/input/`, `data/`, and private generated files. Stop and report exposure without reproducing the sensitive value.

## 7. Run Final Git Checks

Run:

```text
git diff --check
git diff --stat
git status --short
```

Inspect the relevant diff for unintended files and boundary violations. Do not stage, commit, push, or create a remote unless the user separately and explicitly authorizes it.

## 8. Produce the Acceptance Report

Use these headings and include every item:

1. **修改文件列表** — Step files only; identify unrelated pre-existing changes separately.
2. **核心修改说明** — concise behavior and design summary.
3. **测试命令和结果** — exact commands plus passed, failed, blocked, or not run.
4. **更新的文档** — list each updated document and why.
5. **检查但无需更新的文档** — list each checked document and why no update was needed.
6. **`git diff --stat`** — include the actual output or a faithful concise rendering.
7. **`git status --short`** — include the actual output and identify newly untracked files.
8. **未解决问题** — include known failures, blockers, follow-ups, or `无`.
9. **当前真实能力边界** — state implemented and unimplemented boundaries truthfully, including Human-in-the-loop limits.
10. **是否执行 commit / push** — explicitly state both results; default to neither executed.

Do not report the Step complete while required checks are failing or while a material known issue contradicts completion. Report the exact blocker instead.
