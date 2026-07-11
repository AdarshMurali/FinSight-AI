# Authentication & Multi-Tenant Access — Demo Accounts

Part of Task 6.4 (see `plan.md`). Fund managers log in and see only the portfolios
they manage — enforced at the data layer (`Portfolios.manager_id`), not just hidden
in the UI. All accounts below are synthetic demo data seeded by
`backend/db_migration_auth.sql` (production) / `backend/db_migration_fix.sql` (fresh
installs) — not real credentials.

## Demo accounts

Shared password for all accounts: **`FinSight2026!`**

| Email | Name | Role | Portfolios |
|---|---|---|---|
| sarah.chen@finsight.demo | Sarah Chen | fund_manager | 1–10 (BlackRock, Vanguard, SSGA, Fidelity) |
| james.okafor@finsight.demo | James Okafor | fund_manager | 11–20 (Fidelity, PIMCO, GSAM, JPM AM, MS IM) |
| priya.patel@finsight.demo | Priya Patel | fund_manager | 21–30 (TRP, Wellington, Bridgewater, Renaissance, Citadel) |
| david.kim@finsight.demo | David Kim | fund_manager | 31–40 (Citadel, Two Sigma, AQR, Norway GPFG, ADIA) |
| elena.rodriguez@finsight.demo | Elena Rodriguez | fund_manager | 41–50 (CalPERS, OTPP, Rockefeller) |
| admin@finsight.demo | Marcus Webb | admin | all 50 (scoping bypassed) |

## Data model

- `Users` (fund managers — distinct from `Customers`, which are the institutions being managed): `user_id`, `email`, `hashed_password` (bcrypt), `full_name`, `role` (`fund_manager` \| `admin`)
- `Portfolios.manager_id` → FK to `Users.user_id`, one owner per portfolio

## Migration files

- `backend/db_migration_auth.sql` — **additive only**, idempotent, safe to re-run against the live production DB. Does not touch existing `Portfolios` rows beyond adding/backfilling `manager_id`.
- `backend/db_migration_fix.sql` — the full wipe-and-rebuild script (STEP 8) now includes the same `Users`/`manager_id` setup, for a from-scratch fresh install. **Do not re-run this against production** — it deletes and recreates `Portfolios`, which would violate the FK from `Alerts`/`Risk_Metrics` and destroy accumulated alert/risk history.

See `plan.md` Task 6.4 for the full auth architecture (JWT cookie flow, REST enforcement, AI chat tool scoping, MCP server scoping, WebSocket scoping).
