from flows import *

flows_folder = "./data/flows"
price_folder = "./data/energy_prices"
capacities_folder = "./data/capacities"

def gen_yearly_report():
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

    df["utilization_rate"] = (
        df["flow_mw"].abs()
        / df["capacity_mw"].replace(0, np.nan).abs()
    )

    # df.to_csv("hourly_report.csv", index=False)

    yearly_report = aggregate_yearly(df)
    yearly_report.to_csv("yearly_report.csv", index=False)


def gen_flows_maps():
    yearly_report = pd.read_csv("yearly_report.csv")
    for i in range(2021, 2025):
        fig_phy = create_flows_map(yearly_report, i, "physical")
        fig_mon = create_flows_map(yearly_report, i, "monetary")
        fig_phy.write_image(f"plots/flows_map_physical_{i}.png", scale=2)
        fig_mon.write_image(f"plots/flows_map_monetary_{i}.png", scale=2)


if __name__ == "__main__":
    gen_yearly_report()
    # gen_flows_maps()