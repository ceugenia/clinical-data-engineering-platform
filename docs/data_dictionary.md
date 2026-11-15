# Data dictionary

All records are synthetic.

| Entity | Important fields | Description |
|---|---|---|
| patients | patient_id, trial_id, site_id, enrollment_date, age, sex, enrollment_status | Synthetic participant and enrollment attributes |
| trials | trial_id, trial_name, therapeutic_area, phase, site_count | Trial metadata |
| visits | visit_id, patient_id, visit_number, visit_type, visit_date, visit_status | Participant visit events |
| lab_results | lab_result_id, visit_id, analyte, result_value, unit, reference_low, reference_high | Synthetic lab measurements |

## Gold models
- `dim_patient`: one row per participant.
- `dim_trial`: one row per trial.
- `fct_visit`: one row per unique participant visit.
- `mart_trial_operations`: trial-level enrollment, visit completion, and lab out-of-range metrics.
