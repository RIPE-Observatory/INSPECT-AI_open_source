# INSPECT-AI Open Source Cleanup Plan

This repository is the public source release candidate for the INSPECT-AI application. It was synced from the working production app repository at `/home/stardust/Work/INSPECT-AI` into `/home/stardust/Work/paper/INSPECT-AI_open_source`.

The intended public scope is the beta INSPECT-AI app only. The current production app is focused on four INSPECT-SR checks:

- `Q1.1`: Does the study have an associated retraction?
- `Q1.2`: Does the study have an associated expression of concern or other relevant post-publication notice?
- `Q1.3`: Do other studies by the research team highlight causes for concern?
- `Q2.2`: Are there concerns relating to the timing or absence of study registration?

The overall study judgement (`OVERALL`) is kept as the reviewer-facing final decision, but it is not one of the four automated beta checks.

## Important Context

The production app is a monorepo:

- `apps/api`: FastAPI backend. This is intentionally thin and mainly exposes HTTP endpoints.
- `apps/ui`: Next.js 15 frontend with Clerk auth, upload flow, job result view, PDF viewer, INSPECT-SR review controls, and export.
- `apps/worker`: ARQ worker process entrypoint.
- `packages/python/core`: Main backend domain logic, check implementations, services, DB models, schemas, result normalization, and ARQ orchestration.
- `packages/js/api-client`: Ky and TanStack Query client used by the UI.
- `packages/js/ui`: Shared UI primitives.
- `infra`: Dockerfiles and Caddy config.

The separate ontology and knowledge graph work lives in `/home/stardust/Work/InspectAI-Ontology`. That repo is RIPE-KG/RIPE-O focused and includes RDF, GraphDB, OpenAlex enrichment, YARRRML/RML mapping, and a KG exploration UI. Do not mix that full KG repository into this app source release unless explicitly requested. The public app repo should reference the paper/KG work only at a high level if needed.

## Runtime Flow

The current app flow is:

1. The user signs in with Clerk.
2. The user completes reviewer onboarding.
3. The user uploads one or more clinical trial PDFs.
4. FastAPI saves the PDF to shared storage, creates a reviewer-owned `jobs` row, and enqueues `run_evidence_synthesis_arq_task`.
5. The ARQ orchestrator runs enabled checks based on `CHECKS_PROFILE`.
6. Check outputs are merged into `jobs.results` JSONB.
7. Results are normalized into `results.checks`.
8. `results.inspect_sr` is auto-populated with automated suggestions for the beta checklist.
9. The frontend displays the PDF, evidence tabs, automated findings, reviewer controls, and export actions.

## Beta Checks To Keep

Keep the backend check code needed for the four beta questions:

- `packages/python/core/checks/grobid_metadata_extraction.py`
- `packages/python/core/checks/retraction_detection.py`
- `packages/python/core/checks/eoc_correction_detection.py`
- `packages/python/core/checks/author_retraction_history.py`
- `packages/python/core/checks/trial_llm_extraction.py`
- `packages/python/core/checks/timeline_consistency.py`
- `packages/python/core/checks/registry_crosscheck.py`
- `packages/python/core/checks/prospective_registration.py`
- `packages/python/core/checks/pubpeer_signal_analysis.py`

Why these stay:

- `Q1.1` uses GROBID metadata plus Retraction Watch lookup for the main article and references.
- `Q1.2` uses EOC/correction detection and PubPeer signal analysis.
- `Q1.3` uses GROBID authors plus Retraction Watch author history.
- `Q2.2` uses trial ID extraction, registry lookup, timeline extraction, and prospective-registration comparison.

Keep these service modules unless replacing their callers:

- `packages/python/core/services/llm_service.py`
- `packages/python/core/services/grobid_service.py`
- `packages/python/core/services/grobid_parser.py`
- `packages/python/core/services/registry_service.py`
- `packages/python/core/services/retraction_watch_service.py`
- `packages/python/core/services/pubpeer_service.py`

Keep core result/checklist support:

- `packages/python/core/config/check_registry.py`
- `packages/python/core/config/checks_registry.yaml`
- `packages/python/core/results/normalize_checks.py`
- `packages/python/core/results/populate_inspect_sr.py`
- `packages/python/core/schemas/inspect_sr.py`
- `packages/python/core/tasks/arq_tasks.py`

## Non-Beta Code To Remove Or Disable

Remove code and UI that exists only for non-beta checks:

- Baseline table extraction.
- R p-value/statistical analysis.
- Document similarity assessment.
- Similarity API endpoints if no beta UI or backend path depends on them.
- Paper/baseline/statistical-hash DB models and CRUD if no remaining migration or endpoint requires them.
- R scripts and R worker setup.
- `rstats` queue handling.
- Full-profile UI sections for `Q3.2` figures and `Q4.3` baseline data.
- Full-profile export/checklist logic if it is not needed for beta.

Candidate backend removal paths:

- `packages/python/core/checks/baseline_characteristics_extraction.py`
- `packages/python/core/checks/baseline_statistics_analysis/`
- `packages/python/core/checks/document_similarity_assessment/`
- `packages/python/core/r_scripts/`
- `packages/python/core/services/similarity_detection/`
- `packages/python/core/db/models/baseline_characteristic.py`
- `packages/python/core/db/models/paper.py`
- `packages/python/core/db/models/statistical_hash.py`
- `packages/python/core/db/crud/baseline_characteristic.py`
- `packages/python/core/db/crud/paper.py`
- `packages/python/core/db/crud/statistical_hash.py`
- `packages/python/core/schemas/similarity.py`
- `apps/api/src/api/v1/endpoints/similarity.py`

Candidate frontend removal paths:

- `apps/ui/src/app/jobs/[jobId]/components/BaselineTabContent.tsx`
- `apps/ui/src/app/jobs/[jobId]/components/SimilarityTabContent.tsx`
- Full-profile branches in `apps/ui/src/app/jobs/[jobId]/section-config.ts`
- Baseline/similarity branches in `apps/ui/src/app/jobs/[jobId]/utils/status.ts`
- Any references to `/api/internal/plots` that only serve R-generated plots.

Candidate infra removal paths:

- R installation/dependencies in `infra/docker/Dockerfile.worker`.
- `rpy2` extras in Python package config if no beta code imports it.
- `arq:queue:rstats` handling in `apps/worker/arq_worker.py`.
- Any compose service added solely for R stats if present.

## Configuration Truth

Current beta config in the source app:

- Backend profile: `CHECKS_PROFILE=beta_inspect_sr`.
- Frontend profile: `NEXT_PUBLIC_CHECKS_PROFILE=beta`.
- `packages/python/core/config/checks_registry.yaml` defines `beta_inspect_sr` without baseline, R stats, or similarity checks.
- `full` includes `baseline_characteristics_extraction`, `baseline_statistics_analysis`, and `document_similarity_assessment`; these should be removed or made impossible in the public beta-only repo.

After cleanup, the registry should ideally have only one public profile or a clearly beta-only profile. Do not leave a working `full` profile unless the non-beta implementation remains intentionally supported.

## Sensitive Files

Do not commit these:

- `.env`
- `.env.*`
- `apps/ui/.env`
- `apps/ui/.env.*`
- `.logfire/`
- `.playwright-mcp/`
- `.codex/`
- Local caches, virtualenvs, build output, backups, runtime DBs, PDFs, and generated private exports.

After the initial sync, obvious local env and runtime artifacts were removed from the target clone. Re-check before committing:

```bash
find . -name '.env*' -o -path './.logfire/*' -o -path './.playwright-mcp/*'
git status --short
```

Use `.env.example` files with placeholder values only.

## Recommended Cleanup Sequence

1. Confirm target repo state:

```bash
cd /home/stardust/Work/paper/INSPECT-AI_open_source
git status --short
find . -name '.env*'
```

2. Remove copied auxiliary/research material not needed in the app repo:

- `InspectAI-Ontology/`
- `knowledge/semopenalex/`
- Large private docs, cost exports, PDFs, backups, and temporary analysis outputs.

3. Reduce check registry:

- Keep only checks that feed `Q1.1`, `Q1.2`, `Q1.3`, and `Q2.2`.
- Remove `full` or leave it as an alias to the beta set.
- Remove baseline/R/similarity check definitions.

4. Simplify ARQ orchestration:

- Remove imports and branches for baseline extraction, baseline statistics, and document similarity.
- Remove `_execute_baseline_pvalue_chain`.
- Remove `task_baseline_characteristics` and `task_baseline_statistics`.
- Remove `cleanup` or queue behavior that only exists for non-beta paths.

5. Simplify backend API:

- Remove similarity endpoint registration from `apps/api/src/api/v1/api.py`.
- Remove plots endpoint only if no beta UI references it.
- Keep `jobs`, `reviewers`, and test endpoints as needed.

6. Simplify database models and migrations carefully:

- If this public repo is meant to run from a fresh DB only, create a clean beta schema migration.
- If keeping existing migrations, avoid importing removed models in `core/db/models/__init__.py`.
- Decide whether `check_results` is still needed; the main app currently relies mostly on `jobs.results`.

7. Simplify frontend:

- Make `section-config.ts` beta-only.
- Remove baseline and similarity components/imports.
- Remove status logic for removed sections.
- Keep upload, job PDF view, publication metadata, retraction, EOC/PubPeer, author history, registration, final judgement, and export.

8. Prune dependencies:

- Remove R/rpy2 dependencies and Docker setup.
- Remove similarity-only Python dependencies if unused.
- Keep `uv` for Python dependencies, per project rule.
- Keep Bun/Turbo for JS workspace.

9. Verify:

```bash
bun run typecheck
bun run lint
uv run --project apps/api --extra dev pytest
```

If dependency installation is needed, use `uv sync` for Python, not pip.

## Known Cautions

- The current source repo had uncommitted edits before the sync. Treat the target clone as a working snapshot, not a clean upstream release.
- Several non-beta files are referenced indirectly through schemas, types, frontend imports, and Alembic model imports. Remove in dependency order and run typecheck frequently.
- The frontend currently defaults to full if `NEXT_PUBLIC_CHECKS_PROFILE` is missing in one helper. Change this to beta-only or remove profile branching.
- Retraction Watch data itself is runtime data and should not be committed. Keep only loaders or documented setup.
- Do not publish API keys or local `.env` values. The source repo contained real local keys, so scan before the first public commit.

## Initial Next Thread Prompt

Suggested starting prompt for the next thread:

```text
We are in /home/stardust/Work/paper/INSPECT-AI_open_source. Read docs/plan.md first. This is the public source release cleanup for INSPECT-AI. Keep only beta checks Q1.1, Q1.2, Q1.3, and Q2.2 plus OVERALL reviewer judgement. Remove non-beta baseline/R/similarity/full-profile/KG material, preserve app functionality, and verify with typecheck/tests where practical. Do not touch /home/stardust/Work/INSPECT-AI.
```
