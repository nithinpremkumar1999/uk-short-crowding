# FINDINGS

Status key: confirmed / provisional / pending / revised.
Every number must trace to a file named in its Evidence line.

---

### F1: The archive covers late 2012 to July 2026; open named positions fell 2018–21 and rose to around a series high by 2026
- Status: descriptive
- Evidence: panel_base.parquet; reports/figures/open_positions_by_age.png;
- Detail: the 2025–26 rise consists almost entirely of positions updated within 6 months, so it is not stale accumulation.
- Caveats: first months reflect the regime start and are excluded from time-series work. Explanations for 2018–21 (real decline / threshold avoidance / Jan 2021 regime switch) are hypotheses.
- Next test: holders vs positions-per-holder decomposition; bunching just below 0.5%.

### F2: The staleness decision does not drive results
- Status: confirmed once X is filled
- Evidence: stale_candidates.parquet; panel_base vs panel_strict;
- Detail: 663 never-closed positions: 563 active, 75 definite, 7 probable, 18 uncertain. Base and strict panels differ by [X] position-months.
- Caveats: dormancy threshold 12 months (sensitivity at 6/24: [results]).

### F3: In the latest month the short book forms a loose web, not one crowded trade
- Status: descriptive, one month
- Evidence: notebook 02 (unweighted S2): giant component 110 stocks / 74 funds, density 0.12. Pipeline (weighted): [giant_size, giant_share, giant_density from network_monthly_base latest row]
- Caveats: notebook figures used the unweighted graph; pipeline values supersede them.

### F4: Single-run Louvain partitions are unreliable on this data
- Status: confirmed (method finding)
- Evidence: notebook 02, 50 seeds: median ARI 0.50, min 0.23
- Caveats: computed on unweighted S2; rerun on weighted S2 pending.
- Consequence: stock-level analysis uses consensus cores (see METHODS).

### F5: Threshold-graph cores chained; average-linkage consensus cores fixed it
- Status: confirmed (method finding)
- Evidence: notebook 02. Before: mean co-assignment 0.77 / 0.88 / 0.70 / 0.82 / 0.81 (sizes 25/20/19/11/7). After: 0.90–0.97 (sizes 19/14/9/7/6).
- Caveats: unweighted S2; pipeline cores differ in membership.

### F6: Crowded groups are hub-and-satellite rather than multi-fund baskets
- Status: provisional
- Evidence: core_summary_base.parquet, latest month: top-fund coverage 0.70–1.00 across all cores (e.g. 16 of 21 stocks; 13 of 14). Pattern matches the notebook (unweighted) result, so it survives the switch to weighted graphs.
- Revision history:
  - [date] Sort-order bug in core_stats made top1_cov = 1/size, so hub_led was always False. Caught on comparison with notebook; fixed with nlargest; unit test added.
  - [date] After the fix, share_cores_hub_led ≈ 1.0 almost every month. With a 0.5 threshold and small cores, hub-led is close to automatic, so the binary measure was dropped in favour of continuous top1_cov.
- Next tests: top1_cov vs null p95 (null model); holder-type split; exclude top-2 funds; min_shared_holders = 3.

### F7: Interconnection of the short book is at a series high in 2026, although the number of shorted stocks is not
- Status: provisional
- Evidence: network_monthly_base.parquet: giant_share [~0.5], share_in_cores [~0.45] in 2026 vs [values] at the 2019 peak; n_stocks [~210] vs [~235] in 2019. (Values read from chart; replace with exact figures.)
- Caveats: open positions are at a series high on fewer stocks, so more positions per stock raises overlap by construction. largest_core_density is noise when cores are tiny (2021–22).
- Next test: null model, i.e. does the excess over a degree-preserving null rise in 2025–26?

### F8: Tracked core groups are short-lived (median 1 month)
- Status: pending (artefact vs real unresolved)
- Evidence: core_summary_base.parquet: 679 tracks; median life 1 month; 9.3% last ≥3 months; 0.15% ≥12; max 19.
- Caveats: clustering instability (F4), positions flickering around 0.5%, and strict tracking rules (Jaccard 0.5; gap month ends a track) all shorten measured life. Right/left censoring.
- Next test: compare life of individual positions and of stock pairs (≥2 shared holders) with life of cores; Jaccard 0.3 and one-month-gap sensitivity.

### F9: Persistent groups are usually anchored by the same fund, and a few funds anchor most of them
- Status: provisional
- Evidence: life table (notebook 03): modal_hub_share 0.80 (3–5 months), 0.83 (6–11), 0.79 (12+). Top 5 anchoring funds = 59.6% of anchored track-months. Leading anchor is a large diversified asset manager (75 track-months).
- Caveats: under group reporting, a diversified manager's breadth may reflect firm size and many separate strategies or hedges, not one concentrated bet. Single-anchor (52%) vs rotating-hub (48%) split is on hold: it depends on the dropped binary hub definition. Ties for top fund broken arbitrarily.
- Next test: tag top funds by holder type (data/manual/holder_type.csv); rerun excluding diversified managers.

### F10: Public aggregate short interest says a lot about holder count, less about overlap, and little about hub reach
- Status: confirmed (descriptive)
- Evidence: agg_base_crowding.parquet; monthly Spearman with agg_short, median (IQR):
  - n_holders 0.84 (0.80–0.86)
  - n_eff 0.81 (0.78–0.84)
  - overlap_deg 0.63 (0.56–0.70)
  - hub_exposure 0.27 (0.19–0.34)
  hub_exposure correlation falls to about zero in 2021 and 2023.
- Caveats: the n_holders correlation is partly mechanical (every named position ≥0.5%). hub_exposure may be driven by diversified managers (see F9).
- Next test: recompute hub_exposure excluding diversified managers.

### F11 (hypothesis): 2021 is a low-structure period
- Status: hypothesis
- Evidence: network_monthly_base: n_stocks at series low, giant_share near 0, 0–2 cores; hub_exposure correlation near 0.
- Possible explanations: fewer named shorts after early-2021 retail squeezes (threshold avoidance), market conditions, regime switch.
- Next test: bunching below 0.5% before and after Jan 2021.