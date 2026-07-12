-- ─────────────────────────────────────────────────────────────────────────────
-- Parametric shock scenarios migration — additive only, safe to run against the
-- live production DB. Adds a column to store sensitivity-based shock results
-- (rates +/-100bps, equities -20%, no stress) separately from stress_data,
-- which holds historical-replay scenarios only — the two use different
-- computation methods and shouldn't be mixed in one JSON blob. Idempotent.
-- ─────────────────────────────────────────────────────────────────────────────
USE FinSight_AI;
SET NOCOUNT ON;

IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('Risk_Metrics') AND name = 'parametric_data'
)
BEGIN
    ALTER TABLE Risk_Metrics ADD parametric_data NVARCHAR(MAX) NULL;
    PRINT 'Added Risk_Metrics.parametric_data column.';
END
ELSE
    PRINT 'Risk_Metrics.parametric_data already exists, skipping.';
