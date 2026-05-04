# Inspect AI UI

Next.js 15 frontend powered by Bun workspaces. Shared UI primitives live in `packages/js/ui`; API hooks live in `packages/js/api-client`.

## Setup

```bash
bun install
cp apps/ui/.env.example apps/ui/.env.local  # adjust Clerk + API settings for the Next.js app
```

## Scripts

```bash
bun run dev         # start Next.js dev server (http://localhost:3000)
bun run build       # production build (linting runs automatically)
bun run lint        # ESLint
bun run storybook   # Storybook playground on :6006
bun run test        # Playwright end-to-end tests
```

## Shared Packages

- `@inspect/ui`: Tailwind-flavoured primitives (`Button`, `Card`, tokens)
- `@inspect/api-client`: Ky-based HTTP client + React Query hooks for the FastAPI backend

Both packages are consumed via workspace aliases and transpiled through `next.config.ts`.

## Environment

`INSPECT_API_URL` / `NEXT_PUBLIC_API_BASE_URL` default to `http://localhost:8000/api/v1`. Override the frontend values in `apps/ui/.env.local` and backend values in the repo-root `.env` when pointing to another backend so both services stay aligned.

## Developer Notes

- TanStack React Query v5 is initialised in `src/app/layout.tsx`; consume data through the hooks exported from `@inspect/api-client`.
- Shared primitives should be added to `packages/js/ui` and re-exported through the app-level wrappers (see `src/components/ui/*`).
