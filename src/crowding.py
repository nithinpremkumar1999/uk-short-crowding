"""
Building aggregate data from data/processed/agg_{variant}.parquet
"""
import os
import pandas as pd
import numpy as np
import yaml
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns


FOLDER = "data/processed"
with open("config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)
VARIANTS = CONFIG["panel_variants"]


def build_aggregate(df):
    """Build aggregate data from panel dataframe."""
    p = df.copy()
    p["tot"] = p.groupby(["ISIN", "month_end"]).net_short_pos.transform("sum")
    p["s2"] = (p.net_short_pos/p.tot)**2

    agg = p.groupby(["ISIN", "month_end"]).agg(
        agg_short=("net_short_pos", "sum"),
        n_holders=("pos_holder", "nunique"),
        hhi=("s2", "sum")
        ).reset_index()
    agg["n_eff"] = 1/agg["hhi"]

    cols = ["pos_holder", "ISIN", "month_end"]
    pairs = p[cols].merge(p[cols], on=["pos_holder", "month_end"])
    pairs = pairs[pairs.ISIN_x!=pairs.ISIN_y]
    shared = pairs.groupby(["ISIN_x", "ISIN_y", "month_end"]).size().reset_index(name="n_shared")
    ov = (shared[shared.n_shared>=CONFIG["min_shared_holders"]].groupby(["ISIN_x", "month_end"]).size()\
          .reset_index(name="overlap_deg").rename(columns={"ISIN_x":"ISIN"}))
    agg = agg.merge(ov, on=["month_end", "ISIN"], how="left").fillna({"overlap_deg": 0})

    return agg


def plot_correlation(df, type="base"):
    """Spearman correlation of number of holder, effective holders, overlap degree."""
    # Ensure month_end is datetime
    df = df.copy()
    df["month_end"] = pd.to_datetime(df["month_end"])

    rho = df.groupby("month_end").apply(
        lambda g: g[["agg_short", "n_holders", "n_eff", "overlap_deg"]]
        .corr("spearman")
        .loc["agg_short"],
        include_groups=False,
    )
    rho_clean = rho.drop(columns=["agg_short"])

    rho_long = rho_clean.reset_index().melt(
        id_vars="month_end", var_name="metric", value_name="spearman_rho"
    )
    metric_labels = {
        "n_holders": "Number of Holders",
        "n_eff": "Effective Holders (N_eff)",
        "overlap_deg": "Overlap Degree",
    }
    rho_long["metric"] = rho_long["metric"].replace(metric_labels)

    sns.set_theme(style="whitegrid", font="sans-serif")
    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=300)

    palette = sns.color_palette("tab10", n_colors=rho_long["metric"].nunique())

    # style="metric" uses solid, dashed, and dotted lines so overlapping curves show through
    sns.lineplot(
        data=rho_long,
        x="month_end",
        y="spearman_rho",
        hue="metric",
        palette=palette,
        linewidth=2.0,
        alpha=0.85,
        ax=ax,
    )

    ax.axhline(0, color="grey", linestyle="--", linewidth=0.8, alpha=0.7)

    ax.set_title(
        f"Spearman Correlation with Aggregate Short Position ({type.capitalize()})",
        fontsize=12,
        fontweight="bold",
        pad=12,
        loc="left",
    )
    ax.set_xlabel("Snapshot Date", fontsize=10, labelpad=8)
    ax.set_ylabel("Spearman Rank Correlation (ρ)", fontsize=10, labelpad=8)
    ax.set_ylim(-1.05, 1.05)

    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))

    sns.despine(left=True, bottom=False)

    ax.legend(
        title="",
        frameon=True,
        facecolor="white",
        edgecolor="none",
        loc="upper left",
        bbox_to_anchor=(1.02, 1),
    )

    out_dir = "reports/figures"
    os.makedirs(out_dir, exist_ok=True)
    fig.savefig(
        os.path.join(out_dir, f"correlation_over_time_{type}.png"),
        bbox_inches="tight",
        dpi=300,
    )
    plt.close(fig)


def main():
    _dfs = {v: pd.read_parquet(os.path.join(FOLDER, f"panel_{v}.parquet")) for v in VARIANTS}
    panel_base_df = _dfs["base"]
    panel_strict_df = _dfs["strict"]

    agg_base_df = build_aggregate(panel_base_df)
    agg_strict_df = build_aggregate(panel_strict_df)

    agg_base_df.to_parquet(os.path.join(FOLDER, "agg_base_crowding.parquet"), index=False)
    agg_strict_df.to_parquet(os.path.join(FOLDER, "agg_strict_crowding.parquet"), index=False)

    plot_correlation(agg_base_df, type="base")
    plot_correlation(agg_strict_df, type="strict")

    with open("DATA_LOG.md", "a") as log:
        log.write(f"- {datetime.date.today()} | Aggregate crowding data for (base/strict) is formed |\
                  where s: each holder's share of stock of the total short interest (s=position/total) |\
                  HHI = sum of s^2 | Effective number of holders (n_eff = 1/HHI) |\
                  agg_short is the total short interest on a ISIN-month_end combination |\
                  n_holders is the total number of holders on a ISIN-month_end combination |\
                  overlap_deg counts how many other ISIN-month_end share atleast two of its holders\n")
    

if __name__=="__main__":
    main()