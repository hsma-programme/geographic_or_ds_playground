"""
Precomputes the demand + deprivation hotspot analysis and writes it to
data/demand_deprivation_hotspots.pkl, so the Streamlit page can load a ready-made
GeoDataFrame instead of running Local Moran's I (spatial weights + permutation
inference over 729 LSOAs) live on every session.

The pickle holds the GeoDataFrame returned by lokigi's
SiteProblem.get_hotspots(what="demand_equity", n_bins=2): the Devon LSOA geometry
plus the cluster_type, attribute_typology, combined_score, p_value and
local_moran_i columns the page colours and tooltips by. n_bins=2 gives the four
High/Low demand x deprivation typology classes.

A pickle (rather than a GeoPackage) is used so the Arrow-backed string /
categorical columns lokigi produces survive the round-trip unchanged.

Re-run with `uv run python data/generate_hotspots.py` whenever the demand or
deprivation inputs change.
"""

import geopandas as gpd
import pandas as pd
from lokigi.site import SiteProblem

OUTPUT_PATH = "data/demand_deprivation_hotspots.pkl"


def main():
    problem = SiteProblem()

    problem.add_demand(
        pd.read_csv("data/demand_MF_50_84.csv"),
        demand_col="MF50-84",
        location_id_col="LSOA 2021 Name",
    )

    problem.add_region_geometry_layer(
        gpd.read_file("data/LSOA_Devon_2021_EW_BSC_V4.gpkg"),
        common_col="LSOA21NM",
    )

    problem.add_equity_data(
        pd.read_csv("data/devon_imd_2025_2021_LSOAs.csv"),
        equity_col="Index of Multiple Deprivation (IMD) Decile (where 1 is most deprived 10% of LSOA",
        common_col="LSOA name (2021)",
        label="IMD Decile",
        disadvantaged_end="low",  # decile 1 = most deprived
    )

    hotspots_gdf = problem.get_hotspots(what="demand_equity", n_bins=2)

    hotspots_gdf.to_pickle(OUTPUT_PATH)

    print(f"Wrote {OUTPUT_PATH} ({len(hotspots_gdf)} rows)")
    print(hotspots_gdf["cluster_type"].value_counts())


if __name__ == "__main__":
    main()
