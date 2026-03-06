-- cost_dashboard.sql
-- DuckDB queries that produce the same three summary tables as cost_dashboard.py.
--
-- Usage (replace <csv_path> with your actual path):
--
--   duckdb -c ".read scripts/cost_dashboard.sql" -c "SET csv_path='data/sample_billing.csv';"
--
-- Or run interactively in DuckDB:
--   duckdb
--   SET VARIABLE csv_path = 'data/sample_billing.csv';
--   .read scripts/cost_dashboard.sql
--
-- Each query can also be run standalone by substituting the path literal.

-- ---------------------------------------------------------------------------
-- Helper: load the CSV into a temp view with clean types
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW billing AS
SELECT
    CAST(Date AS DATE)                                   AS Date,
    "Organization Plan",
    "Entity Name",
    "Entity Type",
    CSP,
    Region,
    "Warehouse ID",
    "Service ID",
    COALESCE(TRY_CAST("Compute Cost" AS DOUBLE), 0.0)   AS "Compute Cost",
    COALESCE(TRY_CAST("Storage Cost" AS DOUBLE), 0.0)   AS "Storage Cost",
    COALESCE(TRY_CAST("Network Cost" AS DOUBLE), 0.0)   AS "Network Cost",
    COALESCE(TRY_CAST("Request Cost" AS DOUBLE), 0.0)   AS "Request Cost",
    COALESCE(TRY_CAST("Other Cost"   AS DOUBLE), 0.0)   AS "Other Cost",
    COALESCE(TRY_CAST("Total Cost"   AS DOUBLE), 0.0)   AS "Total Cost"
FROM read_csv_auto(getvariable('csv_path'), header=true, nullstr='');

-- ---------------------------------------------------------------------------
-- Table 1: Daily totals with day-over-day change
-- ---------------------------------------------------------------------------
WITH daily AS (
    SELECT
        Date,
        ROUND(SUM("Total Cost"), 4) AS total_usd
    FROM billing
    GROUP BY Date
    ORDER BY Date
)
SELECT
    Date,
    total_usd,
    ROUND(total_usd - LAG(total_usd) OVER (ORDER BY Date), 4) AS dod_change
FROM daily
ORDER BY Date;

-- ---------------------------------------------------------------------------
-- Table 2: Spend by dimensions
-- ---------------------------------------------------------------------------
SELECT
    "Organization Plan",
    "Entity Name",
    "Entity Type",
    CSP,
    Region,
    "Warehouse ID",
    "Service ID",
    ROUND(SUM("Total Cost"), 4) AS total_usd
FROM billing
GROUP BY ALL
ORDER BY total_usd DESC;

-- ---------------------------------------------------------------------------
-- Table 3: Cost-component breakdown
-- ---------------------------------------------------------------------------
SELECT cost_component, ROUND(total_usd, 4) AS total_usd
FROM (
    VALUES
        ('Compute Cost', (SELECT SUM("Compute Cost") FROM billing)),
        ('Storage Cost', (SELECT SUM("Storage Cost") FROM billing)),
        ('Network Cost', (SELECT SUM("Network Cost") FROM billing)),
        ('Request Cost', (SELECT SUM("Request Cost") FROM billing)),
        ('Other Cost',   (SELECT SUM("Other Cost")   FROM billing)),
        ('Total Cost',   (SELECT SUM("Total Cost")   FROM billing))
) AS t(cost_component, total_usd)
ORDER BY total_usd DESC;
