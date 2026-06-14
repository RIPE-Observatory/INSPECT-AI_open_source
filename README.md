# INSPECT-AI

INSPECT-AI is a human-in-the-loop LLM system for supporting research integrity assessments of published clinical trial reports. It helps reviewers inspect a trial publication, gather relevant external info, complete INSPECT-SR assessment checks, and record the reasoning behind automated and human-reviewed outcomes.

The system is designed to support expert judgement by automating the time consuming task of information gathering. Automated checks and LLM-assisted extraction provide draft evidence and hypotheses; human reviewers can verify, revise, override, and export the assessment record.

INSPECT-AI is part of the RIPE Observatory:

* [RIPE-O](https://w3id.org/ripe/ripe-o) provides the ontology for representing assessment cases, evidence, hypotheses, agents, and provenance.
* [RIPE-KG](https://w3id.org/ripe/ripe-kg) publishes assessment traces generated from this workflow as a queryable knowledge graph.
* [RIPE-KG UI](https://ripe-kg.inspectai.app) provides the public exploration and SPARQL interface for the published graph.

## What the System Does

INSPECT-AI supports a reviewer workflow around uploaded clinical trial PDFs:

* extracts publication and study metadata from the document;
* checks publication integrity signals such as retractions and expressions of concern;
* retrieves post-publication discussion signals such as PubPeer comments;
* supports trial registration checks and timeline consistency checks;
* assists with author and publication history checks;
* presents automated outcomes for reviewer inspection;
* lets reviewers edit outcomes, add rationale, and export assessment results.

The exported assessment data can be transformed into RIPE-O RDF and published through RIPE-KG.

## Repository Contents

```text
apps/api/                  FastAPI backend and database migrations
apps/ui/                   Next.js reviewer interface
apps/worker/               Background worker entry point
packages/python/core/      Shared Python assessment, data, and service logic
packages/js/api-client/    Shared TypeScript API client
packages/js/ui/            Shared UI package
infra/                     Docker and Caddy deployment files
docs/                      Project notes, guidance files, and supporting material
tools/                     Utility and migration scripts
```

## Technology Stack

| Layer | Technology |
| --- | --- |
| Backend | FastAPI, PostgreSQL, Redis, ARQ workers |
| Frontend | Next.js, React, Tailwind CSS |
| LLM integration | OpenRouter-compatible model APIs |
| PDF processing | GROBID |
| Authentication | Clerk |
| Infrastructure | Docker, Caddy |
| Package management | `uv` for Python, `bun` for JavaScript/TypeScript |

LLM prompts, schemas, service flow, and check wiring are indexed in [LLM_GUIDE.md](./LLM_GUIDE.md).

## Getting Started

See [GETTING_STARTED.md](./GETTING_STARTED.md) for local setup and deployment instructions.

At a high level:

```sh
cp .env.example .env
docker compose up --build -d
cd apps/ui
bun install
bun run dev
```

The full setup requires API keys, database configuration, authentication configuration, and local infrastructure services.

## Development Commands

Run frontend development server:

```sh
bun run dev
```

Run checks from the repository root:

```sh
bun run lint
bun run typecheck
```

Python dependencies are managed with `uv`; frontend and workspace dependencies are managed with `bun`.

## Relationship to RIPE-O and RIPE-KG

INSPECT-AI produces structured assessment records from a human review workflow. RIPE-O provides the semantic model for representing those records as provenance traces, and RIPE-KG publishes the resulting RDF graph for inspection and querying.

## License

This work is licensed under the Creative Commons Attribution 4.0 International License. See [LICENSE.md](LICENSE.md) for details.

## Contributing

Please keep changes focused and include the relevant checks for the part of the system being modified. Frontend changes should pass the TypeScript and lint checks; backend changes should pass the Python linting and test commands described in the setup guide.
