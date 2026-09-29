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


def build_network_row(month, m, S2, w, comms, giant):
    """Helper function to build the network row."""
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
        "n_communities": len(comms),\
        "largest_comm_size": len(comms[0]),\
        "largest_comm_density": nx.density(S2.subgraph(comms[0]))
    }

    return network_row


def build_community_row(month, m, S2, comms, giant):
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


def iterate_months(df):
    """Iterate through each month and get monthly network summary data."""
    p = df.copy()
    months = p.month_end.unique()
    network_rows, community_rows = [], []
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
        network_row = build_network_row(month, m, S2, w, comms, giant)
        network_rows.append(network_row)
        community_row = build_community_row(month, m, S2, comms, giant)
        community_rows.append(community_row)

    return pd.DataFrame(network_rows), pd.DataFrame(community_rows) 


def main():
    _dfs = {v: pd.read_parquet(os.path.join(FOLDER, f"panel_{v}.parquet")) for v in VARIANTS}
    panel_base_df = _dfs["base"]
    panel_strict_df = _dfs["strict"]

    network_monthly_base_df, community_base_df = iterate_months(panel_base_df)
    network_monthly_strict_df, community_strict_df = iterate_months(panel_strict_df)

    network_monthly_base_df.to_parquet(os.path.join(FOLDER, "network_monthly_base.parquet"), index=False)
    network_monthly_strict_df.to_parquet(os.path.join(FOLDER, "network_monthly_strict_df.parquet"), index=False)
    community_base_df.to_parquet(os.path.join(FOLDER, "community_base.parquet"), index=False)
    community_strict_df.to_parquet(os.path.join(FOLDER, "community_strict.parquet"), index=False)

    with open("DATA_LOG.md", "a") as log:
        log.write(f"- {datetime.date.today()} | Monthly network data for (base/strict) is formed |\
                    n_stocks: number of unique stocks | n_stocks_linked: stocks sharing >= 2 holders with atleast one other stock |\
                    n_positions: total number of positions | Effective number of holders (n_eff = 1/HHI) |\
                    giant_size: size of stocks in the biggest group | giant_share: largest group as a share of all shorted stocks |\
                    giant_density: how tightly linked the largest group is (0 to 1) | median_shared: typical number of shared holders on a link |\
                    max_shared: the most-shared pair of stocks | n_communities: number of tight groups found by Louvain |\
                    largest_comm_size: size of stocks in the largest community | largest_comm_density: density of stocks in the largest community\n")
        log.write(f"- {datetime.date.today()} | Month-ISIN community data for (base/strict) is formed |\
                    community_id: ID of tight group the ISIN belongs to in month_end (-1 by default) |\
                    community_size: size of stocks in that community_id (1 by default) |\
                    community_density: density of stocks in that community_id (Nan by default) |\
                    in_giant: Whether it's in the largest linked group (False by default)\n")


if __name__=="__main__":
    main()