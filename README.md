# agentic-rag-live-memory

An evidence-backed workspace for connecting external knowledge sources, retrieving information, and preserving useful context over time.

## Current status

Phase 1 foundation is implemented: user registration and login, an opt-in local demo session, personal and additional workspaces, conversation/message persistence, a React workspace shell, PostgreSQL migrations, and a Docker Compose development environment.

The chat currently stores user messages only. It does not generate AI answers. Integrations, retrieval, long-term memory, refresh tokens, and background synchronization are not implemented yet.

## Architecture

- `backend/app/api/v1` contains versioned HTTP routes; services own workspace access checks and database operations.
- SQLAlchemy 2 async models persist users, workspace memberships, conversations, and messages. Alembic owns schema changes.
- Passwords are hashed with Argon2id. Short-lived HS256 access tokens are signed using an environment-provided secret. Tokens are held in frontend memory only.
- `frontend` is a React + TypeScript + Vite application using React Router; API calls go to FastAPI and provider credentials are not handled by the browser.
- PostgreSQL is the application database. Redis is included in Compose for later background/cache work and is not used by Phase 1.

## Run locally with Docker

1. Copy `.env.example` to `.env`.
2. Replace `SECRET_KEY` and `POSTGRES_PASSWORD` with random values. Update the password in `DATABASE_URL` to match `POSTGRES_PASSWORD`; URL-encode special characters in the URL. Generate a signing key with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
   The example enables direct access for the local Vite development server using `APP_ENV=development` and `DEMO_MODE=true`. The backend still issues a signed access token and requires it for workspace APIs. Do not enable demo mode in production.
3. Start PostgreSQL and Redis: `docker compose -f infrastructure/docker-compose.yml up -d postgres redis`.
4. In a terminal, from `backend`, install the project and run migrations:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -e ".[dev]"
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

5. In another terminal, from `frontend`:

   ```powershell
   npm install
   npm run dev
   ```

The frontend is served at `http://localhost:5173`, the API at `http://localhost:8000`, and interactive API documentation at `http://localhost:8000/docs`. To stop local services, run `docker compose -f infrastructure/docker-compose.yml down`. Add `-v` only when you intend to delete the local database volume.

To run the backend in Docker instead, start all Compose services with `docker compose -f infrastructure/docker-compose.yml up --build -d`; the backend container applies Alembic migrations before serving requests.

## API

- `GET /health` checks the database connection.
- `POST /api/v1/auth/register` creates a user and personal workspace, then returns an access token.
- `POST /api/v1/auth/login` authenticates a user.
- `POST /api/v1/auth/demo-session` creates or reuses a local demo account only when `APP_ENV=development` and `DEMO_MODE=true`.
- `GET|POST /api/v1/workspaces` lists or creates workspaces for the authenticated user.
- `GET|POST /api/v1/workspaces/{workspace_id}/conversations` lists or creates conversations in an accessible workspace.
- `GET|POST /api/v1/conversations/{conversation_id}/messages` lists or stores user messages in an accessible conversation.

All workspace and conversation access is scoped through workspace membership. Unauthorized or nonexistent resources return `404` to avoid disclosing their existence.

## Configuration

The application reads `.env` from the repository root. See [.env.example](./.env.example). Set `SECRET_KEY` to at least 32 characters before the backend starts. Configure `DATABASE_URL` for the local Compose PostgreSQL service, and keep its password in sync with `POSTGRES_PASSWORD`. `CORS_ORIGINS` may be supplied as a JSON array.

## Tests and checks

From `backend`, run `pytest`. From `frontend`, run `npm test` and `npm run build`. Tests use a temporary SQLite database; the configured application database and migration use PostgreSQL.

## Known limitations

- No assistant/LLM responses, RAG, embeddings, integrations, or memory are available.
- Refresh-token rotation/revocation, rate limiting, audit logging, and production deployment controls remain future work.
- Redis is provisioned but unused. The current access token is short-lived; frontend state is lost on reload and users sign in again.
- PostgreSQL is configured for local development; this change does not claim a production deployment or external-service verification.

## Phase 2 next steps

Add source document and document-chunk models with provenance, configure an embedding provider and pgvector dimension, implement document normalization/chunking and hybrid retrieval, then test retrieval and citation behavior against actual ingested sources before enabling answer generation.
