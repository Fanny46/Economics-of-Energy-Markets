from flows import *

flows_folder = "./data/physical_flows"
price_folder = "./data/energy_prices"

def gen_yearly_flows(price_folder=price_folder, flows_folder=flows_folder):
    prices = load_prices(price_folder)
    flows = load_flows(flows_folder)
    flows_money = compute_monetary_flows(flows, prices)
    yearly_report = aggregate_yearly(flows_money)
    yearly_report.to_csv("yearly_report.csv", index=False)


def gen_flows_maps(yearly_report):
    yearly_report = pd.read_csv(yearly_report)
    for i in range(2024, 2025):
        fig_phy = create_flows_map(yearly_report, i, "physical")
        fig_mon = create_flows_map(yearly_report, i, "monetary")
        fig_phy.write_image(f"plots/flows_map_physical_{i}.png", scale=2)
        fig_mon.write_image(f"plots/flows_map_monetary_{i}.png", scale=2)


gen_flows_maps("yearly_report.csv")

