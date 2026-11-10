# BudgetScope

**Status:** Early implementation. The minimal FastAPI backend and its first automated smoke test are implemented and verified.

BudgetScope is a local-first personal finance and budgeting application developed as a software engineering portfolio project.

The planned first version is designed for offline use on a single computer. Its intended features include importing bank transaction CSV files, categorizing transactions, managing budgets, and analyzing personal finances.

## Project Status

The initial development environment and project structure have been prepared.

**Completed setup:**
- Python 3.13 backend environment with FastAPI, SQLAlchemy, Alembic, and SQLCipher dependencies
- Initial backend package and migration directory structure
- Successful SQLCipher encryption and access-control smoke tests
- React, TypeScript, and Vite frontend configuration
- React Router and frontend testing dependencies
- Successful frontend linting, production builds, and testing-environment smoke test
- Minimal FastAPI application with a passing automated smoke test

**Not yet implemented:**
- Application business logic and API endpoints
- Database models and migrations
- Financial features and CSV imports
- Production user interface

## Technology Stack

**Backend:** Python 3.13, FastAPI, Pydantic, SQLAlchemy, Alembic, SQLCipher

**Frontend:** React, TypeScript, Vite, React Router, CSS

**Testing:** pytest, HTTPX, Vitest, React Testing Library, jsdom

## Repository Structure

- `backend/`: Python backend, database migration infrastructure, and backend tests
- `frontend/`: React frontend and frontend testing configuration
- `demo_data/`: Reserved for synthetic demonstration data
- `scripts/`: Reserved for project-specific utilities

Some planned directories will be added when their contents are implemented.

## Development Setup

**Requirements:** Python 3.13, Node.js 26, and npm.

For the backend, create a virtual environment under `backend/.venv` and install the pinned dependencies from `backend/requirements.lock`.

For the frontend, install dependencies using `npm ci --prefix frontend`.

Available frontend checks:

- `npm run lint --prefix frontend`
- `npm run build --prefix frontend`

### Run the backend

From the repository root, open Git Bash:

```bash
cd backend
source .venv/Scripts/activate
python -m uvicorn budgetscope.main:app --host 127.0.0.1 --port 8000
```

The API documentation is available at:

- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/openapi.json

The backend currently contains no financial API endpoints.

### Run the frontend

In a separate Git Bash terminal, from the repository root:

```bash
cd frontend
npm run dev -- --host 127.0.0.1
```

Open the local URL displayed by Vite.

The frontend currently displays a placeholder. Backend communication is not yet implemented.

### Run checks

Backend tests, from `backend/` with the virtual environment activated:

```bash
python -m pytest -q
```

Frontend linting and production build, from `frontend/`:

```bash
npm run lint
npm run build
```

## Data Privacy

Personal financial records, credentials, local databases, and backups must never be committed to this repository.

Only synthetic or explicitly authorized demonstration and test data may be published. Production data must remain separate from development and testing resources.

## License

MIT License.
