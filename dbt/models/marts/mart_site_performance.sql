with participant_counts as (
    select
        trial_id,
        site_id,
        count(*) as participant_count,
        count(*) filter (where enrollment_status = 'Enrolled') as enrolled_count
    from {{ ref('dim_patient') }}
    group by trial_id, site_id
),
visit_counts as (
    select
        patient.trial_id,
        patient.site_id,
        count(*) as total_visits,
        count(*) filter (where visit.visit_status = 'Completed') as completed_visits,
        count(*) filter (where visit.visit_status = 'Missed') as missed_visits
    from {{ ref('fct_visit') }} as visit
    inner join {{ ref('dim_patient') }} as patient
        on visit.patient_id = patient.patient_id
    group by patient.trial_id, patient.site_id
)
select
    participant.trial_id,
    participant.site_id,
    participant.participant_count,
    participant.enrolled_count,
    coalesce(visit.total_visits, 0) as total_visits,
    coalesce(visit.completed_visits, 0) as completed_visits,
    coalesce(visit.missed_visits, 0) as missed_visits,
    round(
        100.0 * visit.completed_visits / nullif(visit.total_visits, 0),
        1
    ) as visit_completion_pct
from participant_counts as participant
left join visit_counts as visit
    on participant.trial_id = visit.trial_id
    and participant.site_id = visit.site_id
