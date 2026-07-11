-- ─────────────────────────────────────────────────────────────────────────────
-- Auth migration — additive only, safe to run against the live production DB.
-- Unlike db_migration_fix.sql, this does NOT delete/recreate Portfolios (which
-- would violate the FK from Alerts/Risk_Metrics to Portfolios.portfolio_id and
-- destroy accumulated alert/risk history). Idempotent — safe to re-run.
-- ─────────────────────────────────────────────────────────────────────────────
USE FinSight_AI;
SET NOCOUNT ON;

-- ─────────────────────────────────────────────────────────────────────────────
-- STEP 1: Users table (fund managers — distinct from Customers, the institutions)
-- role: fund_manager | admin
-- ─────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Users' AND xtype='U')
BEGIN
    CREATE TABLE Users (
        user_id         INT IDENTITY(1,1) PRIMARY KEY,
        email           VARCHAR(255) NOT NULL UNIQUE,
        hashed_password VARCHAR(255) NOT NULL,
        full_name       VARCHAR(255) NOT NULL,
        role            VARCHAR(20)  NOT NULL CHECK (role IN ('fund_manager', 'admin')),
        created_at      DATETIME NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT 'Created Users table.';
END
ELSE
    PRINT 'Users table already exists, skipping.';
-- BATCH --

-- ─────────────────────────────────────────────────────────────────────────────
-- STEP 2: Portfolios.manager_id FK (one owner per portfolio)
-- ─────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('Portfolios') AND name = 'manager_id'
)
BEGIN
    ALTER TABLE Portfolios ADD manager_id INT NULL;
    ALTER TABLE Portfolios ADD CONSTRAINT FK_Portfolios_Manager
        FOREIGN KEY (manager_id) REFERENCES Users(user_id);
    PRINT 'Added Portfolios.manager_id column + FK.';
END
ELSE
    PRINT 'Portfolios.manager_id already exists, skipping.';
-- BATCH --

-- ─────────────────────────────────────────────────────────────────────────────
-- STEP 3: Seed 5 demo fund managers + 1 admin
-- Shared demo password 'FinSight2026!' (synthetic dataset — see AUTH.md)
-- ─────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM Users WHERE email = 'sarah.chen@finsight.demo')
INSERT INTO Users (email, hashed_password, full_name, role) VALUES
('sarah.chen@finsight.demo',     '$2b$12$d94X9qQeMw2TxMm8z32Hp.IhbfbXO9MCOgUAJOOjhqW8FrIgFyEii', 'Sarah Chen',     'fund_manager'),
('james.okafor@finsight.demo',   '$2b$12$d94X9qQeMw2TxMm8z32Hp.IhbfbXO9MCOgUAJOOjhqW8FrIgFyEii', 'James Okafor',   'fund_manager'),
('priya.patel@finsight.demo',    '$2b$12$d94X9qQeMw2TxMm8z32Hp.IhbfbXO9MCOgUAJOOjhqW8FrIgFyEii', 'Priya Patel',    'fund_manager'),
('david.kim@finsight.demo',      '$2b$12$d94X9qQeMw2TxMm8z32Hp.IhbfbXO9MCOgUAJOOjhqW8FrIgFyEii', 'David Kim',      'fund_manager'),
('elena.rodriguez@finsight.demo','$2b$12$d94X9qQeMw2TxMm8z32Hp.IhbfbXO9MCOgUAJOOjhqW8FrIgFyEii', 'Elena Rodriguez','fund_manager'),
('admin@finsight.demo',          '$2b$12$d94X9qQeMw2TxMm8z32Hp.IhbfbXO9MCOgUAJOOjhqW8FrIgFyEii', 'Marcus Webb',    'admin');
-- BATCH --

-- ─────────────────────────────────────────────────────────────────────────────
-- STEP 4: Backfill manager_id — 50 portfolios split ~10 each across 5 managers
-- Grouped by customer block to keep each manager's book coherent
-- ─────────────────────────────────────────────────────────────────────────────
DECLARE @sarah INT  = (SELECT user_id FROM Users WHERE email = 'sarah.chen@finsight.demo');
DECLARE @james INT  = (SELECT user_id FROM Users WHERE email = 'james.okafor@finsight.demo');
DECLARE @priya INT  = (SELECT user_id FROM Users WHERE email = 'priya.patel@finsight.demo');
DECLARE @david INT  = (SELECT user_id FROM Users WHERE email = 'david.kim@finsight.demo');
DECLARE @elena INT  = (SELECT user_id FROM Users WHERE email = 'elena.rodriguez@finsight.demo');

-- Sarah Chen: BlackRock, Vanguard, SSGA, Fidelity (1-10)
UPDATE Portfolios SET manager_id = @sarah WHERE portfolio_id BETWEEN 1  AND 10;
-- James Okafor: Fidelity(11), PIMCO, GSAM, JPM AM, MS IM (11-20)
UPDATE Portfolios SET manager_id = @james WHERE portfolio_id BETWEEN 11 AND 20;
-- Priya Patel: TRP, Wellington, Bridgewater, Renaissance, Citadel(30) (21-30)
UPDATE Portfolios SET manager_id = @priya WHERE portfolio_id BETWEEN 21 AND 30;
-- David Kim: Citadel(31), Two Sigma, AQR, Norway GPFG, ADIA (31-40)
UPDATE Portfolios SET manager_id = @david WHERE portfolio_id BETWEEN 31 AND 40;
-- Elena Rodriguez: CalPERS, OTPP, Rockefeller (41-50)
UPDATE Portfolios SET manager_id = @elena WHERE portfolio_id BETWEEN 41 AND 50;

PRINT 'Backfilled manager_id for 50 portfolios.';
PRINT '';
PRINT 'Users:';
SELECT user_id, email, full_name, role FROM Users ORDER BY user_id;
PRINT '';
PRINT 'Portfolios per manager:';
SELECT u.full_name, u.role, COUNT(p.portfolio_id) AS portfolio_count
FROM Users u LEFT JOIN Portfolios p ON p.manager_id = u.user_id
GROUP BY u.full_name, u.role
ORDER BY u.full_name;
PRINT '';
PRINT 'Unassigned portfolios (should be 0):';
SELECT COUNT(*) AS unassigned FROM Portfolios WHERE manager_id IS NULL;
