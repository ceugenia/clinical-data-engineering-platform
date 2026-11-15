select
 trial_id::varchar as trial_id, trial_name::varchar as trial_name,
 therapeutic_area::varchar as therapeutic_area, phase::varchar as phase,
 site_count::integer as site_count
from read_parquet('{{ var("silver_dir") }}/trials.parquet')
