import os
import re
import math
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
import numpy as np


# ── Load prices and flows ──────────────────────────────────────────────────

def load_flows(folder):

    flows_list = []

    # mapping ENTSO-E zones → pays
    zone_map = {
        "FR": "France",
        "BE": "Belgium",
        "CH": "Switzerland",
        "DE-LU": "Germany",
        "DE-AT-LU": "Germany",
        "ES": "Spain",
        "GB": "Great Britain",
        "GB(ElecLink)": "Great Britain",
        "GB(IFA)": "Great Britain",
        "GB(IFA2)": "Great Britain",
        "IT-North": "Italy-North",
        "IT-North-FR": "Italy-North",
    }

    for file in os.listdir(folder):
        if not file.endswith(".csv"):
            continue

        path = os.path.join(folder, file)
        df = pd.read_csv(path)

        # datetime
        df["datetime"] = pd.to_datetime(
            df["MTU"]
                .str.split(" - ").str[0]      # début intervalle
                .str.replace(r"\s*\(.*\)", "", regex=True),  # enlève (CET) et (CEST)
            dayfirst=True,
            errors="coerce"
        )

        # extract zones
        df["out_zone"] = df["Out Area"].str.replace("BZN|", "", regex=False)
        df["in_zone"] = df["In Area"].str.replace("BZN|", "", regex=False)

        # map → country
        df["from_country"] = df["out_zone"].map(zone_map)
        df["to_country"] = df["in_zone"].map(zone_map)

        # numeric flow
        df["flow_mw"] = pd.to_numeric(
            df["Physical Flow (MW)"],
            errors="coerce"
        )

        # remove n/e
        df = df.dropna(subset=["flow_mw"])

        # garder seulement flux avec la France
        df = df[
            (df["from_country"] == "France") |
            (df["to_country"] == "France")
        ]

        # partenaire = autre pays
        df["partner"] = df.apply(
            lambda x:
            x["to_country"]
            if x["from_country"] == "France"
            else x["from_country"],
            axis=1
        )

        flows_list.append(
            df[[
                "datetime",
                "from_country",
                "to_country",
                "partner",
                "flow_mw"
            ]]
        )

    flows = pd.concat(flows_list, ignore_index=True)

    return flows


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

# ── Calcul des flux monétaires ────────────────────────────────────────────────

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

    df["energy_mwh"] = np.where(
    df["from_country"] == "France",
    df["flow_mw"],      # export France → +
    -df["flow_mw"]      # import France → -
)

    df["value_eur"] = (
        df["energy_mwh"] * df["price_export"]
    )

    df["congestion_rent"] = (
        df["energy_mwh"] *
        (df["price_import"] - df["price_export"])
    )

    df["year"] = df["datetime"].dt.year

    return df

def aggregate_yearly(df):
    yearly = (
        df.groupby(["year", "partner"])
        .agg(
            export_twh=("energy_mwh",
                        lambda x: x[x > 0].sum()/1e6),

            import_twh=("energy_mwh",
                        lambda x: -x[x < 0].sum()/1e6),

            export_value=("value_eur",
                          lambda x: x[x > 0].sum()/1e6),

            import_value=("value_eur",
                          lambda x: -x[x < 0].sum()/1e6)
        )
        .reset_index()
        .rename(columns={"partner": "country"})
    )
    return yearly


# ── Flows maps ────────────────────────────────────────────────────────────────

COUNTRIES = {
    "Great Britain": {
        "nom": "GREAT BRITAIN",
        "fr":  (48.8,  0.5),
        "tgt": (50.8, -1.2),
        "lbl": (52.0, -4.0),
        "sym": ("triangle-up", "triangle-down"),
    },
    "Italy-North": {
        "nom": "ITALY-NORTH",
        "fr":  (44.5,  4.5),
        "tgt": (44.5, 10.0),
        "lbl": (43.0, 11.8),
        "sym": ("triangle-right", "triangle-left"),
    },
    "Spain": {
        "nom": "SPAIN",
        "fr":  (44.0,  0.5),
        "tgt": (41.0, -3.0),
        "lbl": (40.0, -4.5),
        "sym": ("triangle-sw", "triangle-ne"),
    },
    "Switzerland": {
        "nom": "SWITZERLAND",
        "fr":  (46.5,  4.0),
        "tgt": (46.8,  8.5),
        "lbl": (46.8, 11.8),
        "sym": ("triangle-right", "triangle-left"),
    },
    "Belgium": {
        "nom": "BELGIUM",
        "fr":  (49.5,  3.5),
        "tgt": (50.8,  4.3),
        "lbl": (52.1,  3.0),
        "sym": ("triangle-ne", "triangle-sw"),
    },
    "Germany": {
        "nom": "GERMANY",
        "fr":  (48.5,  5.0),
        "tgt": (51.5,  9.5),
        "lbl": (53.2, 11.0),
        "sym": ("triangle-ne", "triangle-sw"),
    },
}


def _arrow_traces(fr, tgt, val_exp, val_imp, info, max_f, ecart=0.3, max_w=15):
    """Génère les traces Scattergeo pour les flèches d'un pays."""
    traces = []
    dx, dy = tgt[1] - fr[1], tgt[0] - fr[0]
    norm = math.hypot(dx, dy)
    px, py = -dy / norm, dx / norm                 # vecteur perpendiculaire

    for val, color, side, sym in [
        (val_exp, "green",  1, info["sym"][0]),
        (val_imp, "red",   -1, info["sym"][1]),
    ]:
        if val <= 0:
            continue
        w    = max(1, (val / max_f) * max_w)
        lons = [fr[1]  + side * ecart * px, tgt[1] + side * ecart * px]
        lats = [fr[0]  + side * ecart * py, tgt[0] + side * ecart * py]
        # ligne
        traces.append(go.Scattergeo(
            lon=lons, lat=lats, mode="lines",
            line=dict(width=w, color=color), hoverinfo="skip",
        ))
        # tête de flèche (→ bout côté tgt pour export, côté fr pour import)
        tip_lon = lons[1] if color == "green" else lons[0]
        tip_lat = lats[1] if color == "green" else lats[0]
        traces.append(go.Scattergeo(
            lon=[tip_lon], lat=[tip_lat], mode="markers",
            marker=dict(symbol=sym, size=w + 8, color=color),
            hoverinfo="skip",
        ))
    return traces


def create_flows_map(yearly_df, year, flow_type="physical"):
    """
    flow_type :
        - "physical"  → flux physiques (TWh)
        - "monetary"  → flux monétaires (Md €)
    """

    # ─────────────────────────────
    # Choix du type de flux
    # ─────────────────────────────
    if flow_type == "physical":
        export_col = "export_twh"
        import_col = "import_twh"
        unit = "TWh"

    elif flow_type == "monetary":
        export_col = "export_value"
        import_col = "import_value"
        unit = "Md€"

    else:
        raise ValueError("flow_type must be 'physical' or 'monetary'")

    # dataframe année
    df_year = yearly_df[yearly_df["year"] == year].copy()

    # harmonisation noms colonnes
    df_year["export"] = df_year[export_col]
    df_year["import"] = df_year[import_col]

    # total France
    totals = {
        "export": df_year["export"].sum(),
        "import": df_year["import"].sum(),
    }

    fig = go.Figure()

    # normalisation largeur flèches
    max_f = max(
        1,
        df_year["export"].max(),
        df_year["import"].max()
    )

    total_exp = 0
    total_imp = 0

    # ─────────────────────────────
    # Boucle pays
    # ─────────────────────────────
    for country, info in COUNTRIES.items():

        row = df_year[df_year["country"] == country]

        if row.empty:
            continue

        val_exp = row["export"].iloc[0]
        val_imp = row["import"].iloc[0]

        total_exp += val_exp
        total_imp += val_imp

        # ligne guide
        fig.add_trace(go.Scattergeo(
            lon=[info["lbl"][1], info["tgt"][1]],
            lat=[info["lbl"][0], info["tgt"][0]],
            mode="lines",
            line=dict(width=1, color="rgba(100,100,100,0.2)"),
            hoverinfo="skip",
        ))

        label = (
            f"<b>{info['nom']}</b><br>"
            f"<span style='color:green'>Exp: {val_exp:,.3f} {unit}</span><br>"
            f"<span style='color:red'>Imp: {val_imp:,.3f} {unit}</span>"
        ).replace(",", "\u202f")

        fig.add_trace(go.Scattergeo(
            lon=[info["lbl"][1]],
            lat=[info["lbl"][0]],
            mode="text",
            text=[label],
            textfont=dict(size=14, color="#0b1736"),
            hoverinfo="skip",
        ))

        # flèches
        for t in _arrow_traces(
            info["fr"],
            info["tgt"],
            val_exp,
            val_imp,
            info,
            max_f
        ):
            fig.add_trace(t)

    # ─────────────────────────────
    # Bilan France
    # ─────────────────────────────
    solde = totals["export"] - totals["import"]

    bilan = (
        f"<b>TOTAL FRANCE {year}</b><br>"
        f"Exp: {totals['export']:,.3f} {unit}<br>"
        f"Imp: {totals['import']:,.3f} {unit}<br>"
        f"Net: {solde:,.3f} {unit}"
    ).replace(",", "\u202f")

    fig.add_trace(go.Scattergeo(
        lon=[-5.5],
        lat=[46.5],
        mode="text",
        text=[bilan],
        textfont=dict(size=15, color="black"),
        hoverinfo="skip",
    ))

    fig.update_layout(
        geo=dict(
            scope="europe",
            showland=True,
            landcolor="#e0f3f8",
            countrycolor="white",
            center=dict(lon=4.0, lat=47.0),
            projection_scale=4,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=600,
        showlegend=False,
        hovermode=False,
        dragmode=False,
    )

    return fig