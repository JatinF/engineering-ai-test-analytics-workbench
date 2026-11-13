"""SQL semantic model. The same selects are mirrored under dbt/models."""

BUILD_QUALITY_SQL = """
SELECT
  b.tenant_id,
  b.build_id,
  COUNT(r.run_id) AS runs,
  SUM(CASE WHEN r.status = 'pass' THEN 1 ELSE 0 END) AS passes,
  (1.0 * SUM(CASE WHEN r.status = 'pass' THEN 1 ELSE 0 END)) / COUNT(r.run_id) AS pass_rate
FROM firmware_builds b
JOIN test_runs r ON r.tenant_id = b.tenant_id AND r.build_id = b.build_id
GROUP BY b.tenant_id, b.build_id
"""

FAILURE_TREND_SQL = """
SELECT tenant_id, build_id, code, COUNT(*) AS failures
FROM failures
GROUP BY tenant_id, build_id, code
"""

REGRESSION_HISTORY_SQL = """
WITH code_dim AS (
  SELECT DISTINCT tenant_id, code FROM failures
),
run_counts AS (
  SELECT tenant_id, build_id, COUNT(*) AS runs
  FROM test_runs
  GROUP BY tenant_id, build_id
),
fail_counts AS (
  SELECT tenant_id, build_id, code, COUNT(*) AS failures
  FROM failures
  GROUP BY tenant_id, build_id, code
),
rates AS (
  SELECT
    b.tenant_id,
    b.build_id,
    c.code AS code,
    rc.runs AS runs,
    COALESCE(fc.failures, 0) AS failures,
    (1.0 * COALESCE(fc.failures, 0)) / rc.runs AS rate
  FROM firmware_builds b
  JOIN code_dim c ON c.tenant_id = b.tenant_id
  JOIN run_counts rc ON rc.tenant_id = b.tenant_id AND rc.build_id = b.build_id
  LEFT JOIN fail_counts fc
    ON fc.tenant_id = b.tenant_id
    AND fc.build_id = b.build_id
    AND fc.code = c.code
)
SELECT
  tenant_id,
  build_id,
  code,
  runs,
  failures,
  rate,
  AVG(rate) OVER (
    PARTITION BY tenant_id, code
    ORDER BY build_id
    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
  ) AS prior_mean
FROM rates
"""

VIEWS = (
    ("build_quality", BUILD_QUALITY_SQL),
    ("failure_trend", FAILURE_TREND_SQL),
    ("regression_history", REGRESSION_HISTORY_SQL),
)

LINEAGE = (
    ("firmware_builds", "seed"),
    ("test_runs", "seed"),
    ("failures", "seed"),
    ("log_chunks", "seed"),
    ("telemetry", "seed"),
    ("build_quality", "firmware_builds"),
    ("build_quality", "test_runs"),
    ("failure_trend", "failures"),
    ("regression_history", "firmware_builds"),
    ("regression_history", "test_runs"),
    ("regression_history", "failures"),
)

# Rate jump used by the agent. The SQL view does not encode this cutoff.
RATE_JUMP = 0.10
