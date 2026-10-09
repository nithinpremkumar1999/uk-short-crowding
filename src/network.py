"""
Building monthly network data from data/processed/agg_{variant}.parquet
"""
import os
import yaml
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import datetime
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
from itertools import chain


FOLDER = "data/processed"
with open("config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)
VARIANTS = CONFIG["panel_variants"]


def build_network(m, k):
    """Build network graph for monthly panel data."""
    B = nx.Graph()
    B.add_nodes_from(m.pos_holder.unique(), bipartite=0)
    B.add_nodes_from(m.ISIN.unique(), bipartite=1)
    B.add_edges_from(m[["pos_holder", "ISIN"]].itertuples(index=False))
    S = nx.bipartite.weighted_projected_graph(B, m.ISIN.unique())
    S2 = nx.Graph()
    S2.add_weighted_edges_from((u, v, d["weight"]) for u, v, d in S.edges(data=True)\
                               if d["weight"]>=k)

    return B, S, S2


def core_stats(c, co, idx, S2, m):
    """Tightness and hub measures of one core."""
    ids = [idx[n] for n in c]
    sub = co[np.ix_(ids, ids)]
    mc = m[m.ISIN.isin(c)]
    per_fund = mc.groupby("pos_holder").ISIN.nunique().sort_values(ascending=True)
    w = [S2[u][v]["weight"] for u, v in S2.subgraph(c).edges()]

    return {
        "size": len(c),\
        "coassign": sub[np.triu_indices(len(ids), 1)].mean(),\
        "density": nx.density(S2.subgraph(c)),\
        "n_funds": mc.pos_holder.nunique(),\
        "top1_cov": per_fund.iloc[0]/len(c),\
        "top2_cov": per_fund.iloc[1]/len(c) if len(per_fund)>1 else 0.0,\
        "median_shared": np.median(w) if w else np.nan,
    }


def build_network_row(month, m, S2, w, runs, cores, stats, giant):
    """Helper function to build the network row."""
    n_stocks = m.ISIN.nunique()
    top = stats[0] if stats else {}
    network_row = {
        "month_end": month,\
        "n_stocks": m.ISIN.nunique(),\
        "n_funds": m.pos_holder.nunique(),\
        "n_positions": len(m),\
        "n_stocks_linked": S2.number_of_nodes(),\
        "giant_size": len(giant),\
        "giant_share": len(giant)/m.ISIN.nunique(),\
        "giant_density": nx.density(S2.subgraph(giant)),\
        "median_shared": np.median(w),\
        "max_shared": max(w),\
        "n_communities": len(runs[0]) if runs else 0,\
        "n_cores": len(cores),\
        "stocks_in_cores": sum(len(c) for c in cores),
        "share_in_cores": sum(len(c) for c in cores)/n_stocks,\
        "largest_core_size": top.get("size", 0),\
        "largest_core_density": top.get("density", np.nan),\
        "largest_core_coassign": top.get("coassign", np.nan),\
        "share_cores_hub_led": (np.mean([s["top1_cov"]>=CONFIG["hub_coverage"] for s in stats])
                                if stats else np.nan),
    }

    return network_row


def build_community_row(month, m, S2, comms, giant): #Depreciated function
    """Helper function to build community row."""
    community_row = []
    linked_row = [{
        "month_end": month,\
        "ISIN": s,\
        "community_id": i,\
        "community_size": len(c),\
        "community_density": nx.density(S2.subgraph(c)),\
        "in_giant": s in giant
    }
    for i, c in enumerate(comms)
    for s in c]
    community_row.extend(linked_row)
    unlinked = set(m.ISIN) - set(S2.nodes)
    unlinked_rows = [{
        "month_end": month,\
        "ISIN": s,\
        "community_id": -1,\
        "community_size": 1,\
        "community_density": np.nan,\
        "in_giant": False
    }
    for s in unlinked]
    community_row.extend(unlinked_rows)

    return community_row


def build_core_row(month, m, S2, cores, stats, giant):
    """Helper function to build core rows."""
    core_row = []
    linked_row = [{
        "month_end": month,\
        "ISIN": s,\
        "core_id": i,\
        "core_size": stat["size"],\
        "core_density": stat["density"],\
        "core_coassign": stat["coassign"],\
        "in_giant": s in giant
        }
        for i, (c, stat) in enumerate(zip(cores, stats))
        for s in c]
    core_row.extend(linked_row)
    unlinked = set(m.ISIN) - set(S2.nodes)
    unlinked_rows = [{
            "month_end": month,\
            "ISIN": s,\
            "core_id": -1,\
            "core_size": 1,\
            "core_density": np.nan,\
            "core_assign": np.nan,\
            "in_giant": False
        }
    for s in unlinked]
    core_row.extend(unlinked_rows)

    return core_row


def build_core_summary_row(month, stats):
    """Helper function to build core summary rows."""
    return [{
        "month_end": month, 
        "core_id": i,\
        "size": stat["size"],\
        "n_funds": stat["n_funds"],\
        "top1_cov": stat["top1_cov"],\
        "top2_cov": stat["top2_cov"],\
        "median_shared": stat["median_shared"],\
        "density": stat["density"],\
        "coassign": stat["coassign"],\
        "hub_led": stat["top1_cov"]>=CONFIG["hub_coverage"]
    } for i, stat in enumerate(stats)]


def build_fund_row(month, m, cores):
    """Helper function to build fund rows."""
    f = (m.groupby("pos_holder")\
            .agg(n_stocks=("ISIN", "nunique"), total_pct=("net_short_pos", "sum"))\
            .reset_index())
    core_of = {s: i for i, c in enumerate(cores) for s in c}
    mm = m.assign(core_id=m.ISIN.map(core_of)).dropna(subset=["core_id"])

    if len(mm):
        cov = mm.groupby(["pos_holder", "core_id"]).ISIN.nunique().reset_index(name="n_in_core")
        cov["cov"] = cov.n_in_core/cov.core_id.map(lambda i: len(cores[int(i)]))
        fc = cov.groupby("pos_holder").agg(
            n_cores_touched=("core_id", "nunique"),\
            max_core_cov=("cov", "max"),\
            n_hub_cores=("cov", lambda x: (x>=CONFIG["hub_coverage"]).sum())
        ).reset_index()
        f = f.merge(fc, on="pos_holder", how="left")

    f = f.reindex(columns=[*f.columns,\
                           *[c for c in ["n_cores_touched", "max_core_cov", "n_hub_cores"]\
                            if c not in f.columns]])
    f[["n_cores_touched", "max_core_cov", "n_hub_cores"]] =\
        (f[["n_cores_touched", "max_core_cov", "n_hub_cores"]].fillna(0))
    f["is_hub"] = f.n_hub_cores > 0
    f["month_end"] = month

    return f


def iterate_months(df):
    """Iterate through each month and get monthly network summary data."""
    p = df.copy()
    months = p.month_end.unique()
    network_rows, core_rows, core_summary_rows = [], [], []
    fund_df = pd.DataFrame(columns=["month_end", "pos_holder", "n_stocks", "total_pct",\
                                    "n_cores_touched", "max_core_cov", "n_hub_cores"])
    for month in months:
        m = p[p.month_end==month]
        B, S, S2 = build_network(m, CONFIG["min_shared_holders"])
        comps = sorted(nx.connected_components(S2), key=len, reverse=True)
        if len(comps) < 1:
            continue
        big = comps[0]
        sub = S2.subgraph(big)
        w = [S[u][v]["weight"] for u, v in sub.edges()]
        comms = sorted(nx.community.louvain_communities(S2, weight="weight", seed=CONFIG["louvain_seed"]),\
                       key=len, reverse=True)
        giant = max(nx.connected_components(S2), key=len)
        #----------------------------------------------------------------
        nodes = sorted(S2.nodes)
        runs = [nx.community.louvain_communities(S2, weight="weight", seed=s)
                for s in range(CONFIG["n_seed"])]
        idx = {n:i for i, n in enumerate(nodes)}
        co = np.zeros((len(nodes), len(nodes)))
        for r in runs:
            for c in r:
                ids = [idx[n] for n in c]
                co[np.ix_(ids, ids)] += 1
        co /= len(runs)
        D = 1-co
        np.fill_diagonal(D, 0)
        Z = linkage(squareform(D, checks=False), method="average")
        lab = fcluster(Z, t=0.2, criterion="distance")
        cores = [set(np.array(nodes)[lab==k]) for k in np.unique(lab)]
        cores = sorted([c for c in cores if len(c)>=CONFIG["core_min_size"]], key=len, reverse=True)
        stats = [core_stats(c, co, idx, S2, m) for c in cores]
        #----------------------------------------------------------------
        network_row = build_network_row(month, m, S2, w, runs, cores, stats, giant)
        network_rows.append(network_row)
        core_row = build_core_row(month, m, S2, cores, stats, giant)
        core_rows.append(core_row)
        core_summary_row = build_core_summary_row(month, stats)
        core_summary_rows.append(core_summary_row)
        fund_df = pd.concat([fund_df, build_fund_row(month, m, cores)], ignore_index=True)
        #----------------------------------------------------------------
        # community_row = build_community_row(month, m, S2, comms, giant)
        # community_rows.append(community_row)

    return pd.DataFrame(network_rows), pd.DataFrame(chain.from_iterable(core_rows)),\
    pd.DataFrame(chain.from_iterable(core_summary_rows)), fund_df


def assign_track_id(core_df):
    """Helper function to assign a tracker id for stocks."""
    members = (core_df[core_df.core_id>=0]\
               .groupby(["month_end", "core_id"]).ISIN.apply(frozenset))
    track, next_id = {}, 0
    prev, prev_track = {}, {}
    for month in sorted(members.index.get_level_values(0).unique()):
        cur = members.loc[month].to_dict()
        cands = sorted(((len(a&b)/len(a|b), cid, pid)\
                       for cid, a in cur.items() for pid, b in prev.items()),\
                       reverse=True)
        mapping, used_c, used_p = {}, set(), set()
        for j, cid, pid in cands:
            if j < CONFIG["core_link_jaccard"]:
                break
            if cid in used_c or pid in used_p:
                continue
            mapping[cid] = prev_track[pid]
            used_c.add(cid); used_p.add(pid)
        for cid in cur:
            if cid not in mapping:
                mapping[cid] = next_id; next_id+=1
            track[(month, cid)] = mapping[cid]
        prev, prev_track = cur, {cid: mapping[cid] for cid in cur}

    return track


def main():
    _dfs = {v: pd.read_parquet(os.path.join(FOLDER, f"panel_{v}.parquet")) for v in VARIANTS}
    panel_base_df = _dfs["base"]
    panel_strict_df = _dfs["strict"]
    # base variant
    network_monthly_base_df, core_base_df,\
         core_summary_base_df, fund_base_df = iterate_months(panel_base_df)
    track = assign_track_id(core_base_df)
    core_base_df["core_track_id"] = [track.get((m, c), -1) for m, c in zip(core_base_df.month_end, core_base_df.core_id)]
    core_summary_base_df["core_track_id"] = [track[m, c] for m, c in zip(core_summary_base_df.month_end, core_summary_base_df.core_id)]
    # strict variant
    network_monthly_strict_df, core_strict_df,\
         core_summary_strict_df, fund_strict_df = iterate_months(panel_strict_df)
    track = assign_track_id(core_strict_df)
    core_strict_df["core_track_id"] = [track.get((m, c), -1) for m, c in zip(core_strict_df.month_end, core_strict_df.core_id)]
    core_summary_strict_df["core_track_id"] = [track[m, c] for m, c in zip(core_summary_strict_df.month_end, core_summary_strict_df.core_id)]
    
    network_monthly_base_df.to_parquet(os.path.join(FOLDER, "network_monthly_base.parquet"), index=False)
    network_monthly_strict_df.to_parquet(os.path.join(FOLDER, "network_monthly_strict.parquet"), index=False)
    core_base_df.to_parquet(os.path.join(FOLDER, "core_base.parquet"), index=False)
    core_strict_df.to_parquet(os.path.join(FOLDER, "core_strict.parquet"), index=False)
    core_summary_base_df.to_parquet(os.path.join(FOLDER, "core_summary_base.parquet"), index=False)
    core_summary_strict_df.to_parquet(os.path.join(FOLDER, "core_summary_strict.parquet"), index=False)
    fund_base_df.to_parquet(os.path.join(FOLDER, "fund_base.parquet"), index=False)
    fund_strict_df.to_parquet(os.path.join(FOLDER, "fund_strict.parquet"), index=False)
    #--------------------------------------------------------------------------------------------------------
    # community_base_df.to_parquet(os.path.join(FOLDER, "community_base.parquet"), index=False)
    # community_strict_df.to_parquet(os.path.join(FOLDER, "community_strict.parquet"), index=False)

    # with open("DATA_LOG.md", "a") as log:
    #     log.write(f"- {datetime.date.today()} | Monthly network data for (base/strict) is formed |\
    #                 n_stocks: number of unique stocks | n_stocks_linked: stocks sharing >= 2 holders with atleast one other stock |\
    #                 n_positions: total number of positions | Effective number of holders (n_eff = 1/HHI) |\
    #                 giant_size: size of stocks in the biggest group | giant_share: largest group as a share of all shorted stocks |\
    #                 giant_density: how tightly linked the largest group is (0 to 1) | median_shared: typical number of shared holders on a link |\
    #                 max_shared: the most-shared pair of stocks | n_communities: number of tight groups found by Louvain |\
    #                 largest_comm_size: size of stocks in the largest community | largest_comm_density: density of stocks in the largest community\n")
    #     log.write(f"- {datetime.date.today()} | Month-ISIN community data for (base/strict) is formed |\
    #                 community_id: ID of tight group the ISIN belongs to in month_end (-1 by default) |\
    #                 community_size: size of stocks in that community_id (1 by default) |\
    #                 community_density: density of stocks in that community_id (Nan by default) |\
    #                 in_giant: Whether it's in the largest linked group (False by default)\n")


if __name__=="__main__":
    main()