# Database Migrations

Single source of truth for the FinSight AI schema. Azure SQL Server (`mssql+pyodbc`) —
these are plain T-SQL scripts, no migration framework (no Alembic in use despite it
being in `requirements.txt`).

## Apply order

Run in numeric order. `001` is a full wipe-and-rebuild; everything after it is
additive/idempotent and safe to run against a live database with existing data.

| # | File | Type | Safe against live prod data? |
|---|---|---|---|
| 001 | `001_schema_and_seed.sql` | Full schema + synthetic seed data (20 customers, 50 portfolios, 135 securities, etc.) | **No** — deletes and recreates every table. Fresh installs only. |
| 002 | `002_auth.sql` | `Users` table (fund managers/admin), `manager_id` backfill on `Portfolios` | Yes — additive only, idempotent |
| 003 | `003_alerts_v2.sql` | `Alerts.status`/`occurrence_count`/`resolved_at`/`last_triggered_at` columns | Yes — additive only |
| 004 | `004_alerts_v3.sql` | `Alerts.read_at` column + backfill, `last_triggered_at` default fix | Yes — additive only |
| 005 | `005_parametric_shocks.sql` | `Risk_Metrics.parametric_data` column | Yes — additive only |

## Recreating this application from scratch

1. Provision an Azure SQL Server (or any SQL Server–compatible target) and create
   an empty `FinSight_AI` database.
2. Run `001_schema_and_seed.sql` — creates every table and seeds realistic synthetic
   data (real institution names, 5 years of positions/transactions/performance).
3. Run `002` → `003` → `004` → `005` in order — each adds what later application
   phases needed (auth, alert dedup, alert read-tracking, parametric risk shocks).
4. Point `backend/.env` (or AWS Secrets Manager, see `backend/services/secrets_loader.py`)
   at the new server — `DB_SERVER`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.

That's the entire schema history. No other `.sql` files exist anywhere else in the
repo — if you ever need to change the schema again, add `006_...sql` here, additive
only, and update the table above.

## Known gap: ORM model vs actual schema

`backend/models.py` (SQLAlchemy) has historically lagged behind what these `.sql`
files actually create — e.g. `Security.current_price` and `MarketEvent.sentiment`
were both real DB columns for a while before anyone added them to the ORM model,
causing `CompileError: Unconsumed column names` the first time code tried to write
to them. If you hit that error, check `INFORMATION_SCHEMA.COLUMNS` against
`models.py` directly rather than assuming the model is authoritative — these `.sql`
files are the actual source of truth for the schema, not the ORM.
