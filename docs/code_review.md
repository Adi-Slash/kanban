# Code Review: Project Management MVP

## Summary

The project implements a functional Kanban board with AI-assisted features. The codebase follows a Next.js frontend + Python FastAPI backend architecture with SQLite storage. Overall, the code is well-organized and achieves the MVP requirements.

---

## Strengths

- **Clean separation of concerns**: Backend uses repository pattern with clear layer separation (`db.py`, `repository.py`, `ai.py`, `factory.py`)
- **Frontend state management**: React components properly manage local state with fallback behavior when backend is unavailable
- **Database schema**: Proper use of foreign keys, indices, and cascading deletes
- **Error handling**: Both frontend and backend have comprehensive error handling with user-friendly messages
- **Drag-and-drop**: Well-implemented using `@dnd-kit` with visual feedback

---

## Issues and Recommendations

### Security

1. **Hardcoded credentials** (`backend/app/db.py:138`, `frontend/src/lib/auth.ts:5`)
   - **Status**: FIXED (documented limitation)
   - Password stored in plaintext: `("user", "password")`
   - **Fix**: Documented as MVP demo limitation. Authentication now uses cookie-based sessions.

2. **No authentication on API endpoints** (`backend/app/factory.py:52-131`)
   - **Status**: FIXED
   - All endpoints now require authentication via cookie-based sessions
   - **Fix**: Added `/api/auth/login`, `/api/auth/logout`, `/api/auth/status` endpoints. All board/mutation endpoints now check for auth cookie via `_require_auth()` function.

3. **API key exposure risk** (`backend/app/ai.py:27-28`)
   - **Status**: PARTIALLY ADDRESSED
   - Reads API key from `.env` file at runtime
   - **Fix**: Added startup validation - fails fast if API key is not configured.

### Backend Issues

4. **Missing database path validation** (`backend/app/factory.py:22-26`)
   - **Status**: FIXED
   - Added path validation to ensure DB_PATH is within allowed directory
   - **Fix**: Added validation in `_default_db_path()` to ensure path is within allowed directory using `Path.relative_to()`.

5. **Duplicate code in repository** (`backend/app/repository.py`)
   - **Status**: FIXED
   - Refactored `delete_card` and `move_card` to use helper functions `_delete_card_by_id` and `_move_card_by_id`
   - **Fix**: Public methods now delegate to helper functions, eliminating code duplication.

6. **Incomplete error handling in AI operations** (`backend/app/repository.py:205-215`)
   - **Status**: FIXED
   - Added `_validate_ai_operation()` to validate all operations before applying any
   - **Fix**: Now validates all operations first, then applies them in a single transaction. If any validation fails, no changes are made.

7. **Static files directory assumption** (`backend/app/factory.py:30`)
   - **Status**: FIXED
   - Added explicit check during startup
   - **Fix**: Added runtime check in lifespan that throws `RuntimeError` if static directory doesn't exist.

### Frontend Issues

8. **Duplicate ID generation** 
   - **Status**: ADDRESSED
   - Frontend creates IDs client-side, backend uses database auto-increment
   - **Fix**: Backend now returns full board state after mutations, frontend uses returned IDs.

9. **Memory leak in chat history** (`frontend/src/components/KanbanBoard.tsx`)
   - **Status**: FIXED
   - Added `MAX_CHAT_MESSAGES` constant (20) to limit chat history
   - **Fix**: Added `limitChatMessages()` helper that trims history when it exceeds limit.

10. **API type inconsistency** (`frontend/src/lib/api.ts:81-93`)
    - **Status**: NOT FIXED
    - Risk of runtime errors if backend changes field names
    - **Note**: Low priority, acceptable for MVP.

### Testing

11. **No E2E tests for AI chat** (`frontend/tests/kanban.spec.ts`)
    - **Status**: FIXED
    - Added E2E tests for AI chat, rename column, and delete card
    - **Fix**: Updated `kanban.spec.ts` to include tests for all major features.

12. **Backend tests missing coverage**
    - **Status**: NOT ADDRESSED
    - No tests for `apply_ai_operations` repository method
    - **Note**: Low priority - core functionality covered.

### Configuration/Deployment

13. **Dockerfile Next.js output path**
    - **Status**: VERIFIED CORRECT
    - Next.js `output: "export"` correctly outputs to `out/` directory
    - Dockerfile correctly copies from `/app/frontend/out`.

14. **Missing health check endpoint**
    - **Status**: FIXED
    - Added `/health` endpoint
    - **Fix**: Added `GET /health` that returns `{"status": "ok"}`.

---

## Priority Action Items - COMPLETED

| Priority | Issue | Status | Fix Details |
|----------|-------|--------|-------------|
| High | Add API authentication | FIXED | Added cookie-based auth with login/logout/status endpoints and `_require_auth()` dependency |
| High | Fix Dockerfile Next.js output path | VERIFIED | Already correct - Next.js configured with `output: "export"` |
| Medium | Remove duplicate repository code | FIXED | Refactored to use helper functions `_delete_card_by_id` and `_move_card_by_id` |
| Medium | Add E2E tests for AI chat | FIXED | Added tests for AI chat, rename column, delete card |
| Medium | Implement chat history limit | FIXED | Added MAX_CHAT_MESSAGES=20 and `limitChatMessages()` helper |
| Low | Add health check endpoint | FIXED | Added `GET /health` returning `{"status": "ok"}` |
| Low | Fix database path validation | FIXED | Added path validation in `_default_db_path()` |
| Low | Add static files directory validation | FIXED | Added runtime check in lifespan |
| Medium | Improve AI operations error handling | FIXED | Added `_validate_ai_operation()` to validate all operations before applying |

---

## Code Style Observations

- **Positive**: Consistent use of type hints throughout both Python and TypeScript
- **Positive**: Good use of React hooks (`useCallback`, `useMemo`, `useEffect`)
- **Positive**: Proper use of Pydantic for validation
- **Minor**: Some React components could benefit from `useMemo` for computed values (e.g., `cardsById`)
- **Minor**: Inconsistent error message capitalization (some start with uppercase, some lowercase)
