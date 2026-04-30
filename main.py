from src.load_files import *
from src.gen_reports import *
from src.visualization import *

flows_folder = "./data/flows"
price_folder = "./data/energy_prices"
capacities_folder = "./data/capacities"


def gen_reports():

    flows = load_entsoe_folder(flows_folder, "flow")
    prices = load_prices(price_folder)
    capacities = load_entsoe_folder(capacities_folder, "capacity")
    daily_capacities = load_daily_capacity(capacities_folder)

    hourly_report = merge_hourly_report(flows, prices, capacities, daily_capacities)
    yearly_report = aggregate_yearly(hourly_report)
    print(yearly_report.head())

    hourly_report.to_csv("hourly_report.csv", index=False)
    hourly_report.to_parquet("hourly_report.parquet", index=False)
    yearly_report.to_csv("yearly_report.csv", index=False)

    

if __name__ == "__main__":
    # gen_reports()
    
    # hourly_report = pd.read_parquet("hourly_report.parquet")
    # yearly_report = pd.read_csv("yearly_report.csv")

    # for i in range(2021, 2025):

        # # histogramme nombre d'heures à forte utilisation
        # histo_hours = histogram_hours(hourly_report, i)
        # histo_hours.write_image(f"plots/hours_high_utilization/histogram_hours_high_utilization_{i}.png", scale=2)

        # # histogramme de la rente de congestion
        # histo_rent = histogram_congestion_rent(yearly_report, year=i)
        # histo_rent.write_image(f"plots/congestion_rent/histogram_congestion_rent_{i}.png", scale=2)

        # graphique de congestion à deux axes
        # congestion_graph = plot_congestion_map(yearly_report, i)
        # congestion_graph.write_image(f"plots/spread_and_utilization/congestion_graph_{i}.png", scale=2)

        # # cartes de flux physiques et monétaires
        # fig_phy = create_flows_map(yearly_report, i, "physical")
        # fig_mon = create_flows_map(yearly_report, i, "monetary")
        # fig_phy.write_image(f"plots/flows_maps/flows_map_physical_{i}.png", scale=2)
        # fig_mon.write_image(f"plots/flows_maps/flows_map_monetary_{i}.png", scale=2)

