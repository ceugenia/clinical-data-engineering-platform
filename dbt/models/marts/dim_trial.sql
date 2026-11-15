select trial_id, trial_name, therapeutic_area, phase, site_count
from {{ ref('stg_trials') }}
