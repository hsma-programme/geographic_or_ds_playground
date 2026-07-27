from app.utils import (
    create_demand_gdf,
    create_deprivation_gdf,
    create_projected_demand_gdf,
    load_devon_sites,
    load_devon_sites_with_utilisation,
    load_population_weighted_centroids,
    setup_lokigi_site_problem_utilisation,
)
import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd


###########################
# MARK: Helpers
###########################
def add_sites_to_map(m, sites_gdf, add_centroids=False, centroid_gdf=None):
    existing_sites = sites_gdf[sites_gdf["Existing"] == "Yes"]
    proposed_sites = sites_gdf[sites_gdf["Existing"] == "No"]

    existing_group = folium.FeatureGroup(name="Existing CDCs")
    proposed_group = folium.FeatureGroup(name="Proposed CDCs")

    for _, row in existing_sites.iterrows():
        folium.Marker(
            location=[row.geometry.y, row.geometry.x],
            popup=row["Facility_Name"],
            tooltip=row["Facility_Name"],
            icon=folium.Icon(
                icon="plus",
                prefix="fa",
                color="red",
            ),
        ).add_to(existing_group)

    for _, row in proposed_sites.iterrows():
        folium.Marker(
            location=[row.geometry.y, row.geometry.x],
            popup=row["Facility_Name"],
            tooltip=row["Facility_Name"],
            icon=folium.Icon(
                icon="plus",
                prefix="fa",
                color="blue",
            ),
        ).add_to(proposed_group)

    existing_group.add_to(m)
    proposed_group.add_to(m)

    if add_centroids:
        centroids = folium.FeatureGroup(name="Centroids")
        centroid_gdf = centroid_gdf.to_crs("EPSG:4326")

        for _, row in centroid_gdf.iterrows():
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x], color="white", radius=3
            ).add_to(centroids)

        centroids.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    return m


def add_site_legend(m):
    legend_html = """
    <div class="site-maplegend" style="
        position: fixed;
        bottom: 50px;
        left: 50px;
        width: 180px;
        background-color: white;
        border: 2px solid grey;
        z-index: 9999;
        font-size: 14px;
        padding: 10px;
    ">
    <b>CDC Sites</b><br>

    <i class="fa fa-plus" style="color:red"></i>
    Existing CDC<br>

    <i class="fa fa-plus" style="color:blue"></i>
    Proposed CDC
    </div>
    """

    m.get_root().html.add_child(folium.Element(legend_html))

    m.get_root().header.add_child(
        folium.Element("""
        <style>
        .site-maplegend {
            color: black !important;
        }
        </style>
        """)
    )

    return m


###########################
# MARK: Deprivation
###########################
def render_deprivation_map():
    deprivation_gdf = create_deprivation_gdf()
    sites_gdf = load_devon_sites()

    # Create choropleth
    m = deprivation_gdf.explore(
        column="Index of Multiple Deprivation (IMD) Decile (where 1 is most deprived 10% of LSOA",
        tooltip=[
            "LSOA21NM",
            "Index of Multiple Deprivation (IMD) Decile (where 1 is most deprived 10% of LSOA",
        ],
        tooltip_kwds={
            "aliases": [
                "Area:",
                "IMD Decile (1 = most deprived):",
            ],
            "labels": True,
            "sticky": False,
        },
        legend_kwds={"caption": "IMD Decile (1 = most deprived)"},
        cmap="cividis_r",
        # scheme="UserDefined",
        categorical=True,
        name="IMD Deciles",
        # classification_kwds={"bins": [1, 2, 3, 4, 5, 6, 7, 8, 9]},
    )

    # Workaround for legend colours
    m.get_root().header.add_child(
        folium.Element("""
        <style>
        .legend-labels {
            color: black !important;
        }

        .legend-title {
            color: black !important;
        }
        </style>
        """)
    )

    # Add point layer
    m = add_sites_to_map(m, sites_gdf=sites_gdf)
    m = add_site_legend(m)

    return st_folium(m, use_container_width=True)


###########################
# MARK: Demand
###########################
def render_demand_map():
    demand_gdf = create_demand_gdf()
    sites_gdf = load_devon_sites()

    raw_options = ["MF50-84", "Total"]

    alias_dict = {
        "MF50-84": "Per-LSOA Population - Between 50 and 84",
        "Total": "Total Per-LSOA Population",
    }

    selected_age_range = st.radio(
        "Select Age Range to Visualise",
        raw_options,
        format_func=lambda x: alias_dict.get(x, x),
        index=0,
    )
    # Create choropleth
    m = demand_gdf.explore(
        column=selected_age_range,
        tooltip=[
            "LSOA21NM",
            selected_age_range,
            "Total",
        ],
        tooltip_kwds={
            "aliases": [
                "Area:",
                "Expected Demand:",
                "Total Population:",
            ],
            "labels": True,
            "sticky": False,
        },
        name="Population",
        zoom_start=9,
        scheme="Percentiles",
    )

    # Add point layer
    m = add_sites_to_map(m, sites_gdf=sites_gdf)
    m = add_site_legend(m)
    for child in m._children.values():
        if child == "color_scale" or hasattr(child, "caption"):
            # Default is usually ~450px. Let's make it thinner/wider:
            child.width = 800

    return st_folium(m, use_container_width=True)


###########################
# MARK: Projected Demand
###########################
def render_projected_demand_map():
    projected_gdf = create_projected_demand_gdf()
    sites_gdf = load_devon_sites()

    raw_options = ["MF50-84 Growth (%)", "MF50-84", "Total"]

    alias_dict = {
        "MF50-84 Growth (%)": "Projected Growth 2026-2036 (%)",
        "MF50-84": "Projected Per-LSOA Population in 2036 - Between 50 and 84",
        "Total": "Projected Total Per-LSOA Population in 2036",
    }

    selected_metric = st.radio(
        "Select Metric to Visualise",
        raw_options,
        format_func=lambda x: alias_dict.get(x, x),
        index=0,
    )

    other_column_aliases = {
        "MF50-84": "Projected 50-84 Population (2036):",
        "Total": "Projected Total Population (2036):",
    }
    tooltip_columns = ["LSOA21NM", selected_metric]
    tooltip_aliases = ["Area:", f"{alias_dict.get(selected_metric, selected_metric)}:"]
    for column, alias in other_column_aliases.items():
        if column not in tooltip_columns:
            tooltip_columns.append(column)
            tooltip_aliases.append(alias)

    # Create choropleth
    m = projected_gdf.explore(
        column=selected_metric,
        tooltip=tooltip_columns,
        tooltip_kwds={
            "aliases": tooltip_aliases,
            "labels": True,
            "sticky": False,
        },
        name="Projected Population",
        zoom_start=9,
        scheme="Percentiles",
    )

    # Add point layer
    m = add_sites_to_map(m, sites_gdf=sites_gdf)
    m = add_site_legend(m)
    for child in m._children.values():
        if child == "color_scale" or hasattr(child, "caption"):
            # Default is usually ~450px. Let's make it thinner/wider:
            child.width = 800

    return st_folium(m, use_container_width=True)


###########################
# MARK: Utilisation
###########################
# Utilisation is a site-level metric (how full each existing CDC is today),
# not a per-LSOA choropleth, so unlike the other maps this one draws no region
# layer - just the sites on a plain basemap, mirroring lokigi's
# plot_site_utilisation(). Existing CDCs are coloured/sized by utilisation
# (green = spare capacity, red = at/over capacity, following lokigi's RdYlGn_r
# convention); proposed CDCs stay blue so they remain clickable for the site
# selection at the bottom of the page.
_UTIL_COLOUR_MIN = 0.5  # <=50% used -> full green
_UTIL_COLOUR_MAX = 1.0  # >=100% used -> full red (over-capacity clips to red)


def _utilisation_style(ratio):
    """Return (hex colour, marker radius) for a utilisation ratio, using the
    same green->red reading as lokigi: low ratio = green + small, high (bad)
    ratio = red + large so over-capacity sites stand out."""
    import matplotlib
    from matplotlib.colors import Normalize, to_hex

    norm = Normalize(vmin=_UTIL_COLOUR_MIN, vmax=_UTIL_COLOUR_MAX)
    cmap = matplotlib.colormaps["RdYlGn_r"]
    t = min(max(norm(ratio), 0.0), 1.0)  # clip into [0, 1]
    colour = to_hex(cmap(t))
    radius = 12 + t * 16  # 12px (green) -> 28px (red)
    return colour, radius


def render_utilisation_map():
    problem = setup_lokigi_site_problem_utilisation()
    summary = problem.site_utilisation_summary().sort_values(
        "utilisation_ratio", ascending=False
    )

    sites_gdf = load_devon_sites_with_utilisation()
    existing_sites = sites_gdf[sites_gdf["Existing"] == "Yes"]
    proposed_sites = sites_gdf[sites_gdf["Existing"] == "No"]

    # Centre roughly on Devon; fit to the sites afterwards.
    m = folium.Map(location=[50.72, -3.8], zoom_start=9, tiles="cartodbpositron")

    existing_group = folium.FeatureGroup(name="Existing CDCs (utilisation)")
    proposed_group = folium.FeatureGroup(name="Proposed CDCs")

    for _, row in existing_sites.iterrows():
        ratio = summary.loc[row["Facility_Name"], "utilisation_ratio"]
        capacity = int(summary.loc[row["Facility_Name"], "capacity"])
        caseload = int(summary.loc[row["Facility_Name"], "current_load"])
        headroom = int(summary.loc[row["Facility_Name"], "headroom"])
        colour, radius = _utilisation_style(ratio)

        over = headroom < 0
        headroom_line = (
            f"<b style='color:#b2182b'>Over capacity by {abs(headroom)}/week</b>"
            if over
            else f"Spare capacity: {headroom}/week"
        )
        popup_html = (
            f"<b>{row['Facility_Name']}</b><br>"
            f"Weekly capacity: {capacity}<br>"
            f"Weekly caseload: {caseload}<br>"
            f"Utilisation: <b>{ratio * 100:.0f}%</b><br>"
            f"{headroom_line}"
        )

        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=radius,
            color="#333333",
            weight=1,
            fill=True,
            fill_color=colour,
            fill_opacity=0.85,
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=f"{row['Facility_Name']}: {ratio * 100:.0f}% utilised",
        ).add_to(existing_group)

    for _, row in proposed_sites.iterrows():
        folium.Marker(
            location=[row.geometry.y, row.geometry.x],
            popup=row["Facility_Name"],
            tooltip=row["Facility_Name"],
            icon=folium.Icon(icon="plus", prefix="fa", color="blue"),
        ).add_to(proposed_group)

    existing_group.add_to(m)
    proposed_group.add_to(m)

    # Frame the map on all sites.
    bounds = sites_gdf.total_bounds  # [minx, miny, maxx, maxy]
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

    m = _add_utilisation_legend(m)
    folium.LayerControl(collapsed=False).add_to(m)

    # Side-by-side: how full the centres are (left) vs. where the underlying
    # regional demand sits (right), so the two can be read against each other.
    col_util, col_demand = st.columns(2)

    with col_util:
        st.markdown("**How full is each existing CDC today?**")
        # This is the selection map: its clickable proposed (blue) sites drive
        # the site choice at the bottom of the page, so its result is returned.
        result = st_folium(m, use_container_width=True, key="utilisation_map")

    with col_demand:
        st.markdown("**Where is the regional demand? (population aged 50-84)**")
        demand_m = _build_regional_demand_map()
        st_folium(demand_m, use_container_width=True, key="utilisation_demand_map")
        st.caption(
            "Darker areas have more people aged 50-84 - the group most likely to "
            "need CDC services. The white markers are for reference only; make your "
            "site choice on the left-hand map."
        )

    # View the numbers behind the utilisation map (site_utilisation_summary()).
    display = summary.reset_index().rename(
        columns={
            "site": "CDC",
            "capacity": "Weekly capacity",
            "current_load": "Weekly caseload",
            "utilisation_ratio": "Utilisation",
            "headroom": "Spare capacity / week",
        }
    )
    display["Utilisation"] = (display["Utilisation"] * 100).round(0).astype(int).astype(
        str
    ) + "%"
    st.markdown("**Utilisation of each existing CDC**")
    st.dataframe(display, hide_index=True, use_container_width=True)
    st.caption(
        "Utilisation = weekly caseload ÷ weekly capacity."
        "A value over 100% means the site is running beyond its planned capacity."
    )

    return result


def _build_regional_demand_map():
    """Compact demand choropleth (population aged 50-84 per LSOA) with the
    existing/proposed CDCs overlaid, for the utilisation page's second column.
    Mirrors render_demand_map() but with no age-range toggle and returns the
    folium map instead of calling st_folium (the caller renders it)."""
    demand_gdf = create_demand_gdf()

    demand_m = demand_gdf.explore(
        column="MF50-84",
        tooltip=["LSOA21NM", "MF50-84", "Total"],
        tooltip_kwds={
            "aliases": [
                "Area:",
                "Population 50-84:",
                "Total population:",
            ],
            "labels": True,
            "sticky": False,
        },
        name="Population 50-84",
        zoom_start=9,
        scheme="Percentiles",
    )

    # Sites here are context only - existing CDCs white, proposed CDCs grey (both
    # deliberately clear of the green->red utilisation ramp on the left map) so it
    # reads as "you can't pick here". Site selection happens on the left map.
    sites_gdf = load_devon_sites()
    reference_group = folium.FeatureGroup(name="CDCs (reference only)")
    for _, row in sites_gdf.iterrows():
        existing = row["Existing"] == "Yes"
        folium.Marker(
            location=[row.geometry.y, row.geometry.x],
            popup=row["Facility_Name"],
            tooltip=f"{row['Facility_Name']} — choose your site on the left-hand map",
            # Dark glyph so the white (existing) pin stays legible over the choropleth.
            icon=folium.Icon(
                icon="plus",
                prefix="fa",
                color="white" if existing else "gray",
                icon_color="#333333",
            ),
        ).add_to(reference_group)
    reference_group.add_to(demand_m)

    demand_m = _add_reference_site_legend(demand_m)
    folium.LayerControl(collapsed=False).add_to(demand_m)

    return demand_m


def _add_reference_site_legend(m):
    legend_html = """
    <div class="ref-maplegend" style="
        position: fixed;
        bottom: 50px;
        left: 50px;
        width: 200px;
        background-color: white;
        border: 2px solid grey;
        z-index: 9999;
        font-size: 14px;
        padding: 10px;
    ">
    <b>CDC sites</b><br>
    <span style="display:inline-block;width:12px;height:12px;background:white;
    border:1px solid #777;vertical-align:middle;"></span> Existing CDC<br>
    <span style="display:inline-block;width:12px;height:12px;background:gray;
    border:1px solid #777;vertical-align:middle;"></span> Proposed CDC<br>
    <span style="font-size:11px;color:#555;">Shown for reference only —
    choose your site on the left-hand map.</span>
    </div>
    """

    m.get_root().html.add_child(folium.Element(legend_html))
    m.get_root().header.add_child(
        folium.Element("""
        <style>
        .ref-maplegend { color: black !important; }
        </style>
        """)
    )

    return m


def _add_utilisation_legend(m):
    legend_html = """
    <div class="util-maplegend" style="
        position: fixed;
        bottom: 50px;
        left: 50px;
        width: 210px;
        background-color: white;
        border: 2px solid grey;
        z-index: 9999;
        font-size: 14px;
        padding: 10px;
    ">
    <b>CDC Utilisation</b><br>
    <span style="display:inline-block;width:12px;height:12px;border-radius:50%;
        background:#1a9850;border:1px solid #333;"></span>
    Spare capacity (&le;50%)<br>
    <span style="display:inline-block;width:12px;height:12px;border-radius:50%;
        background:#fee08b;border:1px solid #333;"></span>
    Getting busy (~75%)<br>
    <span style="display:inline-block;width:12px;height:12px;border-radius:50%;
        background:#d73027;border:1px solid #333;"></span>
    At / over capacity (&ge;100%)<br>
    <span style="margin-top:4px;display:inline-block;"></span>
    <i class="fa fa-plus" style="color:blue"></i> Proposed CDC
    <br><span style="font-size:11px;color:#555;">Larger circle = busier site</span>
    </div>
    """

    m.get_root().html.add_child(folium.Element(legend_html))
    m.get_root().header.add_child(
        folium.Element("""
        <style>
        .util-maplegend { color: black !important; }
        </style>
        """)
    )

    return m


###########################
# MARK: Travel
###########################
def render_travel_existing_map(best_solution_gdf, what, threshold=None):

    sites_gdf = load_devon_sites()

    centroids = load_population_weighted_centroids()

    if what == "time":
        column = "min_cost"
        name = "Travel Time (Minutes)"
        legend_kwds = {"caption": "Travel Time (Minutes)"}
        cmap = None
    elif what == "centre":
        column = "selected_site"
        name = "Nearest Site"
        legend_kwds = {"caption": "Nearest Site to LSOA"}
        cmap = None
    if what == "threshold":
        if threshold is None:
            raise ValueError("No threshold defined")
        else:
            best_solution_gdf["exceeds_threshold"] = (
                best_solution_gdf["min_cost"] > threshold
            ).map({True: "Yes", False: "No"})

            best_solution_gdf["exceeds_threshold"] = pd.Categorical(
                best_solution_gdf["exceeds_threshold"],
                categories=["No", "Yes"],
                ordered=True,
            )
            column = "exceeds_threshold"
            name = "Exceeds threshold time"
            legend_kwds = {"caption": f"Exceeds travel time of {threshold} minutes"}
            cmap = {
                "Yes": "#ef8a62",  # soft red/orange
                "No": "#67a9cf",  # soft blue
            }

            from matplotlib.colors import ListedColormap

            cmap = ListedColormap(["#67a9cf", "#ef8a62"])

    m = best_solution_gdf.round(1).explore(
        column=column,
        tooltip=["LSOA21NM", "min_cost", "selected_site"],
        tooltip_kwds={
            "aliases": [
                "Area:",
                "Travel time to nearest site (minutes):",
                "Nearest site:",
            ],
            "labels": True,
            "sticky": False,
        },
        name=name,
        zoom_start=9,
        legend_kwds=legend_kwds,
        cmap=cmap,
    )

    if what == "centre" or what == "threshold":
        # Workaround for legend colours
        m.get_root().header.add_child(
            folium.Element("""
            <style>
            .legend-labels {
                color: black !important;
            }

            .legend-title {
                color: black !important;
            }
            </style>
            """)
        )

    # Add point layer
    m = add_sites_to_map(
        m,
        sites_gdf=sites_gdf,
        # Can turn centroids back on for debugging purposes if needed
        centroid_gdf=centroids,
        add_centroids=False,
    )
    m = add_site_legend(m)
    for child in m._children.values():
        if child == "color_scale" or hasattr(child, "caption"):
            # Default is usually ~450px. Let's make it thinner/wider:
            child.width = 800

    return st_folium(m, use_container_width=True)


def render_travel_maps(best_solution_gdf):
    map_selection = st.radio(
        "Select map type",
        [
            "Show travel time",
            "Show nearest centre",
            "Show regions exceeding a certain travel time",
        ],
    )

    if map_selection == "Show travel time":
        return render_travel_existing_map(best_solution_gdf, what="time")
    elif map_selection == "Show nearest centre":
        return render_travel_existing_map(best_solution_gdf, what="centre")
    elif map_selection == "Show regions exceeding a certain travel time":
        threshold = st.slider(
            label="Choose a maximum travel time",
            min_value=15,
            max_value=60,
            value=45,
            step=5,
        )
        return render_travel_existing_map(
            best_solution_gdf, what="threshold", threshold=threshold
        )


###########################
# MARK: Hotspots (shared)
###########################
# lokigi's own get_hotspots() classifications, coloured by convention. Each pair
# of variables is combined offline (data/generate_*hotspots.py) into a single
# GeoDataFrame; here we just draw it, mirroring the other .explore()-based maps
# so it renders reliably in st_folium. The priority typology and the statistical
# clusters are two views of the same precomputed data, shared across every
# hotspot page.
_DEMAND_DEPRIVATION_TYPOLOGY_COLOURS = {
    "High Demand / High Deprivation": "#d7191c",  # priority - act here first
    "High Demand / Low Deprivation": "#fdae61",  # worth watching
    "Low Demand / High Deprivation": "#fdae61",  # worth watching
    "Low Demand / Low Deprivation": "#bdbdbd",  # baseline
}

_DEMAND_TRAVEL_TYPOLOGY_COLOURS = {
    "High Demand / Poor Access": "#d7191c",  # priority - act here first
    "High Demand / Good Access": "#fdae61",  # worth watching
    "Low Demand / Poor Access": "#fdae61",  # worth watching
    "Low Demand / Good Access": "#bdbdbd",  # baseline
}

_DEPRIVATION_TRAVEL_TYPOLOGY_COLOURS = {
    "High Deprivation / Poor Access": "#d7191c",  # priority - act here first
    "High Deprivation / Good Access": "#fdae61",  # worth watching
    "Low Deprivation / Poor Access": "#fdae61",  # worth watching
    "Low Deprivation / Good Access": "#bdbdbd",  # baseline
}

_CLUSTER_COLOURS = {
    "Hotspot": "#d7191c",  # high-high
    "High-Low Outlier": "#fee08b",
    "Low-High Outlier": "#abd9e9",
    "Coldspot": "#2c7bb6",  # low-low
    "Not Significant": "#bdbdbd",
}


def _render_hotspots_map(
    hotspots_gdf, what, typology_colours, typology_alias, typology_caption
):
    from matplotlib.colors import ListedColormap

    sites_gdf = load_devon_sites()

    if what == "typology":
        colour_map = typology_colours
        column = "attribute_typology"
        tooltip = ["LSOA21NM", "attribute_typology", "combined_score"]
        aliases = ["Area:", typology_alias, "Combined priority score:"]
        caption = typology_caption
    else:  # "clusters"
        colour_map = _CLUSTER_COLOURS
        column = "cluster_type"
        tooltip = ["LSOA21NM", "cluster_type", "p_value"]
        aliases = ["Area:", "Cluster type:", "p-value:"]
        caption = "Local Moran's I cluster"

    # .copy() because hotspots_gdf is a cached object reused across fragment reruns.
    gdf = hotspots_gdf.copy()

    # Keep only categories actually present, in the fixed order above, so the
    # ListedColormap lines up with the categorical values.
    present = [c for c in colour_map if c in set(gdf[column].dropna().unique())]
    gdf[column] = pd.Categorical(gdf[column], categories=present, ordered=True)
    cmap = ListedColormap([colour_map[c] for c in present])

    m = gdf.round(3).explore(
        column=column,
        categorical=True,
        cmap=cmap,
        tooltip=tooltip,
        tooltip_kwds={
            "aliases": aliases,
            "labels": True,
            "sticky": False,
        },
        name="Hotspots",
        zoom_start=9,
        legend_kwds={"caption": caption},
    )

    # Workaround for legend colours (same as the deprivation map)
    m.get_root().header.add_child(
        folium.Element("""
        <style>
        .legend-labels {
            color: black !important;
        }

        .legend-title {
            color: black !important;
        }
        </style>
        """)
    )

    m = add_sites_to_map(m, sites_gdf=sites_gdf)
    m = add_site_legend(m)

    return st_folium(m, use_container_width=True)


def _hotspots_view(typology_label):
    """Shared radio toggle between the priority typology and the statistical
    clusters. Returns "typology" or "clusters"."""
    map_selection = st.radio(
        "Select map type",
        [typology_label, "Statistical hotspots (Local Moran's I)"],
    )
    return "typology" if map_selection == typology_label else "clusters"


###########################
# MARK: Demand & Deprivation Hotspots
###########################
def render_demand_deprivation_hotspots_maps(hotspots_gdf):
    what = _hotspots_view("Priority typology (demand × deprivation)")
    return _render_hotspots_map(
        hotspots_gdf,
        what,
        _DEMAND_DEPRIVATION_TYPOLOGY_COLOURS,
        typology_alias="Demand / Deprivation:",
        typology_caption="Demand × Deprivation priority",
    )


###########################
# MARK: Demand & Travel Hotspots
###########################
def render_demand_travel_hotspots_maps(hotspots_gdf):
    what = _hotspots_view("Priority typology (demand × access)")
    return _render_hotspots_map(
        hotspots_gdf,
        what,
        _DEMAND_TRAVEL_TYPOLOGY_COLOURS,
        typology_alias="Demand / Access:",
        typology_caption="Demand × Access priority",
    )


###########################
# MARK: Deprivation & Travel Hotspots
###########################
def render_deprivation_travel_hotspots_maps(hotspots_gdf):
    what = _hotspots_view("Priority typology (deprivation × access)")
    return _render_hotspots_map(
        hotspots_gdf,
        what,
        _DEPRIVATION_TRAVEL_TYPOLOGY_COLOURS,
        typology_alias="Deprivation / Access:",
        typology_caption="Deprivation × Access priority",
    )


###############################
# MARK: Site selection wrapper
###############################
def make_selection_map(map_render_fn, key_suffix):
    @st.fragment
    def selection_map():
        confirmed_key = f"confirmed_site_{key_suffix}"
        submitted_key = f"site_submitted_{key_suffix}"

        if st.session_state[submitted_key]:
            st.info(
                f"You have submitted a site recommendation based on {key_suffix} "
                f"({st.session_state[confirmed_key]['Site']})."
                "\n\nPlease use the buttons below to request your next analysis."
            )
            return

        st_data = map_render_fn()

        st.write("From just the evidence on this page, which site would you choose?")

        all_sites = load_devon_sites()
        existing_sites = all_sites[all_sites["Existing"] == "Yes"][
            "Facility_Name"
        ].to_list()

        selected_site = st_data["last_object_clicked_popup"]

        if selected_site is None:
            st.warning(
                "Click on a blue candidate site on the map above to make your selection."
            )
            # Reset confirmation if no site is selected
            st.session_state[confirmed_key] = None
        elif selected_site in existing_sites:
            st.error(
                "Cannot select an existing site. Please click on a proposed site (the blue markers)."
            )
            st.session_state[confirmed_key] = None
        else:
            st.success(f"Selected Site = {selected_site}")
            st.session_state[confirmed_key] = {
                "What": key_suffix.capitalize(),
                "Site": selected_site,
            }

        button = st.button(
            "Click here to confirm your site choice",
            disabled=True
            if (
                st.session_state[confirmed_key] is None
                or st.session_state[submitted_key]
            )
            else False,
            key=f"confirm_button_{key_suffix}",
        )

        if not button:
            st.write("")
            st.write("")

        if button:
            st.session_state[submitted_key] = True
            st.rerun()

    return selection_map
