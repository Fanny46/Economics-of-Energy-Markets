import os
import pandas as pd
from pathlib import Path
import numpy as np


# ── Load prices and flows ──────────────────────────────────────────────────

def load_prices(price_folder):

    files = Path(price_folder).glob("Energy prices *.csv")
    prices_list = []

    for f in files:

        country = (
            f.name.replace("Energy prices ", "")
                  .replace(".csv", "").split(" ")[0]
        )

        df = pd.read_csv(f)

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


def load_entsoe_folder(folder_path, value_type="flow"):
    """
    value_type : "flow" ou "capacity"
    """
    all_df = []
    
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

    for fname in os.listdir(folder_path):
        if not fname.endswith(".csv"):
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
        elif value_type == "capacity":
            value_col = "Capacity (MW)"
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

        # 4. convention signe
        # export FR = +
        # import FR = -
        df["value_mw"] = np.where(
            df["from_country"] == "France",
            df[value_col],
            -df[value_col]
        )

        # année (depuis datetime → plus robuste)
        df["year"] = df["datetime"].dt.year

        all_df.append(df[[
            "datetime",
            "year",
            "from_country",
            "to_country",
            "partner",
            "value_mw"
        ]])

    if not all_df:
        raise ValueError("Aucun fichier valide")
    
    return pd.concat(all_df, ignore_index=True)


# ── Computation of monetary flows ─────────────────────────────────────────────

def compute_monetary_flows(flows, prices):

    df = flows.copy()

    df = df.merge(
        prices.rename(columns={
            "country": "from_country",
            "price": "price_export"
        }),
        on=["from_country", "datetime"],
        how="left"
    )

    df = df.merge(
        prices.rename(columns={
            "country": "to_country",
            "price": "price_import"
        }),
        on=["to_country", "datetime"],
        how="left"
    )

    df["value_eur"] = (
        df["flow_mw"] * df["price_export"]
    )

    df["congestion_rent"] = (
        df["flow_mw"] *
        (df["price_import"] - df["price_export"])
    )

    return df

# ── Aggregation yearly ─────────────────────────────────────────────────

def aggregate_yearly(df):

    def compute_stats(g):

        # 1. FLOWS COMPLETS
        export_flow = g.loc[g.flow_mw > 0, "flow_mw"].sum()
        import_flow = -g.loc[g.flow_mw < 0, "flow_mw"].sum()

        export_value = g.loc[g.flow_mw > 0, "value_eur"].sum()
        import_value = -g.loc[g.flow_mw < 0, "value_eur"].sum()

        export_rent = g.loc[g.flow_mw > 0, "congestion_rent"].sum()
        import_rent = -g.loc[g.flow_mw < 0, "congestion_rent"].sum()

        # 2. SUBSET VALIDE POUR CAPACITÉS
        valid = g.dropna(subset=["capacity_mw"])
        coverage = coverage = len(valid) / len(g)

        if valid.empty:
            export_cap = np.nan
            import_cap = np.nan
            export_util = np.nan
            import_util = np.nan

        else:
            export_cap_series = valid.loc[valid.capacity_mw > 0, "capacity_mw"]
            import_cap_series = -valid.loc[valid.capacity_mw < 0, "capacity_mw"]

            export_cap = export_cap_series.sum()
            import_cap = import_cap_series.sum()

            # taux d'utilisation structurel
            export_util = (
                valid.loc[valid.flow_mw > 0, "flow_mw"].sum()
                / export_cap
                if export_cap > 0 else np.nan
            )

            import_util = (
                -valid.loc[valid.flow_mw < 0, "flow_mw"].sum()
                / import_cap
                if import_cap > 0 else np.nan
            )

        # 3. OUTPUT
        return pd.Series({

            "export_twh": export_flow / 1e6,
            "import_twh": import_flow / 1e6,

            "export_value": export_value / 1e6,
            "import_value": import_value / 1e6,

            "capacity_coverage": coverage,

            "export_capacity_mwh": export_cap,
            "import_capacity_mwh": import_cap,

            "export_utilization_rate": export_util,
            "import_utilization_rate": import_util,

            "export_congestion_rent": export_rent / 1e6,
            "import_congestion_rent": import_rent / 1e6,
        })

    yearly = (
        df.groupby(["year", "partner"])
        .apply(compute_stats)
        .reset_index()
        .rename(columns={"partner": "country"})
    )

    return yearly


# ── Structural Congestion Index (SCI) ─────────────────────────────────────────
def compute_structural_congestion(df):

    def stats(g):

        valid = g.dropna(
            subset=["flow_mw", "capacity_mw",
                    "price_export", "price_import"]
        )

        # toujours retourner la même structure
        if valid.empty:
            return pd.Series({
                "utilization": np.nan,
                "avg_spread": np.nan,
                "congestion_rent": np.nan,
                "avg_price": np.nan
            })

        flow_abs = valid["flow_mw"].abs()

        # utilisation physique
        utilization = (
            flow_abs.sum()
            / valid["capacity_mw"].abs().sum()
        )

        # price spread pondéré
        spread = (
            (flow_abs *
             (valid["price_import"]
              - valid["price_export"]).abs())
            .sum()
            / flow_abs.sum()
        )

        congestion_rent = valid["congestion_rent"].sum()

        avg_price = (
            valid[["price_import", "price_export"]]
            .stack()
            .mean()
        )

        return pd.Series({
            "utilization": utilization,
            "avg_spread": spread,
            "congestion_rent": congestion_rent,
            "avg_price": avg_price
        })

    # --- agrégation ---
    out = (
        df.groupby(["year", "partner"])
          .apply(stats)
          .reset_index()
    )

    # --- normalisations ---
    out["spread_norm"] = out["avg_spread"] / out["avg_price"]

    out["rent_norm"] = (
        out["congestion_rent"].abs()
        / out["congestion_rent"].abs().max()
    )

    out["structural_congestion_index"] = (
        out["utilization"]
        * out["spread_norm"]
        * out["rent_norm"]
    )

    return out