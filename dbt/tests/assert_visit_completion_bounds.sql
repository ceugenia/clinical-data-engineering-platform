select * from {{ ref('mart_trial_operations') }}
where visit_completion_pct < 0 or visit_completion_pct > 100
