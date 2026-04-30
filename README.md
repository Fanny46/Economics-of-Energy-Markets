# Economics of Energy Markets

This repository analyzes electricity transmission flows between France and its neighboring markets using ENTSO-E data. It builds hourly and yearly reports, computes monetary flows and congestion rents, and produces visualizations such as flow maps and congestion charts.

## What this project does

- Loads hourly cross-border flow data, day-ahead prices, and interconnection capacities.
- Merges those datasets into a single hourly report.
- Fills missing hourly capacities with daily capacity data when available.
- Aggregates the hourly report into yearly indicators by partner country.
- Generates Plotly figures for flow maps, congestion rent histograms, utilization histograms, and congestion quadrants.

## Repository layout

- `main.py`: entry point used to load data, build reports, and export results for some years.
- `src/load_files.py`: data ingestion helpers for prices, flows, hourly capacities, and daily capacities.
- `src/gen_reports.py`: report-building logic, including monetary flow computation, hourly merging, and yearly aggregation.
- `src/visualization.py`: Plotly-based charts and maps.
- `data/flows/`: hourly flow CSV files.
- `data/energy_prices/`: day-ahead price CSV files.
- `data/capacities/`: hourly capacity CSV files and `daily/` fallback capacity files.
- `plots/`: exported figures.
- `hourly_report.csv` / `yearly_report.csv`: generated outputs.
- `hourly_report.parquet`: optional parquet export of the hourly report.
- `test.ipynb`: exploratory notebook.

## Data pipeline

The code follows this workflow:

1. Load ENTSO-E flow files, price files, and capacity files.
2. Standardize country names and timestamps.
3. Compute monetary flows and congestion rent.
4. Merge hourly flows with hourly capacities.
5. Fill missing hourly capacities with daily capacity data.
6. Compute utilization rates.
7. Aggregate hourly data into yearly statistics by partner country.

## How to run

By default, `main.py` contains example code and commented-out blocks for report generation and plotting. If you want to regenerate the CSV and parquet outputs, uncomment the `gen_reports()` call and run the file again.

## Output files

When the pipeline is executed, it produces:

- `hourly_report.csv`: merged hourly dataset
- `hourly_report.parquet`: parquet version of the hourly dataset
- `yearly_report.csv`: yearly aggregation by partner country
- figures exported into the `plots/` subfolders.




