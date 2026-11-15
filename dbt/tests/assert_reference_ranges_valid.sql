select *
from {{ ref('fct_lab_result') }}
where reference_low > reference_high
