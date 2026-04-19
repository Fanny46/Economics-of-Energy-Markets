import math
import plotly.graph_objects as go


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


def histogramme_congestion(df, year):
    # Filtrer pour l'année donnée
    df = df[df["year"] == year]

    # Filtrer les lignes où congestion > 0
    df_congestion = df[df["structural_congestion_index"] > 0]

    # Partner en abscisse, congestion en ordonnée
    fig = go.Figure(data=go.Bar(
        x=df_congestion["partner"],
        y=df_congestion["structural_congestion_index"],
        marker_color='indianred'
    ))
    fig.update_layout(
        title=f"Structural Congestion Index - {year}",
        xaxis_title="Partner Country",
        yaxis_title="Structural Congestion Index",
        yaxis=dict(range=[0, df_congestion["structural_congestion_index"].max() * 1.2])
    )
    return fig
