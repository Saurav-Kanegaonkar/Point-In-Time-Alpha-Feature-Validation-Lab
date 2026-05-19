# Data Dictionary

| Path | Grain | Purpose |
| --- | --- | --- |
| `data/entities.csv` | Feature | Candidate feature catalog with vendor family, thesis, cadence, and assumed signal direction |
| `data/security_master.csv` | Security | Synthetic equity universe metadata by sector, size, and liquidity |
| `data/daily_metrics.csv` | Feature, security, date | Point-in-time panel with observation date, availability date, forward label, feature value, and feed-quality flags |
| `data/source_events.csv` | Feed event | Synthetic vendor incidents and research questions used for root-cause triage |
| `data/recommended_actions.csv` | Action | Candidate promote, watch, repair, quarantine, or retire actions |
| `analysis/outputs/feature_validation_summary.csv` | Feature | Primary promotion queue with signal, stationarity, point-in-time, and health metrics |
| `analysis/outputs/decile_spreads.csv` | Feature, decile | Cross-sectional return readout by feature decile |
| `analysis/outputs/stationarity_tests.csv` | Feature | Train/test IC degradation and population stability index |
| `analysis/outputs/point_in_time_checks.csv` | Feature | Availability cutoff violations and recommendations |
| `analysis/outputs/feed_health.csv` | Feature | Vendor latency, missingness, duplicate, restatement, and incident metrics |
| `analysis/outputs/research_memos.csv` | Feature | Interview-ready summary of thesis, evidence, and next action |
| `analysis/outputs/summary.json` | Artifact | Top-level metrics consumed by the static app |
