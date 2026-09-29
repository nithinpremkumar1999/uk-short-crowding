"""
Building panel data from ../data/interim/notifications_clean.parquet.
"""
import os
import pandas as pd
import numpy as np
import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.dates as mdates


FOLDER = "data/interim"
NOTIFICATION_CLEAN_FILE = "notifications_clean.parquet"
PROCESSED_FOLDER = "data/processed"
INTERIM_FOLDER = "data/interim"


def build_panel_data(notifications_clean):
    """Build panel data from notifications clean."""
    # build panel data, showcasing position holder's position in ISIN at month end
    df = notifications_clean.sort_values(["pos_holder", "ISIN", "pos_date"]).copy()
    df = df.drop_duplicates(["pos_holder", "ISIN", "pos_date"], keep="last")

    month_ends = pd.date_range(df.pos_date.min(), "2026-07-10", freq="ME")
    snaps = []
    for d in month_ends:
        last = df[df.pos_date<=d].groupby(["pos_holder", "ISIN"]).tail(1)
        snaps.append(last[last.net_short_pos>=0.005].assign(month_end=d))
    panel_df = pd.concat(snaps, ignore_index=True)

    return panel_df


def build_candidates(notifications_clean):
    """Build candidates dataframe to filter."""
    end = notifications_clean.pos_date.max()
    last = notifications_clean.sort_values("pos_date").groupby(["pos_holder", "ISIN"]).tail(1)
    cand = last[last.net_short_pos>=0.005]

    cand["holder_last"] = cand.pos_holder.map(notifications_clean.groupby("pos_holder").pos_date.max())
    cand["ISIN_last"] = cand.ISIN.map(notifications_clean.groupby("ISIN").pos_date.max())
    for c in ["pos_date", "holder_last", "ISIN_last"]:
        cand[f"m_{c}"] = (end - cand[c]).dt.days / 30.4

    return cand


def differentiate_status(panel_df, cand_df):
    """Differentiate panel data into active, probable, definite."""
    gone = pd.read_csv("data/manual/dilisted_manual.csv", parse_dates=["gone_date"])
    cand = cand_df.merge(gone[["ISIN", "gone_date"]], on="ISIN", how="left")
    cand["status"] = np.select(
        [cand.gone_date.notna(), cand.m_holder_last>12], # if last notification from position holder is more than 12 months then it is probably inactive
        ["definite", "probable"],
        default="uncertain"
    )
    cand.loc[(cand.status == "uncertain") & (cand.m_pos_date <= 6), "status"] = "active" # if last notification from ISIN is less than 6 months then it is active
    cand.loc[(cand.status == "uncertain"), "status"] = "active" # manually checked remaining uncertain status to confirm it was active

    cand["close_base"] = cand.gone_date # close only definite
    cand["close_strict"] = cand.gone_date.fillna(cand.holder_last.where(cand.status=="probable")) # close probable too

    def apply_close(df, cand, col):
        p = df.merge(cand[["ISIN", "pos_holder", col]], on=["ISIN", "pos_holder"], how="left")
        keep = p[col].isna() | (p.month_end <= p[col]+pd.offsets.MonthEnd(0))
        return p[keep].drop(columns=col)

    panel_base = apply_close(panel_df, cand, "close_base")
    panel_strict = apply_close(panel_df, cand, "close_strict")

    return panel_base, panel_strict


def build_agg_view(panel_base, panel_strict):
    """Build short position view that is now available for public viewers."""
    # aggregate on ISIN, month_end to get sum of short positions and number of unique position holders.
    agg_base = panel_base.groupby(["ISIN", "month_end"]).agg(
        agg_short=("net_short_pos", "sum"),
        n_holders=("pos_holder", "nunique")
    ).reset_index()
    agg_strict = panel_strict.groupby(["ISIN", "month_end"]).agg(
        agg_short=("net_short_pos", "sum"),
        n_holders=("pos_holder", "nunique")
    ).reset_index()

    return agg_base, agg_strict


def plot_active_pos(panel_df, type="base"):
    """Using seaborn to plot panel (base/strict) data on the bases of last notification."""
    p = panel_df.copy()
    p["age_m"] = (p.month_end - p.pos_date).dt.days / 30.4
    p["age"] = pd.cut(p.age_m, [-1, 6, 12, 24, 1e9], labels=["<6m", "6–12m", "12–24m", ">24m"])
    p["month_end"] = pd.to_datetime(p["month_end"])

    data = (
        p.groupby(["month_end", "age"], observed=True)
        .size()
        .unstack(fill_value=0)
        .sort_index()
    )

    # 2. Seaborn aesthetic configuration
    sns.set_theme(style="whitegrid", font="sans-serif")
    fig, ax = plt.subplots(figsize=(11, 5.5), dpi=300)

    # Professional sequential palette matching the ordinal age buckets
    palette = sns.color_palette("ch:s=-.2,r=.6", n_colors=data.shape[1])

    # 3. Stacked area plot
    ax.stackplot(
        data.index,
        data.values.T,
        labels=data.columns,
        colors=palette,
        alpha=0.9,
        edgecolor="white",
        linewidth=0.5,
    )

    # 4. Refined styling & labels
    ax.set_title(
        "Open Net Short Positions by Duration / Age Bucket",
        fontsize=13,
        fontweight="bold",
        pad=15,
        loc="left",
    )
    ax.set_xlabel("Snapshot Date (Month End)", fontsize=10, labelpad=8)
    ax.set_ylabel("Number of Open Positions", fontsize=10, labelpad=8)

    # Format X-axis for clean timeline intervals
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax.tick_params(axis="both", which="major", labelsize=9)

    # Format Y-axis with commas (e.g., 1,000)
    ax.yaxis.set_major_formatter("{x:,.0f}")

    # Tight boundaries and spine clean-up
    ax.set_xlim(data.index.min(), data.index.max())
    ax.margins(y=0.05)
    sns.despine(left=True, bottom=False)

    # Place legend outside the main plotting area
    ax.legend(
        title="Position Age",
        title_fontsize="10",
        fontsize=9,
        frameon=True,
        facecolor="white",
        edgecolor="#e0e0e0",
        loc="upper left",
        bbox_to_anchor=(1.02, 1),
    )

    out_dir = "reports/figures"
    fig.savefig(os.path.join(out_dir, f"open_pos_by_age_{type}.png"), bbox_inches="tight", dpi=300)
    plt.close(fig)
    

def main():
    notifications_clean = pd.read_parquet(os.path.join(FOLDER, NOTIFICATION_CLEAN_FILE))
    panel_df = build_panel_data(notifications_clean=notifications_clean)
    cand_df = build_candidates(notifications_clean=notifications_clean)
    panel_base_df, panel_strict_df = differentiate_status(panel_df=panel_df, cand_df=cand_df)
    agg_base_df, agg_strict_df = build_agg_view(panel_base=panel_base_df, panel_strict=panel_strict_df)
    cand_df.to_parquet(os.path.join(INTERIM_FOLDER, "stale_candidates.parquet"), index=False)
    panel_base_df.to_parquet(os.path.join(PROCESSED_FOLDER, "panel_base.parquet"), index=False)
    panel_strict_df.to_parquet(os.path.join(PROCESSED_FOLDER, "panel_strict.parquet"), index=False)
    agg_base_df.to_parquet(os.path.join(PROCESSED_FOLDER, "agg_base.parquet"), index=False)
    agg_strict_df.to_parquet(os.path.join(PROCESSED_FOLDER, "agg_strict.parquet"), index=False)
    plot_active_pos(panel_base_df, type="base")
    plot_active_pos(panel_strict_df, type="strict")
    with open("DATA_LOG.md", "a") as log:
        log.write(f"- {datetime.date.today()} | panel data is formed by taking the grouping position holder and ISIN on their month end\n")
        log.write(f"- {datetime.date.today()} | candidate data is formed by filtering on panel data that has minimum 0.5% position\n")
        log.write(f"- {datetime.date.today()} | positions are differentiated into active, probably closed, and definitely closed\
                    | if last notification from position holder is more than 12 months then it is probably inactive \
                    | if last notification from ISIN is less than 6 months then it is active \
                    | manually checked remaining uncertain status to confirm it was active\n")
        log.write(f"- {datetime.date.today()} | panel data is differentiated into two\
                    | only filtering out definitely closed positions | filtering both definitely and probably closed positions\n")
        log.write(f"- {datetime.date.today()} | aggregate view is formed by taking the aggregate of both panel data based on ISIN and month end \n")


if __name__=="__main__":
    main()