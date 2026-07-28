import streamlit as st
from functools import partial
from app.utils import (
    render_navigation,
    write_terminal_html,
    page_styling,
    load_demand_travel_hotspots,
)
from app.utils_investigations import HOTSPOTS_DEMAND_TRAVEL
from app.maps import render_demand_travel_hotspots_maps, make_selection_map

st.set_page_config(initial_sidebar_state="expanded", layout="wide")
page_styling()

st.title("Demand & Travel Hotspots")

hotspots_gdf = load_demand_travel_hotspots()

intro_text = """
> Your analyst has combined two of the maps you have already seen - where the demand is, and how long it takes to drive to the nearest existing CDC.
<br><br>
> They explain that a long drive only really matters where lots of people need the service. An empty moor with a two-hour drive is less of a worry than a busy town that is still awkward to reach.
<br><br>
> They tell you to use the buttons above the map to switch views. "Priority typology" grades every area low, medium or high on demand and on access - only the areas with high demand *and* poor access show up red. An area with high demand but only middling access, or poor access but low demand, shows up grey: a mixed picture, not the worst case. "Statistical hotspots" only lights up clusters of high-demand, poor-access areas that are unlikely to be down to chance.
<br><br>
> They remind you that you can still hover over the red and blue markers to see the CDCs, and click a blue one to make your recommendation.
<br><br>
> They add, a little pointedly, that these travel times are to the *existing* four CDCs - the whole point of this exercise is to work out where a fifth might help most.
"""

# Once a decision has been made on this page, drop the analyst intro so a
# revisit shows just the evidence and outcome.
if not st.session_state.site_submitted_demand_travel_hotspots:
    write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/demand_travel_hotspots.html",
    )
    st.iframe("app/assets/terminal_working/demand_travel_hotspots.html", height=375)

hotspots_selection_map = make_selection_map(
    partial(render_demand_travel_hotspots_maps, hotspots_gdf),
    "demand_travel_hotspots",
)
hotspots_selection_map()

if st.session_state.site_submitted_demand_travel_hotspots:
    render_navigation(HOTSPOTS_DEMAND_TRAVEL)
