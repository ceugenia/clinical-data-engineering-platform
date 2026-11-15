select
 visit_id::varchar as visit_id, patient_id::varchar as patient_id,
 trial_id::varchar as trial_id, visit_number::integer as visit_number,
 visit_type::varchar as visit_type, visit_date::date as visit_date,
 visit_status::varchar as visit_status
from read_parquet('{{ var("silver_dir") }}/visits.parquet')
