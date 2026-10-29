# DermaSense AI

A privacy-first skin-lesion screening prototype with a React web flow and a CPU-based research training pipeline. It is a screening aid, not a diagnostic device.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `artifacts/dermasense-ai/` — DermaSense web app and local ML pipeline
- `artifacts/dermasense-ai/src/` — React/Vite interface
- `artifacts/dermasense-ai/src/data/`, `src/models/`, `src/safety/`, `src/explain/`, `src/report/`, `src/safe_corner/` — Python pipeline
- `artifacts/dermasense-ai/README.md` — dataset setup, training, evaluation, and limitations

## Architecture decisions

- Keep patient history and uploaded images in browser memory; do not send them to a server by default.
- Never show a prediction or performance number unless it comes from a trained checkpoint and held-out evaluation.
- Dataset files, processed patient splits, checkpoints, and generated outputs are excluded from version control.

## Product

DermaSense guides a user through consent, lesion history, and an existing image upload; it provides a clear model-unavailable state until a real trained checkpoint is supplied. The routine planner provides general wellness reminders only.

## User preferences

- The user requested the project be pushed to `https://github.com/gaytritripathi121/DermaSense-AI.git`.

## Gotchas

- The PAD-UFES-20 dataset must be downloaded and placed locally by the project owner; never commit the dataset or patient images.
- The web prototype and Python training pipeline do not imply a clinically validated model; do not claim diagnostic accuracy.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
