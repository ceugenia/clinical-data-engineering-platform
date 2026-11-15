select
 patient_id::varchar as patient_id, trial_id::varchar as trial_id,
 site_id::varchar as site_id, enrollment_date::date as enrollment_date,
 age::integer as age, sex::varchar as sex, enrollment_status::varchar as enrollment_status
from read_parquet('{{ var("silver_dir") }}/patients.parquet')
