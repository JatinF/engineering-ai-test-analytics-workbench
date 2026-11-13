select tenant_id, build_id, code, count(*) as failures
from {{ ref('failures') }}
group by tenant_id, build_id, code
