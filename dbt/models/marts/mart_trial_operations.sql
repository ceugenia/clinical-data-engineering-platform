with p as (
 select trial_id, count(*) participant_count,
 count(*) filter (where enrollment_status = 'Enrolled') enrolled_count,
 count(*) filter (where enrollment_status = 'Completed') completed_participant_count,
 round(avg(age), 1) average_participant_age
 from {{ ref('dim_patient') }} group by trial_id
), v as (
 select trial_id, count(*) total_visits,
 count(*) filter (where visit_status = 'Completed') completed_visits,
 count(*) filter (where visit_status = 'Missed') missed_visits
 from {{ ref('fct_visit') }} group by trial_id
), l as (
 select trial_id, count(*) lab_measurements,
 count(*) filter (where is_out_of_range) out_of_range_results
 from {{ ref('stg_lab_results') }} group by trial_id
)
select t.trial_id, t.trial_name, t.therapeutic_area, t.phase, t.site_count,
 coalesce(p.participant_count, 0) participant_count,
 coalesce(p.enrolled_count, 0) enrolled_count,
 coalesce(p.completed_participant_count, 0) completed_participant_count,
 p.average_participant_age, coalesce(v.total_visits, 0) total_visits,
 coalesce(v.completed_visits, 0) completed_visits, coalesce(v.missed_visits, 0) missed_visits,
 round(100.0 * v.completed_visits / nullif(v.total_visits, 0), 1) visit_completion_pct,
 coalesce(l.lab_measurements, 0) lab_measurements,
 coalesce(l.out_of_range_results, 0) out_of_range_results,
 round(100.0 * l.out_of_range_results / nullif(l.lab_measurements, 0), 1) out_of_range_pct
from {{ ref('dim_trial') }} t
left join p using (trial_id)
left join v using (trial_id)
left join l using (trial_id)
