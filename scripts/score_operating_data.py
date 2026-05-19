import csv
import json
import math
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "analysis" / "outputs"
ANALYSIS = ROOT / "analysis"
SEED = 20260519


def business_days(start, end):
    current = start
    days = []
    while current <= end:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def rank(values):
    ordered = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    i = 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and ordered[j + 1][0] == ordered[i][0]:
            j += 1
        avg = (i + j + 2) / 2
        for k in range(i, j + 1):
            ranks[ordered[k][1]] = avg
        i = j + 1
    return ranks


def corr(x_values, y_values):
    if len(x_values) < 3:
        return 0.0
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    x_var = sum((x - x_mean) ** 2 for x in x_values)
    y_var = sum((y - y_mean) ** 2 for y in y_values)
    if x_var == 0 or y_var == 0:
        return 0.0
    return numerator / math.sqrt(x_var * y_var)


def spearman(x_values, y_values):
    return corr(rank(x_values), rank(y_values))


def quantile(values, q):
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int(q * (len(ordered) - 1))))
    return ordered[index]


def psi(base_values, recent_values, buckets=8):
    if not base_values or not recent_values:
        return 0.0
    cuts = [quantile(base_values, i / buckets) for i in range(1, buckets)]
    base_counts = [0] * buckets
    recent_counts = [0] * buckets
    for collection, counts in [(base_values, base_counts), (recent_values, recent_counts)]:
        for value in collection:
            bucket = 0
            while bucket < len(cuts) and value > cuts[bucket]:
                bucket += 1
            counts[bucket] += 1
    score = 0.0
    for base_count, recent_count in zip(base_counts, recent_counts):
        base_pct = max(base_count / len(base_values), 0.001)
        recent_pct = max(recent_count / len(recent_values), 0.001)
        score += (recent_pct - base_pct) * math.log(recent_pct / base_pct)
    return score


def pct(value):
    return round(100 * value, 2)


def make_catalog():
    vendors = ["Core fundamentals", "Earnings text", "Supply chain web", "Hiring feeds", "Analyst revisions", "Card spend"]
    categories = ["fundamental", "text", "alternative", "labor", "estimate", "transaction"]
    theses = [
        "Revision acceleration captures slow analyst incorporation after guidance changes.",
        "Gross margin pressure appears before consensus models absorb cost shocks.",
        "Hiring intensity gives an early read on operating momentum by peer group.",
        "Supplier disruption language precedes inventory and revenue misses.",
        "Web demand momentum helps separate real growth from channel stuffing.",
        "Payment share shifts reveal changing consumer traction across peers.",
        "Filings sentiment flags balance-sheet stress before the next reporting cycle.",
        "Price realization captures sector-level demand resilience.",
        "Inventory drift indicates future discounting pressure.",
        "Customer concentration alerts identify names with brittle revenue quality.",
        "Late vendor restatements can create false alpha if backfilled into training.",
        "News burst decay captures temporary attention effects that should fade.",
        "Estimate dispersion reflects disagreement that may amplify return skew.",
        "Short interest crowding identifies fragile momentum exposures.",
        "Disclosure lag flags issuer groups where features need stricter availability rules.",
        "Macro beta residuals isolate company-specific information from market noise.",
    ]
    catalog = []
    for index in range(16):
        feature_id = f"FEAT{index + 1:03d}"
        vendor = vendors[index % len(vendors)]
        category = categories[index % len(categories)]
        true_ic = [0.052, 0.041, 0.034, 0.027, 0.018, 0.010, -0.006, 0.046][index % 8]
        if index in [5, 10]:
            true_ic += 0.035
        base_latency = [1, 2, 1, 3, 2, 1, 5, 0][index % 8]
        if index == 10:
            base_latency = 8
        catalog.append(
            {
                "feature_id": feature_id,
                "feature_name": f"{vendor} signal {index + 1}",
                "category": category,
                "vendor_family": vendor,
                "cadence": "daily" if index % 3 else "weekly",
                "expected_sign": 1 if true_ic >= 0 else -1,
                "true_ic_assumption": round(true_ic, 4),
                "base_latency_days": base_latency,
                "owner": ["Research", "Feature engineering", "Data operations", "ML platform"][index % 4],
                "thesis": theses[index],
            }
        )
    return catalog


def make_security_master():
    sectors = ["Technology", "Consumer", "Healthcare", "Industrials", "Financials", "Energy"]
    rows = []
    for index in range(48):
        sector = sectors[index % len(sectors)]
        rows.append(
            {
                "security_id": f"SEC{index + 1:03d}",
                "ticker": f"Q{index + 1:03d}",
                "sector": sector,
                "market_cap_bucket": ["large", "mid", "small"][index % 3],
                "liquidity_bucket": ["high", "medium", "low"][(index + 1) % 3],
            }
        )
    return rows


def generate_raw_data():
    random.seed(SEED)
    DATA.mkdir(exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    features = make_catalog()
    securities = make_security_master()
    dates = business_days(date(2025, 10, 1), date(2026, 2, 27))
    sector_shock = defaultdict(float)
    panel = []
    events = []
    actions = []

    for d in dates:
        for sector in sorted({row["sector"] for row in securities}):
            sector_shock[(d.isoformat(), sector)] = random.gauss(0, 0.006)

    for feature in features:
        feature_bias = random.gauss(0, 0.15)
        drift_start = len(dates) * (0.58 + random.random() * 0.18)
        for security in securities:
            security_effect = random.gauss(0, 0.8)
            previous_value = random.gauss(0, 1)
            for day_index, d in enumerate(dates):
                drift = max(0, day_index - drift_start) / len(dates)
                raw_value = (
                    0.72 * previous_value
                    + 0.28 * random.gauss(0, 1)
                    + feature_bias
                    + security_effect * 0.18
                    + drift * random.choice([-1, 1]) * (0.8 if feature["feature_id"] in ["FEAT006", "FEAT011", "FEAT015"] else 0.25)
                )
                previous_value = raw_value
                latency = max(0, int(random.gauss(feature["base_latency_days"], 1.1)))
                if feature["feature_id"] in ["FEAT011", "FEAT015"] and random.random() < 0.18:
                    latency += random.randint(3, 8)
                availability_date = d + timedelta(days=latency)
                label_date = d + timedelta(days=7)
                missing = random.random() < (0.012 + (0.03 if feature["feature_id"] in ["FEAT004", "FEAT015"] else 0))
                duplicate = random.random() < (0.003 + (0.015 if feature["feature_id"] == "FEAT006" else 0))
                restated = random.random() < (0.008 + (0.045 if feature["feature_id"] in ["FEAT011", "FEAT013"] else 0))
                leakage_flag = availability_date > label_date
                signal_component = feature["expected_sign"] * feature["true_ic_assumption"] * raw_value
                forward_return = (
                    signal_component
                    + sector_shock[(d.isoformat(), security["sector"])]
                    + random.gauss(0, 0.035)
                )
                if missing:
                    raw_value_text = ""
                else:
                    raw_value_text = round(raw_value, 5)
                panel.append(
                    {
                        "as_of_date": d.isoformat(),
                        "label_date": label_date.isoformat(),
                        "availability_date": availability_date.isoformat(),
                        "feature_id": feature["feature_id"],
                        "security_id": security["security_id"],
                        "sector": security["sector"],
                        "raw_value": raw_value_text,
                        "feature_value": "" if missing else round(feature["expected_sign"] * raw_value, 5),
                        "forward_5d_return": round(forward_return, 5),
                        "missing_flag": int(missing),
                        "duplicate_flag": int(duplicate),
                        "restated_flag": int(restated),
                        "point_in_time_violation": int(leakage_flag),
                    }
                )

    event_types = ["late_delivery", "schema_shift", "missing_spike", "duplicate_records", "restatement", "research_question"]
    for index in range(360):
        feature = random.choice(features)
        event_date = random.choice(dates)
        event_type = random.choice(event_types)
        severity = random.choices(["low", "medium", "high", "critical"], [0.35, 0.35, 0.22, 0.08])[0]
        if feature["feature_id"] in ["FEAT006", "FEAT011", "FEAT015"] and event_type != "research_question":
            severity = random.choices(["medium", "high", "critical"], [0.35, 0.45, 0.20])[0]
        impact = random.randint(18000, 145000) * {"low": 0.45, "medium": 0.85, "high": 1.25, "critical": 1.75}[severity]
        events.append(
            {
                "event_id": f"EV{index + 1:04d}",
                "event_date": event_date.isoformat(),
                "feature_id": feature["feature_id"],
                "event_type": event_type,
                "severity": severity,
                "estimated_research_hours_at_risk": round(impact / 21000, 1),
                "root_cause": {
                    "late_delivery": "vendor latency exceeded training cutoff",
                    "schema_shift": "new categorical value appeared without contract update",
                    "missing_spike": "source collection coverage dropped by peer group",
                    "duplicate_records": "publisher resend created duplicate observations",
                    "restatement": "historical value changed after first availability",
                    "research_question": "researcher asked whether signal survives stricter validation",
                }[event_type],
            }
        )

    action_types = ["promote", "watch", "repair", "quarantine", "retire"]
    for index in range(96):
        feature = features[index % len(features)]
        action_type = action_types[(index + random.randint(0, 4)) % len(action_types)]
        actions.append(
            {
                "action_id": f"ACT{index + 1:03d}",
                "feature_id": feature["feature_id"],
                "action_type": action_type,
                "owner": feature["owner"],
                "effort_hours": random.randint(4, 38),
                "expected_research_value": random.randint(2, 17) * 10000,
                "note": {
                    "promote": "Package for next research review with monitoring guardrails.",
                    "watch": "Keep in candidate set but require another validation window.",
                    "repair": "Fix curation issue before using in model training.",
                    "quarantine": "Block from training data until point-in-time defect is resolved.",
                    "retire": "Remove from active queue unless a stronger economic thesis appears.",
                }[action_type],
            }
        )

    write_csv(DATA / "entities.csv", features, list(features[0].keys()))
    write_csv(DATA / "security_master.csv", securities, list(securities[0].keys()))
    write_csv(DATA / "daily_metrics.csv", panel, list(panel[0].keys()))
    write_csv(DATA / "source_events.csv", events, list(events[0].keys()))
    write_csv(DATA / "recommended_actions.csv", actions, list(actions[0].keys()))
    return features, securities, panel, events, actions


def aggregate_validations(features, panel, events, actions):
    by_feature = defaultdict(list)
    by_feature_date = defaultdict(lambda: defaultdict(list))
    for row in panel:
        by_feature[row["feature_id"]].append(row)
        by_feature_date[row["feature_id"]][row["as_of_date"]].append(row)

    event_hours = defaultdict(float)
    critical_events = defaultdict(int)
    for event in events:
        event_hours[event["feature_id"]] += float(event["estimated_research_hours_at_risk"])
        if event["severity"] in ["high", "critical"]:
            critical_events[event["feature_id"]] += 1

    action_value = defaultdict(float)
    for action in actions:
        action_value[action["feature_id"]] += float(action["expected_research_value"])

    rows = []
    deciles = []
    stationarity = []
    pit = []
    feed = []
    memos = []

    for feature in features:
        feature_id = feature["feature_id"]
        rows_for_feature = by_feature[feature_id]
        valid_rows = [row for row in rows_for_feature if row["feature_value"] != ""]
        daily_ics = []
        daily_spreads = []
        daily_counts = []
        for as_of_date, daily_rows in sorted(by_feature_date[feature_id].items()):
            valid_daily = [row for row in daily_rows if row["feature_value"] != ""]
            if len(valid_daily) < 12:
                continue
            values = [float(row["feature_value"]) for row in valid_daily]
            returns = [float(row["forward_5d_return"]) for row in valid_daily]
            daily_ics.append(spearman(values, returns))
            ordered = sorted(valid_daily, key=lambda item: float(item["feature_value"]))
            size = max(3, len(ordered) // 10)
            low = sum(float(row["forward_5d_return"]) for row in ordered[:size]) / size
            high = sum(float(row["forward_5d_return"]) for row in ordered[-size:]) / size
            daily_spreads.append(high - low)
            daily_counts.append(len(valid_daily))

        midpoint = len(daily_ics) // 2
        train_ic = sum(daily_ics[:midpoint]) / max(1, midpoint)
        test_ic = sum(daily_ics[midpoint:]) / max(1, len(daily_ics) - midpoint)
        mean_ic = sum(daily_ics) / max(1, len(daily_ics))
        mean_spread = sum(daily_spreads) / max(1, len(daily_spreads))
        first_values = [float(row["feature_value"]) for row in valid_rows[: len(valid_rows) // 2]]
        last_values = [float(row["feature_value"]) for row in valid_rows[len(valid_rows) // 2 :]]
        drift_psi = psi(first_values, last_values)
        missing_rate = sum(int(row["missing_flag"]) for row in rows_for_feature) / len(rows_for_feature)
        duplicate_rate = sum(int(row["duplicate_flag"]) for row in rows_for_feature) / len(rows_for_feature)
        restatement_rate = sum(int(row["restated_flag"]) for row in rows_for_feature) / len(rows_for_feature)
        pit_failures = sum(int(row["point_in_time_violation"]) for row in rows_for_feature)
        pit_failure_rate = pit_failures / len(rows_for_feature)
        avg_latency = sum(
            (date.fromisoformat(row["availability_date"]) - date.fromisoformat(row["as_of_date"])).days
            for row in rows_for_feature
        ) / len(rows_for_feature)
        health_score = max(0, 100 - pct(missing_rate) * 1.1 - pct(duplicate_rate) * 1.8 - pct(restatement_rate) * 1.5 - pct(pit_failure_rate) * 3.5)
        stability_score = max(0, 100 - min(60, drift_psi * 120) - min(30, abs(train_ic - test_ic) * 220))
        signal_score = max(0, min(100, 50 + mean_ic * 520 + mean_spread * 700))
        promotion_score = round(signal_score * 0.45 + health_score * 0.30 + stability_score * 0.25, 1)
        if pit_failure_rate > 0.015 or health_score < 72:
            decision = "quarantine"
        elif promotion_score >= 72 and test_ic > 0.015 and drift_psi < 0.18:
            decision = "promote"
        elif stability_score < 70:
            decision = "repair"
        else:
            decision = "watch"

        rows.append(
            {
                "feature_id": feature_id,
                "feature_name": feature["feature_name"],
                "category": feature["category"],
                "vendor_family": feature["vendor_family"],
                "decision": decision,
                "promotion_score": promotion_score,
                "mean_ic": round(mean_ic, 4),
                "train_ic": round(train_ic, 4),
                "test_ic": round(test_ic, 4),
                "long_short_spread_bps": round(mean_spread * 10000, 1),
                "stationarity_psi": round(drift_psi, 3),
                "health_score": round(health_score, 1),
                "stability_score": round(stability_score, 1),
                "signal_score": round(signal_score, 1),
                "pit_failure_rate": pct(pit_failure_rate),
                "missing_rate": pct(missing_rate),
                "duplicate_rate": pct(duplicate_rate),
                "restatement_rate": pct(restatement_rate),
                "avg_latency_days": round(avg_latency, 2),
                "event_hours_at_risk": round(event_hours[feature_id], 1),
                "high_severity_events": critical_events[feature_id],
                "action_value": int(action_value[feature_id]),
            }
        )

        for bucket in range(10):
            bucket_rows = []
            for daily_rows in by_feature_date[feature_id].values():
                valid_daily = [row for row in daily_rows if row["feature_value"] != ""]
                ordered = sorted(valid_daily, key=lambda item: float(item["feature_value"]))
                size = max(1, len(ordered) // 10)
                bucket_rows.extend(ordered[bucket * size : (bucket + 1) * size])
            avg_return = sum(float(row["forward_5d_return"]) for row in bucket_rows) / max(1, len(bucket_rows))
            deciles.append(
                {
                    "feature_id": feature_id,
                    "decile": bucket + 1,
                    "avg_forward_5d_return_bps": round(avg_return * 10000, 1),
                    "row_count": len(bucket_rows),
                }
            )

        pit.append(
            {
                "feature_id": feature_id,
                "late_rows": pit_failures,
                "late_rate": pct(pit_failure_rate),
                "max_latency_days": max((date.fromisoformat(row["availability_date"]) - date.fromisoformat(row["as_of_date"])).days for row in rows_for_feature),
                "recommendation": "block from training joins" if pit_failures else "passes availability cutoff",
            }
        )
        stationarity.append(
            {
                "feature_id": feature_id,
                "stationarity_psi": round(drift_psi, 3),
                "train_ic": round(train_ic, 4),
                "test_ic": round(test_ic, 4),
                "degradation": round(train_ic - test_ic, 4),
                "status": "drift review" if drift_psi >= 0.18 or abs(train_ic - test_ic) > 0.06 else "stable",
            }
        )
        feed.append(
            {
                "feature_id": feature_id,
                "vendor_family": feature["vendor_family"],
                "health_score": round(health_score, 1),
                "avg_latency_days": round(avg_latency, 2),
                "missing_rate": pct(missing_rate),
                "duplicate_rate": pct(duplicate_rate),
                "restatement_rate": pct(restatement_rate),
                "high_severity_events": critical_events[feature_id],
            }
        )
        memos.append(
            {
                "feature_id": feature_id,
                "feature_name": feature["feature_name"],
                "decision": decision,
                "thesis": feature["thesis"],
                "evidence": f"Test IC {round(test_ic, 4)}, spread {round(mean_spread * 10000, 1)} bps, PSI {round(drift_psi, 3)}, health {round(health_score, 1)}.",
                "next_step": {
                    "promote": "Move into research review with guardrail monitoring.",
                    "watch": "Keep in candidate pool and require another out-of-sample window.",
                    "repair": "Fix stationarity or curation defect before promotion.",
                    "quarantine": "Exclude from training data until availability and feed defects clear.",
                }[decision],
            }
        )

    rows = sorted(rows, key=lambda item: item["promotion_score"], reverse=True)
    return rows, deciles, stationarity, pit, feed, memos


def write_analysis_docs(summary, top_rows):
    findings = [
        "# Executive Findings",
        "",
        "## What I analyzed",
        "",
        f"I generated a synthetic point-in-time research panel with {summary['panel_rows']:,} feature-security-date rows, {summary['feature_count']} candidate features, and {summary['event_count']} feed or research events.",
        "",
        "## Findings",
        "",
        f"- {summary['promote_count']} features clear the promotion threshold after signal, stationarity, point-in-time, and feed-health checks.",
        f"- {summary['quarantine_count']} features are quarantined because availability timing or data-health defects could create false alpha.",
        f"- The top candidate is {top_rows[0]['feature_name']} with a promotion score of {top_rows[0]['promotion_score']} and test IC of {top_rows[0]['test_ic']}.",
        f"- The highest data-risk item has {max(top_rows, key=lambda row: float(row['pit_failure_rate']))['pit_failure_rate']} percent point-in-time failure rate.",
        "",
        "## Recommendation",
        "",
        "Use the validation queue as a research gate. Promote only features that survive out-of-sample testing and availability checks, repair features with drift or feed defects, and quarantine features that would leak future information into training data.",
        "",
    ]
    (ANALYSIS / "executive_findings.md").write_text("\n".join(findings))

    plan = [
        "# Analysis Plan",
        "",
        "1. Generate a synthetic security-date panel with observation dates, availability dates, forward labels, and vendor-quality defects.",
        "2. Compute cross-sectional information coefficients and long-short decile spreads by feature.",
        "3. Compare train and test windows to identify signal decay.",
        "4. Run stationarity checks using population stability index between early and recent distributions.",
        "5. Enforce point-in-time correctness by comparing feature availability dates with label dates.",
        "6. Join feed events and action candidates into a research promotion queue.",
        "",
    ]
    (ANALYSIS / "analysis_plan.md").write_text("\n".join(plan))

    sql = """-- Point-in-time feature validation checks for a quantitative research workflow.

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
"""
    (ANALYSIS / "sql_checks.sql").write_text(sql)


def write_data_docs(summary):
    data_readme = [
        "# Data Notes",
        "",
        "All data in this repository is synthetic and portfolio-safe. It is generated by `scripts/score_operating_data.py` with a fixed random seed.",
        "",
        "The synthetic structure mirrors common financial feature-engineering tables: a feature catalog, a security master, a security-date feature panel, feed events, and action candidates.",
        "",
        "Injected defects include vendor latency, missingness, duplicate records, restatements, schema-style events, and point-in-time violations where a value becomes available after the forward label date.",
        "",
        f"The current generated panel contains {summary['panel_rows']:,} rows across {summary['feature_count']} features and {summary['security_count']} securities.",
        "",
    ]
    (DATA / "README.md").write_text("\n".join(data_readme))

    dictionary = [
        "# Data Dictionary",
        "",
        "| Path | Grain | Purpose |",
        "| --- | --- | --- |",
        "| `data/entities.csv` | Feature | Candidate feature catalog with vendor family, thesis, cadence, and assumed signal direction |",
        "| `data/security_master.csv` | Security | Synthetic equity universe metadata by sector, size, and liquidity |",
        "| `data/daily_metrics.csv` | Feature, security, date | Point-in-time panel with observation date, availability date, forward label, feature value, and feed-quality flags |",
        "| `data/source_events.csv` | Feed event | Synthetic vendor incidents and research questions used for root-cause triage |",
        "| `data/recommended_actions.csv` | Action | Candidate promote, watch, repair, quarantine, or retire actions |",
        "| `analysis/outputs/feature_validation_summary.csv` | Feature | Primary promotion queue with signal, stationarity, point-in-time, and health metrics |",
        "| `analysis/outputs/decile_spreads.csv` | Feature, decile | Cross-sectional return readout by feature decile |",
        "| `analysis/outputs/stationarity_tests.csv` | Feature | Train/test IC degradation and population stability index |",
        "| `analysis/outputs/point_in_time_checks.csv` | Feature | Availability cutoff violations and recommendations |",
        "| `analysis/outputs/feed_health.csv` | Feature | Vendor latency, missingness, duplicate, restatement, and incident metrics |",
        "| `analysis/outputs/research_memos.csv` | Feature | Interview-ready summary of thesis, evidence, and next action |",
        "| `analysis/outputs/summary.json` | Artifact | Top-level metrics consumed by the static app |",
        "",
    ]
    (ROOT / "data_dictionary.md").write_text("\n".join(dictionary))


def main():
    features, securities, panel, events, actions = generate_raw_data()
    summary_rows, deciles, stationarity, pit, feed, memos = aggregate_validations(features, panel, events, actions)
    write_csv(OUT / "feature_validation_summary.csv", summary_rows, list(summary_rows[0].keys()))
    write_csv(OUT / "priority_queue.csv", summary_rows, list(summary_rows[0].keys()))
    write_csv(OUT / "decile_spreads.csv", deciles, list(deciles[0].keys()))
    write_csv(OUT / "stationarity_tests.csv", stationarity, list(stationarity[0].keys()))
    write_csv(OUT / "point_in_time_checks.csv", pit, list(pit[0].keys()))
    write_csv(OUT / "feed_health.csv", feed, list(feed[0].keys()))
    write_csv(OUT / "research_memos.csv", memos, list(memos[0].keys()))
    decisions = defaultdict(int)
    for row in summary_rows:
        decisions[row["decision"]] += 1
    summary = {
        "feature_count": len(features),
        "security_count": len(securities),
        "panel_rows": len(panel),
        "event_count": len(events),
        "action_count": len(actions),
        "promote_count": decisions["promote"],
        "watch_count": decisions["watch"],
        "repair_count": decisions["repair"],
        "quarantine_count": decisions["quarantine"],
        "avg_health_score": round(sum(float(row["health_score"]) for row in summary_rows) / len(summary_rows), 1),
        "avg_test_ic": round(sum(float(row["test_ic"]) for row in summary_rows) / len(summary_rows), 4),
        "top_feature": summary_rows[0]["feature_name"],
        "top_score": summary_rows[0]["promotion_score"],
        "generated_with_seed": SEED,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    write_analysis_docs(summary, summary_rows)
    write_data_docs(summary)
    print(f"Generated {summary['panel_rows']:,} point-in-time rows across {summary['feature_count']} features.")
    print(f"Promotion queue: {summary['promote_count']} promote, {summary['watch_count']} watch, {summary['repair_count']} repair, {summary['quarantine_count']} quarantine.")
    for row in summary_rows[:8]:
        print(
            f"{row['feature_id']}: decision={row['decision']}, score={row['promotion_score']}, test_ic={row['test_ic']}, pit_fail={row['pit_failure_rate']}%"
        )


if __name__ == "__main__":
    main()
