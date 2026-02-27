# Frontend Agent Guide

This document describes the current `frontend/` codebase so agents can make safe, minimal changes.

## Scope

- This is a standalone Next.js App Router project that currently implements a frontend-only Kanban demo.
- Main user route is `/` and renders `KanbanBoard`.
- No backend integration is present yet in this frontend package.

## Stack

- Next.js 16 + React 19 + TypeScript.
- Tailwind CSS v4 for styling (plus CSS variables in `src/app/globals.css`).
- Drag and drop via `@dnd-kit/core` and `@dnd-kit/sortable`.
- Tests:
  - Unit/component: Vitest + Testing Library.
  - E2E: Playwright.

## Current Architecture

- Entry route:
  - `src/app/page.tsx` renders `<KanbanBoard />`.
- Board state and behaviors:
  - `src/components/KanbanBoard.tsx` keeps board state in React state.
  - Supports rename column, add card, delete card, drag-and-drop move.
- Presentational/interaction components:
  - `src/components/KanbanColumn.tsx`
  - `src/components/KanbanCard.tsx`
  - `src/components/KanbanCardPreview.tsx`
  - `src/components/NewCardForm.tsx`
- Domain helpers and seed data:
  - `src/lib/kanban.ts` defines types, `initialData`, `moveCard`, `createId`.

## Styling and Theme

- Project palette is encoded in CSS custom properties in `src/app/globals.css`.
- Layout and typography are defined in `src/app/layout.tsx` and component-level utility classes.
- Keep styles consistent with existing variable usage (`--accent-yellow`, `--primary-blue`, etc.).

## Test Commands

- Install: `npm install`
- Dev server: `npm run dev`
- Unit tests: `npm run test:unit`
- E2E tests: `npm run test:e2e`
- Full frontend suite: `npm run test:all`

## Existing Test Coverage

- `src/lib/kanban.test.ts`: `moveCard` behavior.
- `src/components/KanbanBoard.test.tsx`: render, rename, add/remove card interactions.
- `tests/kanban.spec.ts`: page load, add card, drag between columns.

## Change Guidelines for Agents

- Keep changes minimal and focused on requested scope.
- Preserve current interaction behavior unless change request says otherwise.
- Prefer extending existing types/utilities in `src/lib/kanban.ts` over duplicating logic.
- If UI behavior changes, update unit tests and relevant e2e scenarios in the same task.
- Avoid adding new dependencies unless clearly necessary.
