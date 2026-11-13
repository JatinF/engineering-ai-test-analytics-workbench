select
  b.tenant_id,
  b.build_id,
  count(r.run_id) as runs,
  sum(case when r.status = 'pass' then 1 else 0 end) as passes,
  (1.0 * sum(case when r.status = 'pass' then 1 else 0 end)) / count(r.run_id) as pass_rate
from {{ ref('firmware_builds') }} b
join {{ ref('test_runs') }} r
  on r.tenant_id = b.tenant_id and r.build_id = b.build_id
group by b.tenant_id, b.build_id
