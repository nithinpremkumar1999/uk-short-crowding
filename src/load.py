"""
Load and clean ../data/named_archive.xlsx containing short position information till 2026/07/10.
"""
import os
import pandas as pd
import numpy as np
import datetime


FOLDER = "data/raw"
NAMED_ARCHIVE_FILE = "named_archive.xlsx"
RSL_FILE = "rsl.xlsx"
DEST_FOLDER = "data/interim"
DEST_FILE = "notifications_clean.parquet"


def rename_dtype_clean(rsl_df, named_archive_df):
    """Rename and fix data types of the dataframes."""
    # rsl
    rsl_df.rename(columns={
    "Share ISIN":"ISIN",
    "Company name":"name",
    "Date added": "date",
    "Class of share (Main or Other Class of Shares)":"share_class"
    }, inplace=True)
    rsl_df["date"] = pd.to_datetime(rsl_df["date"], format="%Y-%m-%d")
    # named_archive
    named_archive_df.rename(columns={"Position Holder": "pos_holder",
                          "Name of Share Issuer": "name_share_issuer",
                          "Net Short Position (%)": "net_short_pos",
                          "Position Date": "pos_date"},
                inplace=True)
    named_archive_df["pos_date"] = pd.to_datetime(named_archive_df["pos_date"], format="%Y-%m-%d")
    named_archive_df["net_short_pos"] = named_archive_df["net_short_pos"]/100

    return rsl_df, named_archive_df


def normalise_col_values(named_archive_df):
    """Normalise and match column values in the datafrmae."""
    # name_share_issuer
    clean_issuer_holder = (
        named_archive_df["name_share_issuer"]
        .str.lower()
        .str.replace(r"[,.]", "", regex=True)
        .str.replace(r"\b(pvt|private|ltd|limited|ph|lp|llp|l.p.|pty|llc|llc|inc|plc|lllp|sa)\b", "", regex=True)
        .str.replace(r"[^\w]+", "_", regex=True)
        .str.strip("_")
        .str.replace(r"_+", "_", regex=True)
        )
    named_archive_df["name_share_issuer"] = clean_issuer_holder
    # pos_holder
    clean_pos_holder = (
    named_archive_df["pos_holder"]
        .str.lower()
        .str.replace(r"[,.]", "", regex=True)
        .str.replace(r"\b(pvt|private|ltd|limited|ph|lp|llp|europe|jersey|ii|pty|llc|llc|inc|plc|lllp|sa|uk|usa|gp|mt)\b", "", regex=True)
        .str.replace(r"[^\w]+", "_", regex=True)
        .str.strip("_")
        .str.replace(r"_+", "_", regex=True)
    )
    named_archive_df["pos_holder"] = clean_pos_holder
    # replace the ISIN with unique latest ISIN values
    issuer_isin = named_archive_df.groupby(["name_share_issuer"])["ISIN"].nunique()
    latest_isin = (
        named_archive_df.sort_values(by="pos_date")
        .drop_duplicates(subset=["name_share_issuer"], keep="last")
        .set_index("name_share_issuer")["ISIN"]
    )
    issuer_isin = issuer_isin[issuer_isin>1].index
    isin_mapping = latest_isin[latest_isin.index.isin(issuer_isin)]
    named_archive_df["ISIN"] = named_archive_df["name_share_issuer"].map(isin_mapping).fillna(named_archive_df["ISIN"])

    return named_archive_df


def main():
    named_archive = pd.read_excel(os.path.join(FOLDER, NAMED_ARCHIVE_FILE),\
                                  sheet_name="Historic Disclosures 10.07.2026")
    rsl = pd.read_excel(os.path.join(FOLDER, RSL_FILE),\
                        sheet_name="Reportable Shares List")
    rsl, named_archive = rename_dtype_clean(rsl_df=rsl, named_archive_df=named_archive)
    named_archive = normalise_col_values(named_archive_df=named_archive)
    named_archive.to_parquet(os.path.join(DEST_FOLDER, DEST_FILE), index=False)
    with open("DATA_LOG.md", "a") as log:
        log.write(f"- {datetime.date.today()} | cleaned and processed named_archive.xlsx \
                  | replaced the ISIN with unique latest ISIN values \
                  | removed suffix from position holder and name of issuer fields \
                  | net short position is converted into decimal values\n")



if __name__=="__main__":
    main()