from flows import *
from maps import *

flows_folder = "./data/flows"
price_folder = "./data/energy_prices"
capacities_folder = "./data/capacities"


def gen_reports():

    capacities = load_entsoe_folder(capacities_folder, "capacity")
    capacities.rename(columns={"value_mw":"capacity_mw"}, inplace=True)

    capacities_clean = (
        capacities
        .groupby(["datetime","from_country", "to_country"], as_index=False)
        .agg(capacity_mw=("capacity_mw","max"))
    )

    flows = load_entsoe_folder(flows_folder, "flow")
    flows.rename(columns={"value_mw":"flow_mw"}, inplace=True)

    prices = load_prices(price_folder)

    flows_money = compute_monetary_flows(flows, prices)

    df = flows_money.merge(
        capacities_clean,
        on=["datetime","from_country","to_country"],
        how="left",
        validate="many_to_one"
    )

    df.to_csv("hourly_report.csv", index=False)
    
    yearly_report = aggregate_yearly(df)
    yearly_report.to_csv("yearly_report.csv", index=False)

    congestion = compute_structural_congestion(df)
    congestion.to_csv("congestion_yearly.csv", index=False)


if __name__ == "__main__":
    
    congestion = pd.read_csv("congestion_yearly.csv")
    hourly_report = pd.read_csv("hourly_report.csv")
    yearly_report = pd.read_csv("yearly_report.csv")

    for i in range(2021, 2025):

        # # histogramme nombre d'heures à forte utilisation
        # histo_hours = histogram_hours(hourly_report, i)
        # # histo_hours.write_image(f"plots/hours_high_utilization/histogram_hours_high_utilization_{i}.png", scale=2)

        # # histogramme de la rente de congestion
        # histo_rent = histogram_congestion_rent(yearly_report, year=i)
        # histo_rent.write_image(f"plots/congestion_rent/histogram_congestion_rent_{i}.png", scale=2)

        # # graphique de congestion à deux axes
        # congestion_graph = plot_congestion_map(congestion, i)
        # congestion_graph.write_image(f"plots/spread_and_utilization/congestion_graph_{i}.png", scale=2)

        # # histogramme structural congestion index
        # histo_congestion = histogram_congestion(congestion, type="structural_congestion_index", year=i)
        # histo_congestion.write_image(f"plots/structural_congestion/histogram_structural_congestion_{i}.png", scale=2)

        # # cartes de flux physiques et monétaires
        # fig_phy = create_flows_map(yearly_report, i, "physical")
        # fig_mon = create_flows_map(yearly_report, i, "monetary")
        # fig_phy.write_image(f"plots/flows_maps/flows_map_physical_{i}.png", scale=2)
        # fig_mon.write_image(f"plots/flows_maps/flows_map_monetary_{i}.png", scale=2)





# Compter le nombre d'heures où la congestion rent est positive ET la France est exportatrice
# hourly_report["congestion_rent_positive_and_exporting"] = (hourly_report["congestion_rent"] > 0) & (hourly_report["flow_mw"] > 0)
# hours = hourly_report[(hourly_report["congestion_rent_positive_and_exporting"] == True)].shape[0]
# print("nb of hours where congestion rent is positive and France is exporting:", hours)

# hourly_report["congestion_rent_positive_and_importing"] = (hourly_report["congestion_rent"] > 0) & (hourly_report["flow_mw"] < 0)
# hours = hourly_report[(hourly_report["congestion_rent_positive_and_importing"] == True)].shape[0]
# print("nb of hours where congestion rent is positive and France is importing:", hours)

# hourly_report["congestion_rent_negative_and_exporting"] = (hourly_report["congestion_rent"] < 0) & (hourly_report["flow_mw"] > 0)
# hours = hourly_report[(hourly_report["congestion_rent_negative_and_exporting"] == True)].shape[0]
# print("nb of hours where congestion rent is negative and France is exporting:", hours)

# hourly_report["congestion_rent_negative_and_importing"] = (hourly_report["congestion_rent"] < 0) & (hourly_report["flow_mw"] < 0)
# hours = hourly_report[(hourly_report["congestion_rent_negative_and_importing"] == True)].shape[0]
# print("nb of hours where congestion rent is negative and France is importing:", hours)

# # Afficher les export_congestion_rent et import_congestion_rent par pays partenaire de la France
# congestion_by_partner = yearly_report.groupby("country").agg(
#     export_congestion_rent=("export_congestion_rent", "sum"),
#     import_congestion_rent=("import_congestion_rent", "sum")
# ).reset_index()
# print(congestion_by_partner)



