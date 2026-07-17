-- Additive migration for the Alerts table — adds read_at so the alert-mute
-- cooldown (backend/services/alert_engine.py) can tell how long ago an alert
-- was acknowledged. Non-destructive; safe against a live Alerts table.

ALTER TABLE Alerts ADD read_at DATETIME NULL;

-- Backfill: any row already marked read has no recorded read timestamp yet.
-- Approximate with last_triggered_at (best available signal) so pre-existing
-- read alerts aren't treated as "just read" (which would restart their mute
-- window) or as "never read" (which would make them immediately eligible to
-- resurface with no cooldown at all).
UPDATE Alerts SET read_at = last_triggered_at WHERE is_read = 1 AND read_at IS NULL;

-- Safety net: 003_alerts_v2.sql made last_triggered_at NOT NULL with no
-- server-side default (relying on the ORM's client-side default instead). Any
-- code still running the OLD alert_engine.py (unaware this column exists at all)
-- would omit it from its INSERTs and violate the NOT NULL constraint. A DB-level
-- default makes old-code inserts survive regardless of deploy timing/order.
ALTER TABLE Alerts ADD CONSTRAINT DF_Alerts_last_triggered_at DEFAULT GETUTCDATE() FOR last_triggered_at;
