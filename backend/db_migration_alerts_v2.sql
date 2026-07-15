-- Additive migration for the Alerts table — adds columns needed to collapse
-- re-triggering threshold alerts into a single row instead of one row per
-- risk_job run. Non-destructive: existing rows are preserved, only gain new
-- columns with backfilled defaults.
--
-- Safe to run against a live Alerts table with existing data. Not part of
-- db_migration_fix.sql (that file wipes/reseeds everything from scratch and
-- never included Alerts — the table is created at runtime via
-- Base.metadata.create_all(), which does not ALTER existing tables).

ALTER TABLE Alerts ADD status VARCHAR(20) NOT NULL CONSTRAINT DF_Alerts_status DEFAULT 'active';
ALTER TABLE Alerts ADD occurrence_count INT NOT NULL CONSTRAINT DF_Alerts_occurrence_count DEFAULT 1;
ALTER TABLE Alerts ADD resolved_at DATETIME NULL;

-- last_triggered_at needs to backfill from each row's own triggered_at value,
-- not "now" — so add nullable, backfill, then tighten to NOT NULL.
ALTER TABLE Alerts ADD last_triggered_at DATETIME NULL;
UPDATE Alerts SET last_triggered_at = triggered_at WHERE last_triggered_at IS NULL;
ALTER TABLE Alerts ALTER COLUMN last_triggered_at DATETIME NOT NULL;
