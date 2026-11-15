select
    trial_id,
    analyte,
    unit,
    count(*) as measurement_count,
    count(*) filter (where is_out_of_range) as out_of_range_count,
    round(avg(result_value), 2) as average_result,
    min(result_value) as minimum_result,
    max(result_value) as maximum_result,
    round(
        100.0 * count(*) filter (where is_out_of_range) / nullif(count(*), 0),
        1
    ) as out_of_range_pct
from {{ ref('fct_lab_result') }}
group by trial_id, analyte, unit
