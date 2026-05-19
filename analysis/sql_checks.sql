-- Point-in-time feature validation checks for a quantitative research workflow.

-- 1. Block features whose values arrive after the label date.
select
  feature_id,
  count(*) as row_count,
  sum(point_in_time_violation) as late_rows,
  100.0 * sum(point_in_time_violation) / count(*) as late_rate_pct
from daily_metrics
group by 1
having sum(point_in_time_violation) > 0
order by late_rate_pct desc;

-- 2. Cross-sectional feature coverage by sector and day.
select
  as_of_date,
  feature_id,
  sector,
  avg(case when missing_flag = 1 then 1.0 else 0.0 end) as missing_rate
from daily_metrics
group by 1, 2, 3
having missing_rate > 0.05;

-- 3. Vendor feed health summary for production monitoring.
select
  feature_id,
  avg(missing_flag) as missing_rate,
  avg(duplicate_flag) as duplicate_rate,
  avg(restated_flag) as restatement_rate,
  avg(julianday(availability_date) - julianday(as_of_date)) as avg_latency_days
from daily_metrics
group by 1
order by restatement_rate desc, avg_latency_days desc;

-- 4. Research event root-cause queue.
select
  feature_id,
  event_type,
  severity,
  count(*) as events,
  sum(estimated_research_hours_at_risk) as research_hours_at_risk
from source_events
group by 1, 2, 3
order by research_hours_at_risk desc;
