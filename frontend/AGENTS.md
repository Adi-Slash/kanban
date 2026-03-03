# Frontend Agent Guide

This document describes the current `frontend/` codebase so agents can make safe, minimal changes.

## Scope

- This is a Next.js App Router project for the frontend experience.
- Main user route is `/` and renders `KanbanApp`.
- The app is backend-backed via `/api/*` with local fallback behavior when board load fails.

## Stack

- Next.js 16 + React 19 + TypeScript.
- Tailwind CSS v4 for styling (plus CSS variables in `src/app/globals.css`).
- Drag and drop via `@dnd-kit/core` and `@dnd-kit/sortable`.
- Tests:
  - Unit/component: Vitest + Testing Library.
  - E2E: Playwright.

## Current Architecture

- Entry route:
  - `src/app/page.tsx` renders `<KanbanApp />`.
- App flow:
  - `src/components/KanbanApp.tsx` manages auth flow and view routing:
    - Login view, Register view, Board list view, Board view
  - After authentication, user sees board list
  - Clicking a board opens the Kanban board view
- Board list:
  - `src/components/BoardList.tsx` shows user's boards with create, rename, and delete
- Board state and behaviors:
  - `src/components/KanbanBoard.tsx` takes `boardId` prop, loads board from backend
  - Supports rename column, add card (with priority/due date), update card, delete card, drag-and-drop move
  - Card detail modal for editing title, details, priority, due date, and labels
  - Right-sidebar AI chat UI scoped to the current board
- Card features:
  - `src/components/KanbanCard.tsx` shows labels, priority badge, due date
  - `src/components/CardDetailModal.tsx` for full card editing
- Presentational/interaction components:
  - `src/components/KanbanColumn.tsx`
  - `src/components/KanbanCardPreview.tsx`
  - `src/components/NewCardForm.tsx` (with priority and due date fields)
- Domain helpers:
  - `src/lib/kanban.ts` defines types (Card, Column, BoardData, BoardSummary, Label), `moveCard`, `createId`, `priorityColors`
  - `src/lib/api.ts` defines typed API clients for auth, boards, cards, labels, and AI chat
  - `src/lib/auth.ts` wraps API auth calls

## Styling and Theme

- Project palette is encoded in CSS custom properties in `src/app/globals.css`.
- Keep styles consistent with existing variable usage (`--accent-yellow`, `--primary-blue`, etc.).

## Test Commands

- Install: `npm install`
- Dev server: `npm run dev`
- Unit tests: `npm run test:unit`
- E2E tests: `npm run test:e2e`
- Full frontend suite: `npm run test:all`

## Existing Test Coverage

- `src/lib/kanban.test.ts`: `moveCard` behavior.
- `src/lib/auth.test.ts`: credential validation, registration, auth verification.
- `src/components/KanbanApp.test.tsx`: login/logout/register flow, board list navigation.
- `src/components/KanbanBoard.test.tsx`: render, rename, add/remove card, back navigation.
- `src/components/KanbanBoard.api.test.tsx`: backend load/fallback behavior.
- `src/components/KanbanBoard.chat.test.tsx`: AI chat send/error UX and board refresh from AI response.
- `tests/kanban.spec.ts`: Playwright E2E tests.

## Change Guidelines for Agents

- Keep changes minimal and focused on requested scope.
- Preserve current interaction behavior unless change request says otherwise.
- Prefer extending existing types/utilities in `src/lib/kanban.ts` over duplicating logic.
- If UI behavior changes, update unit tests and relevant e2e scenarios in the same task.
- Avoid adding new dependencies unless clearly necessary.
