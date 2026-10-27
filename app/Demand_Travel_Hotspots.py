from pathlib import Path
import streamlit as st
from functools import partial
from app.utils import (
    render_navigation,
    write_terminal_html,
    page_styling,
    load_demand_travel_hotspots,
    render_prior_choice_recap,
)
from app.utils_investigations import HOTSPOTS_DEMAND_TRAVEL
from app.maps import render_demand_travel_hotspots_maps, make_selection_map

st.set_page_config(initial_sidebar_state="expanded", layout="wide")
page_styling()

st.title("Demand & Travel Hotspots")

hotspots_gdf = load_demand_travel_hotspots()

intro_text = """
> Your analyst has combined demand with car travel time to today's four CDCs. A long drive only really matters where lots of people need the service: an empty moor with a two-hour drive is less of a worry than a busy town that is still awkward to reach.
<br><br>
> Red areas have high demand *and* poor access. Grey areas have only one of the two: a mixed picture, not the worst case. The "statistical hotspots" view only lights up clusters unlikely to be down to chance.
<br><br>
> They add, a little pointedly, that the whole point of this exercise is to work out where a fifth CDC might help most.
"""

# Once a decision has been made on this page, drop the analyst intro so a
# revisit shows just the evidence and outcome.
if not st.session_state.site_submitted_demand_travel_hotspots:
    write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/demand_travel_hotspots.html",
    )
    st.iframe(
        Path("app/assets/terminal_working/demand_travel_hotspots.html"), height=275
    )
    render_prior_choice_recap(HOTSPOTS_DEMAND_TRAVEL)

hotspots_selection_map = make_selection_map(
    partial(render_demand_travel_hotspots_maps, hotspots_gdf),
    "demand_travel_hotspots",
)
hotspots_selection_map()

if st.session_state.site_submitted_demand_travel_hotspots:
    render_navigation(HOTSPOTS_DEMAND_TRAVEL)
