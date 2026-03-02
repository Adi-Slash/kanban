# Project Plan

This document defines the execution plan for the MVP. Work is done in ordered phases, with explicit test gates and success criteria.

## Agreed Constraints

- Frontend: Next.js app in `frontend/` (existing demo codebase).
- Backend: FastAPI app in `backend/`.
- Packaging/runtime: single local Docker container.
- Python package manager in container: `uv`.
- Database: normalized SQLite schema (not a single board JSON blob).
- Auth MVP: hardcoded credentials `user` / `password`, cookie/session flow only.
- AI provider/model: OpenRouter using `openai/gpt-oss-120b`.
- Tests: simplest best-practice stack (`pytest` for backend, existing `vitest` + `playwright` for frontend).

## Phase 1 - Planning and Baseline Documentation

### Checklist

- [x] Expand `docs/PLAN.md` into phased checklists with test gates and success criteria.
- [x] Add `frontend/AGENTS.md` that documents the current frontend architecture and conventions.
- [x] User review and approval of this plan before implementation phases.

### Tests

- Documentation quality check: all phases include actionable tasks, tests, and clear completion criteria.

### Success Criteria

- Plan is approved by user.
- No implementation/scaffolding work starts before approval.

---

## Phase 2 - Scaffolding (Docker + FastAPI hello world)

### Checklist

- [x] Create `backend/` FastAPI service with minimal app entrypoint.
- [x] Create Dockerfile and compose/setup for local single-container run.
- [x] Add start/stop scripts in `scripts/` for Windows, macOS, Linux.
- [x] Serve a simple static HTML page (temporary smoke page) from backend.
- [x] Add one sample API route and confirm frontend/static page can call it.

### Tests

- Backend unit test: hello API returns expected JSON/status.
- Container smoke test: container builds and starts cleanly.
- Manual smoke: open root URL and verify page + API call both work.

### Success Criteria

- `docker` run path works locally from clean checkout.
- Root URL and sample API are reachable and stable.

---

## Phase 3 - Integrate Existing Frontend Build into Backend Serving

### Checklist

- [x] Build Next.js frontend for production.
- [x] Configure backend/container to serve built frontend at `/`.
- [x] Remove/replace temporary scaffold page with real Kanban UI delivery.
- [x] Ensure static asset routing is correct in containerized runtime.

### Tests

- Frontend unit tests: `npm run test:unit`.
- Frontend e2e tests: `npm run test:e2e`.
- Runtime smoke test: root route shows Kanban board in containerized app.

### Success Criteria

- Kanban demo appears at `/` from backend-served app.
- Existing frontend tests pass in CI/local flow.

---

## Phase 4 - MVP Sign-In and Sign-Out Flow

### Checklist

- [x] Add login page/view shown before board access.
- [x] Implement hardcoded credential check (`user` / `password`).
- [x] Add simple session/cookie handling and protected root flow.
- [x] Add logout action that clears session and redirects to login.

### Tests

- Frontend unit/integration tests for login form behavior and validation.
- Backend/session tests for auth guard behavior if auth is enforced server-side.
- E2E tests: unauthenticated redirect, successful login, logout.

### Success Criteria

- Unauthenticated users cannot access board.
- Valid credentials unlock board; logout reliably returns to login.

---

## Phase 5 - Database Schema Design and Sign-Off

### Checklist

- [x] Design normalized SQLite schema for users, boards, columns, cards, and ordering.
- [x] Document schema and migration/bootstrap approach in `docs/`.
- [x] Define strategy to produce board JSON view from normalized tables for UI and AI context.
- [x] Review schema tradeoffs with user and get explicit sign-off before API implementation.

### Tests

- Schema validation tests (migration/bootstrap + relational integrity basics).
- Persistence smoke test (create/read sample board data).

### Success Criteria

- User explicitly approves schema documentation.
- Database creation path is deterministic on first run.

---

## Phase 6 - Backend Kanban API (Persistent CRUD)

### Checklist

- [x] Implement API routes to read/update Kanban state per user.
- [x] Add repository/service layer for SQLite access and mapping.
- [x] Ensure DB auto-creates on first startup if missing.
- [x] Add robust request/response models and validation.

### Tests

- `pytest` unit tests for service/repository logic.
- API tests for happy paths and key failures (invalid IDs/payloads).
- Startup test verifies DB initialization path.

### Success Criteria

- Backend supports persistent Kanban load/update per signed-in user.
- Backend test suite passes with good core coverage.

---

## Phase 7 - Frontend Connected to Backend APIs

### Checklist

- [ ] Replace local in-memory board state with backend-backed state loading/saving.
- [ ] Wire board actions (rename/add/move/delete) to API calls.
- [ ] Add loading/error UX for request failures.
- [ ] Preserve existing board interaction behavior and polish.

### Tests

- Frontend unit/integration tests with mocked API client.
- E2E tests for persistence across refresh.
- Contract checks for frontend/backend payload compatibility.

### Success Criteria

- Board operations persist via backend and survive reload.
- Existing user-visible board behavior remains correct.

---

## Phase 8 - AI Connectivity (OpenRouter Smoke)

### Checklist

- [ ] Implement backend OpenRouter client configuration from `.env`.
- [ ] Add minimal AI endpoint/service with `"2+2"` connectivity check flow.
- [ ] Add timeout/error handling and clear failure responses.

### Tests

- Unit tests for request builder and response parsing.
- Optional integration smoke test (enabled when API key present).
- Manual verification: AI endpoint returns expected response shape.

### Success Criteria

- Backend can make successful OpenRouter call with configured model.
- Errors are surfaced cleanly when key/network/model fail.

---

## Phase 9 - Structured AI Output with Optional Board Mutations

### Proposed Structured Output (for sign-off)

```json
{
  "assistant_message": "string",
  "operations": [
    {
      "type": "create_card | update_card | move_card | delete_card | rename_column",
      "column_id": "string (required for create/move target/rename)",
      "card_id": "string (required except create)",
      "title": "string (optional)",
      "details": "string (optional)",
      "before_card_id": "string|null (optional for move ordering)"
    }
  ]
}
```

### Checklist

- [x] Finalize and approve structured output schema.
- [ ] Send board JSON snapshot + user message + conversation history to model.
- [ ] Validate model JSON output strictly before applying operations.
- [ ] Apply valid operations transactionally; reject/ignore invalid ops safely.
- [ ] Return assistant message + resulting board state to frontend.

### Tests

- Unit tests for structured output validation and operation application rules.
- Transaction tests: all-or-nothing mutation behavior.
- Failure tests: malformed model output does not corrupt persisted state.

### Success Criteria

- AI responses are parseable, validated, and safely mapped to board mutations.
- Board remains consistent under malformed or partial AI outputs.

---

## Phase 10 - Sidebar AI Chat UX with Live Board Refresh

### Checklist

- [ ] Add right-sidebar AI chat UI integrated into board experience.
- [ ] Implement message history, send state, and error state UX.
- [ ] On AI mutation operations, refresh/reconcile board state automatically.
- [ ] Keep UI aligned with project color/design language.

### Tests

- Frontend unit/integration tests for chat interactions and rendering.
- E2E tests for full loop: ask AI -> receive response -> board updates when operations returned.
- Regression checks for drag/drop and manual edits after AI updates.

### Success Criteria

- User can chat with AI from sidebar and receive reliable responses.
- AI-driven board updates appear automatically and remain consistent.

---

## Global Definition of Done

- [ ] All phase tests pass for the completed phase before moving forward.
- [ ] Docs updated when architecture/behavior changes.
- [ ] Simplicity maintained (no over-engineering, no extra scope).
- [ ] Root-cause-first debugging approach used for all defects.