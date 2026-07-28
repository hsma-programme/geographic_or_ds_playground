"""
Generates data/demand_MF_50_84_projected_2036.csv: an illustrative 10-year-ahead
projection of the 50-84 population demand dataset (data/demand_MF_50_84.csv).

This is a *synthetic teaching dataset*, not an ONS population projection. It is
built from a documented, district-level growth-rate model so that the resulting
map tells a plausible and pedagogically useful story: rural/coastal districts
age and grow faster than urban ones (broadly consistent with real ONS
sub-national projection trends for Devon), with South Hams - and the LSOAs
around Kingsbridge in particular - growing fastest of all, reflecting
retirement in-migration to that coastal area. This is deliberately engineered
so that Kingsbridge, which is not the standout choice under current demand,
becomes a much stronger candidate site under projected demand.

Re-run with `uv run python data/generate_projected_demand.py` to regenerate.
"""

import geopandas as gpd
import numpy as np
import pandas as pd

RNG_SEED = 2036

# Cumulative 10-year growth (2026 -> 2036) in the 50-84 population, by district.
# Urban districts (Plymouth, Exeter) grow slowest; rural/coastal districts grow
# fastest, reflecting an ageing-in-place and retirement in-migration pattern.
DISTRICT_GROWTH_50_84 = {
    "Plymouth": 0.06,
    "Exeter": 0.09,
    "Torbay": 0.13,
    "Mid Devon": 0.14,
    "Torridge": 0.14,
    "North Devon": 0.15,
    "West Devon": 0.15,
    "Teignbridge": 0.16,
    "East Devon": 0.17,
    "South Hams": 0.22,
}

# Total (all-age) population growth is assumed to run at ~45% of the 50-84
# growth rate in the same LSOA - this is specifically an older-age growth
# story, not a general population/housing boom.
TOTAL_GROWTH_FACTOR = 0.45

# Extra boost applied on top of the district rate for LSOAs close to
# Kingsbridge, representing concentrated retirement in-migration to that
# specific coastal/rural pocket of South Hams.
KINGSBRIDGE_SITE = {"Latitude": 50.285124062275806, "Longitude": -3.777670225836845}
KINGSBRIDGE_RADIUS_KM = 12
KINGSBRIDGE_EXTRA_GROWTH = 0.18

# Per-LSOA random noise (uniform, +/- this fraction) layered on top of the
# district/hotspot rate so the map doesn't look artificially uniform.
NOISE_FRACTION = 0.03


def main():
    demand_df = pd.read_csv("data/demand_MF_50_84.csv")
    devon_gdf = gpd.read_file("data/LSOA_Devon_2021_EW_BSC_V4.gpkg")

    full = devon_gdf.merge(
        demand_df, left_on="LSOA21NM", right_on="LSOA 2021 Name"
    ).to_crs("EPSG:27700")

    kingsbridge_point = gpd.GeoSeries(
        gpd.points_from_xy([KINGSBRIDGE_SITE["Longitude"]], [KINGSBRIDGE_SITE["Latitude"]]),
        crs="EPSG:4326",
    ).to_crs("EPSG:27700").iloc[0]

    # Per-LSOA attributes computed from the geography, keyed by LSOA code so they
    # can be safely realigned to demand_df's row order (merge() above does NOT
    # preserve demand_df's row order - it follows devon_gdf's).
    attrs = pd.DataFrame(
        {
            "LSOA 2021 Code": full["LSOA 2021 Code"],
            "district": full["LSOA 2021 Name"]
            .str.extract(r"^([A-Za-z ]+?)\s*\d")[0]
            .str.strip(),
            "dist_to_kingsbridge_km": full.geometry.centroid.distance(kingsbridge_point)
            / 1000,
        }
    ).set_index("LSOA 2021 Code")
    attrs = attrs.loc[demand_df["LSOA 2021 Code"]].reset_index(drop=True)

    rng = np.random.default_rng(RNG_SEED)
    noise = rng.uniform(-NOISE_FRACTION, NOISE_FRACTION, size=len(demand_df))

    base_growth = attrs["district"].map(DISTRICT_GROWTH_50_84)
    if base_growth.isna().any():
        missing = attrs["district"][base_growth.isna()].unique()
        raise ValueError(f"No growth rate defined for district(s): {missing}")

    kingsbridge_boost = np.where(
        attrs["dist_to_kingsbridge_km"] <= KINGSBRIDGE_RADIUS_KM,
        KINGSBRIDGE_EXTRA_GROWTH,
        0.0,
    )

    growth_50_84 = base_growth.to_numpy() + kingsbridge_boost + noise
    growth_total = growth_50_84 * TOTAL_GROWTH_FACTOR

    projected = demand_df.copy()
    projected["Total"] = np.round(demand_df["Total"] * (1 + growth_total)).astype(int)
    projected["F50-84"] = np.round(demand_df["F50-84"] * (1 + growth_50_84)).astype(int)
    projected["M50-84"] = np.round(demand_df["M50-84"] * (1 + growth_50_84)).astype(int)
    projected["MF50-84"] = projected["F50-84"] + projected["M50-84"]

    projected["F50-84 Percentage of Total LSOA Population"] = round(
        (projected["F50-84"] / projected["Total"]) * 100, 1
    )
    projected["M50-84 Percentage of Total LSOA Population"] = round(
        (projected["M50-84"] / projected["Total"]) * 100, 1
    )
    projected["MF50-84 Percentage of Total LSOA Population"] = round(
        (projected["MF50-84"] / projected["Total"]) * 100, 1
    )

    projected = projected[demand_df.columns]

    output_path = "data/demand_MF_50_84_projected_2036.csv"
    projected.to_csv(output_path, index=False)
    print(f"Wrote {output_path} ({len(projected)} rows)")

    growth_pct = (projected["MF50-84"].sum() / demand_df["MF50-84"].sum() - 1) * 100
    print(f"Devon-wide MF50-84 growth: {growth_pct:.1f}%")


if __name__ == "__main__":
    main()
