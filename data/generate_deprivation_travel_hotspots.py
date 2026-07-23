"""
Precomputes the deprivation + travel-time hotspot analysis and writes it to
data/deprivation_travel_hotspots.pkl, so the Streamlit page can load a ready-made
GeoDataFrame instead of solving the site problem and running Local Moran's I
(spatial weights + permutation inference over 729 LSOAs) live on every session.

Like the demand/travel hotspots, deprivation vs travel is a *solution*-level
analysis: the travel time to each LSOA's nearest site only exists once the
problem has been solved. We solve the existing-CDCs / car-travel problem exactly
as the Travel_Car page does (existing sites + the car travel matrix + solve(p=4)),
add the IMD deprivation data, then ask lokigi for
get_hotspots(what="travel_equity", n_bins=2).

The demand ID column is renamed to "LSOA21NM" here so that the demand/travel key
and the region-geometry key share one column name (lokigi's solution-level travel
analysis looks the region key up by name inside the solved problem_df), keeping
the pickle keyed by "LSOA21NM" like the other hotspot pickles. Only the column
*name* changes; the values (LSOA names) are identical, so the solve is unchanged
from the Travel_Car page.

The pickle holds the Devon LSOA geometry plus the cluster_type,
attribute_typology, combined_score, p_value, local_moran_i and min_cost columns
the page colours and tooltips by. n_bins=2 gives the four Low/High deprivation x
Good/Poor access typology classes.

A pickle (rather than a GeoPackage) is used so the Arrow-backed string /
categorical columns lokigi produces survive the round-trip unchanged.

Re-run with `uv run python data/generate_deprivation_travel_hotspots.py` whenever
the deprivation or car-travel inputs change.
"""

import geopandas as gpd
import pandas as pd
from lokigi.site import SiteProblem

OUTPUT_PATH = "data/deprivation_travel_hotspots.pkl"


def main():
    # Mirrors setup_lokigi_site_problem_car_existing() in app/utils.py, but keys
    # demand by "LSOA21NM" (same values as "LSOA 2021 Name") so the solution-level
    # travel analysis can find the region key inside the solved problem_df.
    demand = pd.read_csv("data/demand_MF_50_84.csv").rename(
        columns={"LSOA 2021 Name": "LSOA21NM"}
    )

    sites = pd.read_csv("data/devon_cdcs.csv")
    sites = gpd.GeoDataFrame(
        sites,
        geometry=gpd.points_from_xy(sites["Longitude"], sites["Latitude"]),
        crs="EPSG:4326",
    )
    sites = sites[sites["Existing"] == "Yes"]

    travel = pd.read_csv("data/travel_matrix_car.csv").fillna(9999.0)

    problem = SiteProblem()
    problem.add_demand(demand, demand_col="MF50-84", location_id_col="LSOA21NM")
    problem.add_region_geometry_layer(
        gpd.read_file("data/LSOA_Devon_2021_EW_BSC_V4.gpkg"), common_col="LSOA21NM"
    )
    problem.add_sites(sites, candidate_id_col="Facility_Name")
    problem.add_travel_matrix(travel, unit="minutes", source_col="from_id")
    problem.add_equity_data(
        pd.read_csv("data/devon_imd_2025_2021_LSOAs.csv"),
        equity_col="Index of Multiple Deprivation (IMD) Decile (where 1 is most deprived 10% of LSOA",
        common_col="LSOA name (2021)",
        label="IMD Decile",
        disadvantaged_end="low",  # decile 1 = most deprived
    )

    solution = problem.solve(p=4)

    hotspots_gdf = solution.get_hotspots(what="travel_equity", n_bins=2)

    hotspots_gdf.to_pickle(OUTPUT_PATH)

    print(f"Wrote {OUTPUT_PATH} ({len(hotspots_gdf)} rows)")
    print(hotspots_gdf["cluster_type"].value_counts())
    print(
        "typology classes:",
        sorted(hotspots_gdf["attribute_typology"].dropna().unique().tolist()),
    )


if __name__ == "__main__":
    main()
