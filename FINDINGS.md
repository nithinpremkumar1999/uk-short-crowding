### F[1]: Coverage and shape of the archive
- Status: Confirmed
- Description: Open positions declined from 2018 to a 2021 low, then rose around 2026, and is
likely due to recently opened positions.
- Evidence: Open position by age figures in reports/figures

### F[2]: Staleness doesn't drive results
- Status: Confirmed
- Description: 663 never-closed positions: 563 active, 75 definite, 7 probable, 18 uncertain.
Base and strict panels differ by 378 position_holder-months.
- Evidence: notebooks/panel_data_analysis.ipynb

### F[3]: Latest month's network is a loose web
- Status: Confirmed
- Description: Giant component of 110 stocks and 74 funds, density 0.12, maximum stocks held by
a fund is 7.
- Evidence: notebooks/panel_data_analysis.ipynb

### F[4]: Single-run community detection is unreliable here
- Status: Confirmed
- Description: Median ARI 0.50, minimum 0.23 across 50 seeds.
- Evidence: notebooks/panel_data_analysis.ipynb

### F[5]: Threshold cores chained; average linkage fixed it
- Status: Confirmed
- Description: Include the before-and-after tables: mean co-assignment 0.70–0.88 before, 0.90–0.97 after.
- Evidence: notebooks/panel_data_analysis.ipynb

### F[6]: Crowded groups are hub-and-satellite, not multi-fund baskets
- Status: Confirmed
- Description: Median shared holders is 2 in every group; one or two funds cover most of each group’s stocks.
- Evidence: notebooks/panel_data_analysis.ipynb