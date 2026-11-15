select
 visit_id, patient_id, trial_id, visit_number, visit_type, visit_date, visit_status,
 case when visit_status = 'Completed' then 1 else 0 end as completed_flag
from {{ ref('stg_visits') }}
