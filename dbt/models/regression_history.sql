with code_dim as (
  select distinct tenant_id, code from {{ ref('failures') }}
),
run_counts as (
  select tenant_id, build_id, count(*) as runs
  from {{ ref('test_runs') }}
  group by tenant_id, build_id
),
fail_counts as (
  select tenant_id, build_id, code, count(*) as failures
  from {{ ref('failures') }}
  group by tenant_id, build_id, code
),
rates as (
  select
    b.tenant_id,
    b.build_id,
    c.code as code,
    rc.runs as runs,
    coalesce(fc.failures, 0) as failures,
    (1.0 * coalesce(fc.failures, 0)) / rc.runs as rate
  from {{ ref('firmware_builds') }} b
  join code_dim c on c.tenant_id = b.tenant_id
  join run_counts rc on rc.tenant_id = b.tenant_id and rc.build_id = b.build_id
  left join fail_counts fc
    on fc.tenant_id = b.tenant_id
    and fc.build_id = b.build_id
    and fc.code = c.code
)
select
  tenant_id,
  build_id,
  code,
  runs,
  failures,
  rate,
  avg(rate) over (
    partition by tenant_id, code
    order by build_id
    rows between unbounded preceding and 1 preceding
  ) as prior_mean
from rates
