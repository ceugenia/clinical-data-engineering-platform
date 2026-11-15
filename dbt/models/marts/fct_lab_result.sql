select
    lab_result_id,
    patient_id,
    trial_id,
    visit_id,
    collection_date,
    analyte,
    result_value,
    unit,
    reference_low,
    reference_high,
    is_out_of_range
from {{ ref('stg_lab_results') }}
