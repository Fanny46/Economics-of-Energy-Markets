import pandas as pd
import numpy as np

# ── Computation of monetary flows ─────────────────────────────────────────────

def compute_monetary_flows(flows, prices):
    """ Compute value in euros and congestion rent for each flow observation.
    Input : - flows : dataframe with columns datetime, from_country, to_country, flow_mw
            - prices : dataframe with columns datetime, country, price (in EUR/MWh)
    Output : dataframe with columns datetime, from_country, to_country, flow_mw, price_export, price_import, value_eur, congestion_rent"""

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


# ── Merging hourly─────────────────────────────────────────────────
def fill_hourly_with_daily(hourly_report, daily_capacity):
    """ Fill missing hourly capacities with daily capacities, by matching on date and border.
    Tool for merge_hourly_report.
    """

    df = hourly_report.copy()

    # convertir datetime → jour (datetime64)
    df["day"] = pd.to_datetime(df["datetime"]).dt.normalize()

    # conversion des 0 en nan
    df["capacity_mw"] = df["capacity_mw"].replace(0, np.nan)

    # merge
    df = df.merge(
        daily_capacity,
        left_on=["day", "from_country", "to_country"],
        right_on=["day", "from_country", "to_country"],
        how="left",
        suffixes=("", "_daily"),
        validate = "many_to_one"
    )

    # remplir uniquement les capacités manquantes
    df["capacity_mw"] = df["capacity_mw"].fillna(df["capacity_mw_daily"])

    # nettoyage
    df = df.drop(columns=["day", "capacity_mw_daily"])

    return df


def merge_hourly_report(flows, prices, capacities, daily_capacities):

    # calcul des flux monétaires
    flows_money = compute_monetary_flows(flows, prices)

    # supprimer les lignes dupliquées
    flows_money = flows_money.drop_duplicates(
        subset=["datetime", "year", "from_country", "to_country"],
        keep="first"
    )

    # merge avec les capacités horaires
    hourly_report = flows_money.merge(
        capacities,
        on=["datetime","year","from_country","to_country","partner"],
        how="left",
        validate="one_to_one"
     )

    # merge avec les capacités journalières pour remplir les capacités manquantes
    hourly_report = fill_hourly_with_daily(hourly_report, daily_capacities)

    # calcul du taux d'utilisation
    hourly_report["utilization_rate"] = np.where(
        hourly_report["capacity_mw"].notna(),
        hourly_report["flow_mw"] / hourly_report["capacity_mw"],
        np.nan
    )

    return hourly_report


# ── Aggregation yearly ─────────────────────────────────────────────────

def aggregate_yearly(df):
    """ Aggregate hourly report by year and partner, and compute statistics on flows, values, capacities and utilization rates.
    Input : dataframe with columns datetime, year, from_country, to_country, partner, flow_mw, price_export, price_import, value_eur, congestion_rent, capacity_mw, utilization_rate
    Output : dataframe with columns year, partner, export_twh, import_twh, export_value_M€, import_value_M€, export_price_avg_€/MWh, import_price_avg_€/MWh, capacity_coverage, export_capacity_mwh, import_capacity_mwh, export_utilization_rate, import_utilization_rate, export_abs_congestion_rent_M€, import_abs_congestion_rent_M€, utilization_rate, abs_congestion_rent_M€"""

    def compute_stats(g):

        export_flow = g.loc[g.from_country == "France", "flow_mw"].sum()
        import_flow = g.loc[g.to_country == "France", "flow_mw"].sum()

        export_value = g.loc[g.from_country == "France", "value_eur"].sum()
        import_value = g.loc[g.to_country == "France", "value_eur"].sum()

        export_abs_rent = g.loc[g.from_country == "France", "congestion_rent"].abs().sum()
        import_abs_rent = g.loc[g.to_country == "France", "congestion_rent"].abs().sum()

        export_price_avg = (export_value / export_flow) if export_flow > 0 else np.nan
        import_price_avg = (import_value / import_flow) if import_flow > 0 else np.nan

        total_abs_rent = export_abs_rent + import_abs_rent
        spread_avg = total_abs_rent / (export_flow + import_flow) if (export_flow + import_flow) > 0 else np.nan

        export_capacities = g.loc[g.from_country == "France", "capacity_mw"].sum()
        import_capacities = g.loc[g.to_country == "France", "capacity_mw"].sum()

        export_util = (g.loc[g.from_country == "France", "utilization_rate"].mean())
        import_util = (g.loc[g.to_country == "France", "utilization_rate"].mean())
        total_util_rate = (g["utilization_rate"].mean())

        return pd.Series({

            "export_twh": export_flow / 1e6,
            "import_twh": import_flow / 1e6,

            "export_value_M€": export_value / 1e6,
            "import_value_M€": import_value / 1e6,

            "import_price_avg_€/MWh": import_price_avg,
            "export_price_avg_€/MWh": export_price_avg,

            "export_abs_congestion_rent_M€": export_abs_rent / 1e6,
            "import_abs_congestion_rent_M€": import_abs_rent / 1e6,

            "export_capacity_twh": export_capacities / 1e6,
            "import_capacity_twh": import_capacities / 1e6,

            "export_utilization_rate": export_util,
            "import_utilization_rate": import_util,

            "utilization_rate": total_util_rate,
            "spread_avg_€/MWh": spread_avg,
            "abs_congestion_rent_M€": total_abs_rent / 1e6
        })

    yearly = (
        df.groupby(["year", "partner"])
        .apply(compute_stats)
        .reset_index()
        .rename(columns={"partner": "country"})
    )

    return yearly