select
 lab_result_id::varchar as lab_result_id, patient_id::varchar as patient_id,
 trial_id::varchar as trial_id, visit_id::varchar as visit_id,
 collection_date::date as collection_date, analyte::varchar as analyte,
 result_value::double as result_value, unit::varchar as unit,
 reference_low::double as reference_low, reference_high::double as reference_high,
 (result_value < reference_low or result_value > reference_high) as is_out_of_range
from read_parquet('{{ var("silver_dir") }}/lab_results.parquet')
