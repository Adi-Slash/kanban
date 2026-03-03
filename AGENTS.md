# The Project Management App

## Business Requirements

This project is a comprehensive Project Management App. Key features:
- User registration and authentication with hashed passwords
- Multiple Kanban boards per user
- Kanban boards with renameable columns and draggable cards
- Cards with priority levels (low/medium/high/urgent), due dates, and labels
- Board-level labels with colors that can be assigned to cards
- Card detail editing modal
- AI chat sidebar that can create/edit/move/delete cards per board

## Technical Decisions

- NextJS frontend (static export)
- Python FastAPI backend, serving the static NextJS site at /
- Everything packaged into a Docker container
- Use "uv" as the package manager for python in the Docker container
- Use OpenRouter for the AI calls. An OPENROUTER_API_KEY is in .env in the project root
- Use `openai/gpt-oss-120b` as the model
- Use SQLite local database (normalized schema with version tracking)
- Start and Stop server scripts for Mac, PC, Linux in scripts/
- In-memory session management with secure random tokens
- PBKDF2-SHA256 password hashing (no external dependencies)

## Authentication

- Session-based auth using `pm_session` cookie with random tokens
- In-memory session store (tokens map to user_id + username)
- Registration creates new users with hashed passwords
- Login validates credentials against DB and creates session
- All API endpoints (except auth and health) require authentication

## API Structure

Auth:
- `POST /api/auth/register` - register new user
- `POST /api/auth/login` - login with JSON body
- `POST /api/auth/logout` - logout
- `GET /api/auth/status` - check auth status
- `GET /api/auth/profile` - get user profile
- `PATCH /api/auth/profile` - update profile

Boards:
- `GET /api/boards` - list user's boards
- `POST /api/boards` - create board
- `GET /api/boards/{board_id}` - get board with columns, cards, labels
- `PATCH /api/boards/{board_id}` - update board name/description
- `DELETE /api/boards/{board_id}` - delete board

Board operations:
- `PATCH /api/boards/{board_id}/columns/{column_id}` - rename column
- `POST /api/boards/{board_id}/columns/{column_id}/cards` - add card
- `PATCH /api/boards/{board_id}/cards/{card_id}` - update card
- `DELETE /api/boards/{board_id}/columns/{column_id}/cards/{card_id}` - delete card
- `POST /api/boards/{board_id}/cards/{card_id}/move` - move card
- `PUT /api/boards/{board_id}/cards/{card_id}/labels` - set card labels

Labels:
- `POST /api/boards/{board_id}/labels` - create label
- `PATCH /api/boards/{board_id}/labels/{label_id}` - update label
- `DELETE /api/boards/{board_id}/labels/{label_id}` - delete label

AI:
- `POST /api/ai/smoke` - AI connectivity check
- `POST /api/boards/{board_id}/ai/chat` - AI chat for specific board

## Color Scheme

- Accent Yellow: `#ecad0a` - accent lines, highlights
- Blue Primary: `#209dd7` - links, key sections
- Purple Secondary: `#753991` - submit buttons, important actions
- Dark Navy: `#032147` - main headings
- Gray Text: `#888888` - supporting text, labels

## Coding standards

1. Use latest versions of libraries and idiomatic approaches as of today
2. Keep it simple - NEVER over-engineer, ALWAYS simplify, NO unnecessary defensive programming. No extra features - focus on simplicity.
3. Be concise. Keep README minimal. IMPORTANT: no emojis ever
4. When hitting issues, always identify root cause before trying a fix. Do not guess. Prove with evidence, then fix the root cause.

## Working documentation

All documents for planning and executing this project will be in the docs/ directory.
Please review the docs/PLAN.md document before proceeding.
