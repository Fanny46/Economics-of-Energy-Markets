import math
import plotly.graph_objects as go
import numpy as np


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
        - "monetary"  → flux monétaires (M€)
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
        unit = "M€"

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


# ── Histograms ────────────────────────────────────────────────────────────────

def histogram_hours(df, year=None):
    # Filtrer pour l'année donnée
    if year is not None:
        df = df[df["year"] == year]

    # Compter le nombre d'heures avec taux d'utilisation > 80% pour chaque interconnexion
    # Pour chaque interconnexion, indiquer avec deux couleurs différentes les heures d'exportation et d'importation à forte utilisation
    df["utilization_rate"] = df["flow_mw"].abs() / df["capacity_mw"].abs()
    df["high_utilization"] = df["utilization_rate"] > 0.8
    df["flow_direction"] = df["flow_mw"].apply(lambda x: "export" if x > 0 else "import")
    high_utilization = df[df["high_utilization"]]
    counts = high_utilization.groupby(["from_country", "to_country", "flow_direction"]).size().reset_index(name="hours_high_utilization")
    
    fig = go.Figure()
    
    for flow_direction, color in [("export", "green"), ("import", "red")]:
        df_direction = counts[counts["flow_direction"] == flow_direction]
        fig.add_trace(go.Bar(
            x=df_direction.apply(lambda row: f"{row['from_country']} → {row['to_country']}", axis=1),
            y=df_direction["hours_high_utilization"],
            name=flow_direction.capitalize(),
            marker_color=color
        ))
    fig.update_layout(
        title="Hours with Utilization Rate > 80%",
        xaxis_title="Interconnection",
        yaxis_title="Number of Hours",
        barmode='stack'
    )
    return fig


def histogram_congestion_rent(df, year=None):
    """ Prend en entrée le yearly_report"""
    # Filtrer pour l'année donnée
    if year is not None:
        df = df[df["year"] == year]

    # Pour chaque partenaire, afficher par deux couleurs différentes les barres de la rente de congestion à l'export et à l'import
    df_congestion = df[(df["export_congestion_rent"] > 0) | (df["import_congestion_rent"] > 0)].copy()
    df_congestion["congestion_rent"] = df_congestion["export_congestion_rent"].fillna(0) - df_congestion["import_congestion_rent"].fillna(0)

    fig = go.Figure()
    for direction, color in [("export_congestion_rent", "green"), ("import_congestion_rent", "red")]:
        df_direction = df_congestion[df_congestion[direction] > 0]
        fig.add_trace(go.Bar(
            x=df_direction["country"],
            y=df_direction[direction],
            name=direction.replace("_", " ").capitalize(),
            marker_color=color
        ))
    fig.update_layout(
        title="Congestion rent by partner" + (f" ({year})" if year is not None else ""),
        xaxis_title="Partner country",
        yaxis_title="Congestion rent (M€)",
        barmode='stack'
    )
    return fig


def histogram_congestion(df, type="structural_congestion_index", year=None):
    """Histogramme d'un indice de congestion par partenaire pour une année donnée.
    
    type :
    * "structural_congestion_index" → index de congestion structurelle
    * "congestion_rent" → rente de congestion
    """

    # Filtrer pour l'année donnée
    if year is not None:
        df = df[df["year"] == year]

    # Filtrer les lignes où congestion > 0
    df_congestion = df[df[type] > 0]

    # Partner en abscisse, congestion en ordonnée
    fig = go.Figure(data=go.Bar(
        x=df_congestion["partner"],
        y=df_congestion[type],
        marker_color='indianred'
    ))
    fig.update_layout(
        title=f"{type.replace('_', ' ').title()} - {year}",
        xaxis_title="Partner Country",
        yaxis_title=type.replace('_', ' ').title(),
        yaxis=dict(range=[0, df_congestion[type].max() * 1.2])
    )
    return fig


# ── Graphs ────────────────────────────────────────────────────────────────

def plot_congestion_map_old(congestion, year):

    df = congestion.loc[congestion["year"] == year].copy()

    # sens dominant du flux
    df["direction"] = np.where(
        df["congestion_rent"] > 0,
        "France exports",
        "France imports"
    )

    # couleurs
    colors = {
        "France exports": "green",
        "France imports": "red"
    }
    
    # graphique
    fig = go.Figure()
    for direction, g in df.groupby("direction"):
        fig.add_trace(go.Scatter(
            x=g["utilization"],
            y=g["avg_spread"],
            mode="markers+text",
            name=direction,
            text=g["partner"],
            textposition="top center",
            marker=dict(size=12, color=colors[direction], opacity=0.8)
        ))
    fig.update_layout(
        title=f"France congestion map ({year})",
        xaxis_title="Average utilization rate",
        yaxis_title="Average price spread (€/MWh)",
        legend_title="Flow direction",
        xaxis=dict(range=[0, 1]),
        yaxis=dict(range=[0, df["avg_spread"].max() * 1.2])
    )
    return fig


def plot_congestion_map(congestion, year):

    df = congestion.loc[congestion["year"] == year].copy()

    # sens dominant du flux
    df["direction"] = np.where(
        df["congestion_rent"] > 0,
        "France exports",
        "France imports"
    )

    colors = {
        "France exports": "green",
        "France imports": "red"
    }

    # --------------------------------------------------
    # seuils séparant les cadrans
    # --------------------------------------------------
    util_thresh = df["utilization"].median()
    spread_thresh = df["avg_spread"].median()

    xmax = 1
    ymax = df["avg_spread"].max() * 1.2

    fig = go.Figure()

    # --------------------------------------------------
    # POINTS
    # --------------------------------------------------
    for direction, g in df.groupby("direction"):
        fig.add_trace(go.Scatter(
            x=g["utilization"],
            y=g["avg_spread"],
            mode="markers+text",
            name=direction,
            text=g["partner"],
            textposition="top center",
            marker=dict(
                size=12,
                color=colors[direction],
                opacity=0.85
            )
        ))

    # --------------------------------------------------
    # QUADRANTS COLORÉS
    # --------------------------------------------------
    fig.update_layout(
        shapes=[

            # Bas gauche : marché intégré
            dict(
                type="rect",
                x0=0, x1=util_thresh,
                y0=0, y1=spread_thresh,
                fillcolor="lightgreen",
                opacity=0.15,
                line_width=0,
                layer="below"
            ),

            # Bas droit : arbitrage efficace
            dict(
                type="rect",
                x0=util_thresh, x1=xmax,
                y0=0, y1=spread_thresh,
                fillcolor="lightblue",
                opacity=0.15,
                line_width=0,
                layer="below"
            ),

            # Haut gauche : problème marché
            dict(
                type="rect",
                x0=0, x1=util_thresh,
                y0=spread_thresh, y1=ymax,
                fillcolor="orange",
                opacity=0.15,
                line_width=0,
                layer="below"
            ),

            # Haut droit : congestion structurelle
            dict(
                type="rect",
                x0=util_thresh, x1=xmax,
                y0=spread_thresh, y1=ymax,
                fillcolor="red",
                opacity=0.15,
                line_width=0,
                layer="below"
            ),
        ]
    )

    # --------------------------------------------------
    # LIGNES DE SÉPARATION
    # --------------------------------------------------
    fig.add_vline(x=util_thresh, line_dash="dash")
    fig.add_hline(y=spread_thresh, line_dash="dash")

    # --------------------------------------------------
    # LABELS DES CADRANS
    # --------------------------------------------------
    fig.add_annotation(
        x=util_thresh/2,
        y=spread_thresh/2,
        text="Integrated market",
        showarrow=False
    )

    fig.add_annotation(
        x=(util_thresh+xmax)/2,
        y=spread_thresh/2,
        text="Efficient arbitrage",
        showarrow=False
    )

    fig.add_annotation(
        x=util_thresh/2,
        y=(spread_thresh+ymax)/2,
        text="Market barrier",
        showarrow=False
    )

    fig.add_annotation(
        x=(util_thresh+xmax)/2,
        y=(spread_thresh+ymax)/2,
        text="Structural congestion",
        showarrow=False,
        font=dict(size=13)
    )

    # --------------------------------------------------
    # LAYOUT
    # --------------------------------------------------
    fig.update_layout(
        title=f"France congestion map ({year})",
        xaxis_title="Average utilization rate",
        yaxis_title="Average price spread (€/MWh)",
        legend_title="Flow direction",
        xaxis=dict(range=[0, xmax]),
        yaxis=dict(range=[0, ymax])
    )

    return fig