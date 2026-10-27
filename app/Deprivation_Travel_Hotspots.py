from pathlib import Path
import streamlit as st
from functools import partial
from app.utils import (
    render_navigation,
    write_terminal_html,
    page_styling,
    load_deprivation_travel_hotspots,
    render_prior_choice_recap,
)
from app.utils_investigations import HOTSPOTS_DEPRIVATION_TRAVEL
from app.maps import render_deprivation_travel_hotspots_maps, make_selection_map

st.set_page_config(initial_sidebar_state="expanded", layout="wide")
page_styling()

st.title("Deprivation & Travel Hotspots")

hotspots_gdf = load_deprivation_travel_hotspots()

intro_text = """
> Your analyst has combined deprivation with car travel time to today's four CDCs. People in deprived areas already face worse outcomes and lower screening uptake - a long, awkward journey on top is exactly the double disadvantage a fair service is meant to avoid.
<br><br>
> Red areas are highly deprived *and* poorly served. Grey areas have only one of the two: worth watching, not the worst case. The "statistical hotspots" view only lights up clusters unlikely to be down to chance.
"""

# Once a decision has been made on this page, drop the analyst intro so a
# revisit shows just the evidence and outcome.
if not st.session_state.site_submitted_deprivation_travel_hotspots:
    write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/deprivation_travel_hotspots.html",
    )
    st.iframe(
        Path("app/assets/terminal_working/deprivation_travel_hotspots.html"),
        height=225,
    )
    render_prior_choice_recap(HOTSPOTS_DEPRIVATION_TRAVEL)

hotspots_selection_map = make_selection_map(
    partial(render_deprivation_travel_hotspots_maps, hotspots_gdf),
    "deprivation_travel_hotspots",
)
hotspots_selection_map()

if st.session_state.site_submitted_deprivation_travel_hotspots:
    render_navigation(HOTSPOTS_DEPRIVATION_TRAVEL)
