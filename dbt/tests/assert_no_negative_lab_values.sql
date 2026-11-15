select * from {{ ref('stg_lab_results') }} where result_value < 0
