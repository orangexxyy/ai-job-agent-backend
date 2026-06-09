# AI Job Agent Design

## Project Positioning

AI Job Agent is a human-in-the-loop assistant for AI application developer job search workflows. It helps a candidate store explicit profile facts, prepare safe HR replies, analyze job descriptions, generate business proposal drafts, and track applications.

The project is not an automatic mass-apply script. It does not connect to real recruitment platforms in Step 1, does not send messages automatically, does not confirm interviews automatically, and does not fabricate candidate experience.

## Step 1 MVP Scope

Step 1 only implements:

- FastAPI project skeleton
- `GET /health`
- SQLite database initialization
- `candidate_profile` table
- `POST /profile`
- `GET /profile`
- `.env.example`
- initial documentation
- placeholder `llm_service.py`

Step 1 intentionally does not implement RAG, Playwright, frontend, automatic application, automatic HR messaging, or real LLM calls.

## Module Design

- `routes/`: HTTP API entry points.
- `schemas/`: Pydantic request and response models.
- `services/`: business logic and future LLM orchestration.
- `database.py`: SQLite connection and initialization.
- `models.py`: table creation SQL.
- `config.py`: environment-based settings.
- `docs/`: design notes, task plan, and API examples.

## Candidate Profile First

Fixed preference questions must read from `candidate_profile` instead of letting the model guess. This includes salary, availability, preferred cities, relocation, outsourcing, onsite work, remote work, overtime, business trips, target roles, available projects, and truth boundaries.

## Human In The Loop

All external actions require user confirmation:

- Sending HR messages
- Confirming interview times
- Salary negotiation
- Accepting or rejecting roles
- Applying to jobs

The system can generate drafts and suggestions, but the user remains the final decision maker.

## Truth Boundary

The agent must not claim experience that the candidate did not provide. It must distinguish:

- Completed work
- Learning experience
- Demonstration projects
- Future expansion plans

The agent must not turn future roadmap items into finished experience.

## Future Roadmap

- Step 2: HR intent classifier and reply draft service
- Step 3: job match scorer
- Step 4: business proposal agent
- Step 5: truth boundary checker
- Step 6: project-experience RAG
- Step 7: Playwright dry-run job collection
- Step 8: user-confirmed semi-automatic application support
