# Data dictionary

All records are synthetic. Identifiers are generated for this portfolio demonstration and do not refer to real people, sites, or studies.

| Entity | Important fields | Description |
|---|---|---|
| `patients` | `patient_id`, `trial_id`, `site_id`, `enrollment_date`, `age`, `sex`, `enrollment_status`, `source_updated_at` | Synthetic participant and enrollment attributes |
| `trials` | `trial_id`, `trial_name`, `therapeutic_area`, `phase`, `site_count` | Synthetic trial metadata |
| `visits` | `visit_id`, `patient_id`, `trial_id`, `visit_number`, `visit_type`, `visit_date`, `visit_status`, `source_updated_at` | Participant visit events |
| `lab_results` | `lab_result_id`, `visit_id`, `analyte`, `result_value`, `unit`, `reference_low`, `reference_high`, `source_updated_at` | Synthetic laboratory measurements |

## dbt models

- `dim_patient`: one row per participant.
- `dim_trial`: one row per trial.
- `fct_visit`: one row per unique participant visit.
- `fct_lab_result`: one row per unique lab measurement, including reference-range flag.
- `mart_trial_operations`: trial-level participant, visit, and lab metrics.
- `mart_lab_analyte`: measurement counts, averages, and out-of-range metrics by analyte and unit.
- `mart_site_performance`: participant and visit metrics by trial and site.

## Operational metadata

- Bronze `manifest.json`: batch ID, status, timestamps, source file names, and row counts.
- Bronze `_SUCCESS`: marker written only after all batch files and manifest are complete.
- `quality/quality_report.json`: successful checks, source/Silver row counts, and deduplicated row counts.
- `warehouse/pipeline_runs.jsonl`: one JSON record per pipeline execution, including status, duration, row counts, dbt status, and failure stage.

## Notes

The synthetic lab ranges and measurements are illustrative. They must not be interpreted as medical reference intervals.
