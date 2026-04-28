import pandas as pd

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

def load_daily_capacity(df, zone_map):

    # enlever n/e
    df["Capacity (MW)"] = pd.to_numeric(
        df["Capacity (MW)"],
        errors="coerce"
    )

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

    # signe directionnel
    df["capacity_mw"] = df.apply(
        lambda r: r["Capacity (MW)"]
        if r["from_country"] == "France"
        else -r["Capacity (MW)"],
        axis=1
    )

    return df[[
        "from_country",
        "to_country",
        "capacity_mw"
    ]]

def fill_capacity_with_daily(hourly_report, daily_capacity):

    df = hourly_report.copy()

    # merge fallback
    df = df.merge(
        daily_capacity,
        on=["from_country", "to_country"],
        how="left",
        suffixes=("", "_daily")
    )

    # remplir uniquement les NaN
    df["capacity_mw"] = df["capacity_mw"].fillna(
        df["capacity_mw_daily"]
    )

    df = df.drop(columns=["capacity_mw_daily"])

    return df


# main.py
import glob

# dossier contenant les fichiers
path = "data/capacities/daily/*.csv"

# liste des fichiers
files = glob.glob(path)

# lecture + concaténation
daily = pd.concat(
    (pd.read_csv(f) for f in files),
    ignore_index=True
)

print(daily.shape)

# main.py
hourly_report = pd.read_csv("hourly_report.csv")
daily_cap = load_daily_capacity(daily, zone_map)

hourly_report = fill_capacity_with_daily(
    hourly_report,
    daily_cap
)

hourly_report.to_csv("hourly_report_filled.csv", index=False)