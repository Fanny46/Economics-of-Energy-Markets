import os
import pandas as pd
from pathlib import Path
import numpy as np
import glob


# ── Load prices, flows and capacities ──────────────────────────────────────────────────

zone_map = {
        "FR": "France",
        "BE": "Belgium",
        "CH": "Switzerland",
        "DE-LU": "Germany",
        "DE-AT-LU": "Germany",
        "DE(TransnetBW)": "Germany",
        "DE(Amprion)": "Germany",
        "ES": "Spain",
        "GB": "Great Britain",
        "GB(ElecLink)": "Great Britain",
        "GB(IFA)": "Great Britain",
        "GB(IFA2)": "Great Britain",
        "IT-North": "Italy-North",
        "IT-North-FR": "Italy-North",
        "IT": "Italy-North",
        "LU": "Germany",
}

def load_prices(price_folder, years=[2021, 2022, 2023, 2024]):
    years = [str(y) for y in years]
    files = Path(price_folder).glob("Energy prices *.csv")
    prices_list = []

    for f in files:
        if not any(year in f.name for year in years):
            continue

        country = (
            f.name.replace("Energy prices ", "")
                  .replace(".csv", "").split(" ")[0]
        )

        df = pd.read_csv(f)
        print("Lecture :", f.name)

        if "Sequence" in df.columns:
            df = df[df["Sequence"].isin(
                ["Without Sequence", "Sequence 1"]
            )]

        df["datetime"] = pd.to_datetime(
            df["MTU (CET/CEST)"].str[:19],
            format="%d/%m/%Y %H:%M:%S"
        )

        df = df.rename(columns={
            "Day-ahead Price (EUR/MWh)": "price"
        })[["datetime", "price"]]

        df["country"] = country

        # Allemagne quart d'heure → horaire
        df["datetime"] = df["datetime"].dt.floor("H")

        df = (
            df.groupby(["country", "datetime"], as_index=False)
            .agg(price=("price", "mean"))
        )

        prices_list.append(df)

    return pd.concat(prices_list, ignore_index=True)


def load_entsoe_folder(folder_path, value_type="flow", years=[2021, 2022, 2023, 2024]):
    """
    value_type : "flow" ou "capacity"
    """
    all_df = []
    years = [str(y) for y in years]

    for fname in os.listdir(folder_path):
        if not fname.endswith(".csv") or not any(year in fname for year in years) :
            continue

        print("Lecture :", fname)
        path = os.path.join(folder_path, fname)
        df = pd.read_csv(path)

        # 1. détecter MTU
        if "MTU" in df.columns:
            mtu_col = "MTU"
        elif "MTU (CET/CEST)" in df.columns:
            mtu_col = "MTU (CET/CEST)"
        else:
            print("MTU introuvable :", fname)
            continue

        df["datetime"] = pd.to_datetime(
            df[mtu_col]
                .astype(str)
                .str.split(" - ").str[0]
                .str.replace(r"\s*\(.*\)", "", regex=True),
            dayfirst=True,
            errors="coerce"
        )

        # 2. colonne valeur
        if value_type == "flow":
            value_col = "Physical Flow (MW)"
            col_name = "flow_mw"
        elif value_type == "capacity":
            value_col = "Capacity (MW)"
            col_name = "capacity_mw"
        else:
            raise ValueError("value_type invalide")

        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")

        # 3. nettoyage zones
        df["from_country"] = df["Out Area"].str.split("|", n=1, regex=False).str[1].map(zone_map)
        df["to_country"] = df["In Area"].str.split("|", n=1, regex=False).str[1].map(zone_map)

        # garder interconnexions France
        df = df[
            (df["from_country"] == "France") |
            (df["to_country"] == "France")
        ]

        df["partner"] = np.where(
            df["from_country"] == "France",
            df["to_country"],
            df["from_country"]
        )

        # 4. garder les colonnes d'intérêt
        df[col_name] = df[value_col]
        df["year"] = df["datetime"].dt.year

        # 5. Nettoyage des valeurs redondantes
        df = (
            df.groupby(["datetime", "year", "from_country", "to_country", "partner"], as_index=False)
            [col_name]
            .sum()
        )

        all_df.append(df[[
            "datetime",
            "year",
            "from_country",
            "to_country",
            "partner",
            col_name
        ]])

    if not all_df:
        raise ValueError("Aucun fichier valide")
    
    return pd.concat(all_df, ignore_index=True)


def load_daily_capacity(folder_path, years=[2021, 2022, 2023, 2024]):
    """ Charge files with daily capacities and merge them to extract relevant info (zones, date, capacity)"""
    
    # liste des fichiers
    path = folder_path + "/daily/*.csv"
    years = [str(y) for y in years]
    files = glob.glob(path)

    # lecture + concaténation
    df = pd.concat(
        (pd.read_csv(f) for f in files if any(year in f for year in years)),
        ignore_index=True
    )

    # enlever n/e et renommer en capacity_mw
    df["Capacity (MW)"] = pd.to_numeric(
        df["Capacity (MW)"],
        errors="coerce"
    )
    df = df.rename(columns={"Capacity (MW)": "capacity_mw"})

    # extraction zones robuste
    df["from_country"] = (
        df["Out Area"]
        .str.extract(r"\|(.*)")
        .iloc[:, 0]
        .map(zone_map)
    )

    df["to_country"] = (
        df["In Area"]
        .str.extract(r"\|(.*)")
        .iloc[:, 0]
        .map(zone_map)
    )

    # Supprimer la colonne "Time Interval"
    df = df.drop(columns=["Time Interval"])

    # Mettre au format datetime
    df["day"] = pd.to_datetime(
        df["Day"].str.split(" ").str[1],
        format="%d/%m/%Y"
    )

    # Agréger par jour et par paire de pays en prenant la somme des capacités
    df = (
        df.groupby(["day","from_country","to_country"], as_index=False)
        ["capacity_mw"]
        .sum()
    )

    return df[[
        "day",
        "from_country",
        "to_country",
        "capacity_mw"
    ]]