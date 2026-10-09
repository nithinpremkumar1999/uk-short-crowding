- 2026-09-25 | named_archive.xlsx | https://www.fca.org.uk/publication/data/short-positions-daily-update.xlsx | sha256:d8759660c786
- 2026-09-25 | ansp.xlsx | https://www.fca.org.uk/publication/documents/aggregated-net-short-positions.xlsx | sha256:471b71e87e90
- 2026-09-25 | rsl.xlsx | https://www.fca.org.uk/publication/documents/uk-reportable-shares-list.xlsx | sha256:cccc352095ee
- 2026-09-27 | cleaned and processed named_archive.xlsx                   | replaced the ISIN with unique latest ISIN values                   | removed suffix from position holder and name of issuer fields                   | net short position is converted into decimal values
- 2026-09-27 | panel data is formed by taking the grouping position holder and ISIN on their month end
- 2026-09-27 | candidate data is formed by filtering on panel data that has minimum 0.5% position
- 2026-09-27 | positions are differentiated into active, probably closed, and definitely closed                    | if last notification from position holder is more than 12 months then it is probably inactive                     | if last notification from ISIN is less than 6 months then it is active                     | manually checked remaining uncertain status to confirm it was active
- 2026-09-27 | panel data is differentiated into two                    | only filtering out definitely closed positions | filtering both definitely and probably closed positions
- 2026-09-27 | aggregate view is formed by taking the aggregate of both panel data based on ISIN and month end 
- 2026-09-30 | Aggregate crowding data for (base/strict) is formed |                  where s: each holder's share of stock of the total short interest (s=position/total) |                  HHI = sum of s^2 | Effective number of holders (n_eff = 1/HHI) |                  agg_short is the total short interest on a ISIN-month_end combination |                  n_holders is the total number of holders on a ISIN-month_end combination |                  overlap_deg counts how many other ISIN-month_end share atleast two of its holders

### /data/processed/network_monthly_base.parquet
- Produced by: /src/network.py | commit 50bd5ab | run 2026-10-09
- Inputs: /data/panel_base.parquet
- Config: min_shared_holders=2, n_seed=50, core_cut=0.2, core_min_size=3, hub_coverage=0.5, core_link_jaccard=0.5
- Rows: 164 | months: 2012-11 to 2026-06
- Nulls: {'largest_core_density': 1, 'largest_core_coassign': 1, 'share_cores_hub_led': 1}

### /data/processed/core_base.parquet
- Produced by: /src/network.py | commit 50bd5ab | run 2026-10-09
- Inputs: /data/panel_base.parquet
- Config: min_shared_holders=2, n_seed=50, core_cut=0.2, core_min_size=3, hub_coverage=0.5, core_link_jaccard=0.5
- Rows: 26482 | months: 2012-11 to 2026-06
- Nulls: {'core_density': 19390, 'core_coassign': 19390, 'core_assign': 26482}

### /data/processed/core_summary_base.parquet
- Produced by: /src/network.py | commit 50bd5ab | run 2026-10-09
- Inputs: /data/panel_base.parquet
- Config: min_shared_holders=2, n_seed=50, core_cut=0.2, core_min_size=3, hub_coverage=0.5, core_link_jaccard=0.5
- Rows: 991 | months: 2012-11 to 2026-06
- Nulls: none

### /data/processed/fund_base.parquet
- Produced by: /src/network.py | commit 50bd5ab | run 2026-10-09
- Inputs: /data/panel_base.parquet
- Config: min_shared_holders=2, n_seed=50, core_cut=0.2, core_min_size=3, hub_coverage=0.5, core_link_jaccard=0.5
- Rows: 16310 | months: 2012-11 to 2026-06
- Nulls: none

### /data/processed/network_monthly_strict.parquet
- Produced by: /src/network.py | commit 50bd5ab | run 2026-10-09
- Inputs: /data/panel_strict.parquet
- Config: min_shared_holders=2, n_seed=50, core_cut=0.2, core_min_size=3, hub_coverage=0.5, core_link_jaccard=0.5
- Rows: 164 | months: 2012-11 to 2026-06
- Nulls: {'largest_core_density': 1, 'largest_core_coassign': 1, 'share_cores_hub_led': 1}

### /data/processed/core_strict.parquet
- Produced by: /src/network.py | commit 50bd5ab | run 2026-10-09
- Inputs: /data/panel_strict.parquet
- Config: min_shared_holders=2, n_seed=50, core_cut=0.2, core_min_size=3, hub_coverage=0.5, core_link_jaccard=0.5
- Rows: 26331 | months: 2012-11 to 2026-06
- Nulls: {'core_density': 19239, 'core_coassign': 19239, 'core_assign': 26331}

### /data/processed/core_summary_strict.parquet
- Produced by: /src/network.py | commit 50bd5ab | run 2026-10-09
- Inputs: /data/panel_strict.parquet
- Config: min_shared_holders=2, n_seed=50, core_cut=0.2, core_min_size=3, hub_coverage=0.5, core_link_jaccard=0.5
- Rows: 991 | months: 2012-11 to 2026-06
- Nulls: none

### /data/processed/fund_strict.parquet
- Produced by: /src/network.py | commit 50bd5ab | run 2026-10-09
- Inputs: /data/panel_strict.parquet
- Config: min_shared_holders=2, n_seed=50, core_cut=0.2, core_min_size=3, hub_coverage=0.5, core_link_jaccard=0.5
- Rows: 15932 | months: 2012-11 to 2026-06
- Nulls: none
