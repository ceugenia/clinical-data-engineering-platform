select patient_id, trial_id, site_id, enrollment_date, age, sex, enrollment_status
from {{ ref('stg_patients') }}
