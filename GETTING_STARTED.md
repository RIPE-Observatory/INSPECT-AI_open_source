# INSPECT-AI

AI-powered clinical trial analysis tool that helps detect potential data inconsistencies and fabrication in published research. Implements the INSPECT-SR (Standardized Response) framework for randomized clincal trial assessment.

## what it does

upload a clinical trial PDF and the system runs the beta automated checks:
- retraction detection 
- expression of concern lookup
- pubpeer community flags
- author retraction history
- trial registration validation
- registry crosscheck
- timeline consistency
- llm-based metadata extraction

results feed into the beta INSPECT-SR questions that you can review, override, and export.

---

## tech stack

**backend**: fastapi, postgresql, redis, arq workers
**frontend**: next.js 15, react 19, tailwind, radix ui
**llm**: openrouter-compatible models
**pdf processing**: grobid
**auth**: clerk
**monorepo**: turbo, bun, uv

---

## project structure

```
INSPECT-AI/
├── apps/
│   ├── api/          # fastapi backend
│   ├── ui/           # next.js frontend
│   └── worker/       # arq background workers
├── packages/
│   ├── python/core/  # shared python logic (checks, db, schemas)
│   └── js/
│       ├── api-client/  # react query + ky client
│       └── ui/          # shared components
├── infra/
│   ├── docker/       # dockerfiles
│   └── caddy/        # reverse proxy config
└── var/
    └── data/         # runtime data (retraction_watch.csv)
```

---

## prerequisites

- [uv](https://github.com/astral-sh/uv) - python package manager
- [bun](https://bun.sh) 1.2.22+ - node package manager
- docker desktop with compose v2
- node.js lts

---

## full setup guide

### step 1: clone and configure

```bash
git clone https://github.com/Discovery-of-fabricated-clinical-trials/INSPECT-AI.git
cd INSPECT-AI
cp .env.example .env
```

edit `.env` and set these required values:

```bash
# llm api (required)
OPENROUTER_API_KEY=your-openrouter-api-key

# monitoring (required)
LOGFIRE_TOKEN=your-logfire-write-token      # from logfire.pydantic.dev

# database (change the password!)
POSTGRES_PASSWORD=your-secure-password-here
DATABASE_URL=postgresql+asyncpg://inspect_user:your-secure-password-here@postgres:5432/inspect_ai

# auth - clerk (required for frontend)
CLERK_JWKS_URL=https://your-domain.clerk.accounts.dev/.well-known/jwks.json
CLERK_ISSUER=https://your-domain.clerk.accounts.dev
```

create `apps/ui/.env.local` for frontend:

```bash
# clerk frontend keys
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...

# api connection
NEXT_PUBLIC_API_BASE_URL=/api/internal

# checks profile
NEXT_PUBLIC_CHECKS_PROFILE=beta
```

---

### step 2: build docker images

```bash
# build all images (api, worker, grobid)
docker compose build

# this builds:
# - inspect-ai-api:latest
# - inspect-ai-worker:latest
# - inspect-ai-grobid:0.8.2
```

---

### step 3: start infrastructure services

```bash
# start postgres, redis, and grobid
docker compose up -d postgres redis grobid
```

wait for services to be healthy:

```bash
# check status
docker compose ps

# you should see postgres and redis as "healthy"
# grobid takes ~2 minutes to start (model loading)
docker compose logs -f grobid
```

---

### step 4: run database migrations

the database needs to be migrated before starting the api.

```bash
cd apps/api

# create virtual environment and install dependencies
uv sync

# activate the virtual environment
source .venv/bin/activate  # linux/mac
# .venv\Scripts\Activate.ps1  # windows powershell

# IMPORTANT: set the host override for running from your machine
# (docker uses 'postgres' as hostname, but from host you need localhost)
export ALEMBIC_DB_HOST=localhost

# run migrations
alembic upgrade head

cd ../..
```

you should see output like:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 53bd03ba16c6, initial complete schema
INFO  [alembic.runtime.migration] Running upgrade 53bd03ba16c6 -> ...
```

---

### step 5: load retraction watch data

the retraction detection feature requires the retraction watch database to be loaded.

```bash
cd apps/api
source .venv/bin/activate

# set database host for local connection
export DATABASE_URL=postgresql+asyncpg://inspect_user:your-password@localhost:5432/inspect_ai

# load the data (takes ~30 seconds)
python -m core.db.load_retraction_data

cd ../..
```

you should see:
```
✓ Loaded 50,000+ retractions with 150,000+ author entries
✓ DATA LOAD COMPLETED SUCCESSFULLY
```

---

### step 6: start all services

```bash
# start api and workers
docker compose up -d api worker-orchestrator worker-default-1 worker-default-2 worker-grobid
```

verify everything is running:

```bash
docker compose ps
```

all services should show as "running" or "healthy".

---

### step 7: start the frontend

```bash
cd apps/ui
bun install
bun run dev
```

---

### step 8: access the app

| service | url | notes |
|---------|-----|-------|
| **frontend** | http://localhost:3000 | main app |
| **api docs** | http://localhost:8000/docs | openapi spec |
| **grobid** | http://localhost:8070 | pdf extraction |

---

## development workflow

### running commands

from the repo root:

```bash
bun run dev          # frontend dev server
bun run build        # build all packages
bun run lint         # lint js + python
bun run typecheck    # type check ts + python
bun run format       # format code
bun run test         # run tests
```

### docker commands

```bash
# view logs
docker compose logs -f api
docker compose logs -f worker-orchestrator

# restart a service
docker compose restart api

# rebuild after code changes
docker compose up --build -d api

# stop everything
docker compose down

# full reset (removes database!)
docker compose down -v
```

### creating new migrations

when you modify database models:

```bash
cd apps/api
source .venv/bin/activate
export ALEMBIC_DB_HOST=localhost

# generate migration
alembic revision --autogenerate -m "description of changes"

# review the generated file in apps/api/alembic/versions/
# then apply it
alembic upgrade head
```

---

## environment variables reference

### required

| variable | description |
|----------|-------------|
| `OPENROUTER_API_KEY` | OpenRouter-compatible API key for LLM checks |
| `LOGFIRE_TOKEN` | monitoring/observability token |
| `POSTGRES_PASSWORD` | database password (change from default!) |
| `CLERK_JWKS_URL` | clerk jwt verification url |
| `CLERK_ISSUER` | clerk issuer url |

### frontend (apps/ui/.env.local)

| variable | description |
|----------|-------------|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | clerk public key |
| `CLERK_SECRET_KEY` | clerk secret key |
| `NEXT_PUBLIC_API_BASE_URL` | api proxy path (use `/api/internal`) |
| `NEXT_PUBLIC_CHECKS_PROFILE` | `beta` |

### optional

| variable | default | description |
|----------|---------|-------------|
| `POSTGRES_PORT` | 5432 | postgres port |
| `REDIS_PORT` | 6379 | redis port |
| `API_PORT` | 8000 | api port |
| `GROBID_PORT` | 8070 | grobid port |
| `ENVIRONMENT` | development | `development` or `production` |

see `.env.example` for the complete list.

---

## api endpoints

| endpoint | method | description |
|----------|--------|-------------|
| `/api/v1/analyze` | POST | upload pdf, start analysis |
| `/api/v1/jobs/{id}` | GET | get job status and results |
| `/api/v1/jobs/{id}/inspect-sr` | GET/PUT | fetch/save inspect-sr data |
| `/api/v1/jobs/{id}/inspect-sr/progress` | GET | completion progress |
| `/api/v1/reviewers/profile` | GET/PUT | user profile |
| `/api/v1/test/health` | GET | health check |

full api docs at http://localhost:8000/docs

---

## worker architecture

background jobs use arq (redis-backed async task queue):

| worker | queue | concurrent jobs | purpose |
|--------|-------|-----------------|---------|
| worker-orchestrator | orchestrator | 2 | coordinates analysis flow |
| worker-default-1 | default | 2 | llm-based checks |
| worker-default-2 | default | 2 | llm-based checks |
| worker-grobid | grobid | 1 | pdf extraction |

job flow:
1. user uploads pdf → api creates job in postgres
2. orchestrator picks up job, spawns check tasks
3. workers process checks in parallel
4. results stored in postgres
5. api aggregates into inspect-sr format

---

## inspect-sr structure

the beta checklist currently stores these automated questions:

| question | focus |
|----------|-------|
| Q1.1 | publication retraction |
| Q1.2 | post-publication notices and PubPeer comments |
| Q1.3 | author history concerns |
| Q2.2 | registration timing |
| OVERALL | study-level judgement |

responses: `yes`, `no`, `unclear`, `na`
judgements: `no-concerns`, `some-concerns`, `serious-concerns`

---

## troubleshooting

### docker won't start

```bash
# check for port conflicts
lsof -i :5432  # postgres
lsof -i :6379  # redis
lsof -i :8000  # api

# full reset
docker compose down -v
docker compose up --build -d
```

### database connection errors

```bash
# check postgres is running
docker compose ps postgres
docker compose logs postgres

# test connection
docker compose exec postgres psql -U inspect_user -d inspect_ai -c "SELECT 1"
```

### migrations fail

```bash
# make sure ALEMBIC_DB_HOST is set
export ALEMBIC_DB_HOST=localhost

# check current migration state
alembic current

# if stuck, you may need to stamp
alembic stamp head
```

### grobid timeout

grobid takes 1-2 minutes to fully start (lazy model loading).

```bash
# check if it's ready
curl http://localhost:8070/api/isalive

# view logs
docker compose logs -f grobid
```

### frontend can't connect to api

1. make sure api is running: `docker compose ps api`
2. check `.env.local` has `NEXT_PUBLIC_API_BASE_URL=/api/internal`
3. check api logs: `docker compose logs api`

### workers not processing jobs

```bash
# check worker logs
docker compose logs -f worker-orchestrator

# verify redis connection
docker compose exec redis redis-cli ping
```

---

## production deployment

use the production compose file:

```bash
docker compose -f docker-compose.prod.yml up -d
```

this adds:
- caddy reverse proxy (auto ssl)
- next.js container
- scaled workers (3 default workers)
- stricter security settings

set in `.env`:
```bash
ENVIRONMENT=production
DEBUG=false
```

---

## useful links

- [fastapi docs](https://fastapi.tiangolo.com/)
- [next.js docs](https://nextjs.org/docs)
- [arq docs](https://arq-docs.helpmanual.io/)
- [grobid docs](https://grobid.readthedocs.io/)
- [clerk docs](https://clerk.com/docs)
- [alembic docs](https://alembic.sqlalchemy.org/)

---

## contributing

1. create a branch off `main`
2. make your changes
3. run `bun run lint && bun run typecheck`
4. open a pr
