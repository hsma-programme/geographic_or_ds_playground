from pathlib import Path
import streamlit as st
from functools import partial
from app.utils import (
    render_navigation,
    write_terminal_html,
    page_styling,
    load_demand_deprivation_hotspots,
    render_prior_choice_recap,
)
from app.utils_investigations import HOTSPOTS_DEMAND_DEPRIVATION
from app.maps import render_demand_deprivation_hotspots_maps, make_selection_map

st.set_page_config(initial_sidebar_state="expanded", layout="wide")
page_styling()

st.title("Demand & Deprivation Hotspots")

hotspots_gdf = load_demand_deprivation_hotspots()

intro_text = """
> Your analyst has combined demand and deprivation into one map. On its own, a busy area or a deprived area is only half the story - what matters is the places that are *both*.
<br><br>
> Red areas are high on both. Grey areas are high on only one, or middling on both: worth a second look, not a five-alarm fire. The "statistical hotspots" view is fussier still - it only lights up clusters that are unlikely to be down to chance.
<br><br>
> They mutter something about "Moran's I" and "spatial autocorrelation", notice you have stopped listening, and retreat to the safety of their spreadsheet.
"""

# Once a decision has been made on this page, drop the analyst intro so a
# revisit shows just the evidence and outcome.
if not st.session_state.site_submitted_demand_deprivation_hotspots:
    write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/demand_deprivation_hotspots.html",
    )
    st.iframe(
        Path("app/assets/terminal_working/demand_deprivation_hotspots.html"),
        height=275,
    )
    render_prior_choice_recap(HOTSPOTS_DEMAND_DEPRIVATION)

hotspots_selection_map = make_selection_map(
    partial(render_demand_deprivation_hotspots_maps, hotspots_gdf),
    "demand_deprivation_hotspots",
)
hotspots_selection_map()

if st.session_state.site_submitted_demand_deprivation_hotspots:
    render_navigation(HOTSPOTS_DEMAND_DEPRIVATION)
