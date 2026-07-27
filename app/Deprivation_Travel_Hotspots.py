import streamlit as st
from functools import partial
from app.utils import (
    render_navigation,
    write_terminal_html,
    page_styling,
    load_deprivation_travel_hotspots,
    render_notes_textbox,
)
from app.utils_investigations import HOTSPOTS_DEPRIVATION_TRAVEL
from app.maps import render_deprivation_travel_hotspots_maps, make_selection_map

st.set_page_config(initial_sidebar_state="collapsed", layout="wide")
page_styling()

st.title("Deprivation & Travel Hotspots")

hotspots_gdf = load_deprivation_travel_hotspots()

intro_text = """
> Your analyst has combined two of the maps you have already seen - how deprived each area is, and how long it takes to drive to the nearest existing CDC.
<br><br>
> They remind you that people in more deprived areas already face worse outcomes and lower screening uptake. Adding a long, awkward journey on top of that is exactly the sort of double disadvantage a fair service is meant to avoid.
<br><br>
> They tell you to use the buttons above the map to switch views. "Priority typology" colours every area by whether it is high or low on deprivation and on access - the red areas are highly deprived *and* have poor access. "Statistical hotspots" only lights up clusters of deprived, poorly-served areas that are unlikely to be down to chance.
<br><br>
> They remind you that you can still hover over the red and blue markers to see the CDCs, and click a blue one to make your recommendation.
<br><br>
> They note that access here is again measured to the *existing* four CDCs - a new site could ease the burden on the areas that can least absorb it.
"""

# Once a decision has been made on this page, drop the analyst intro so a
# revisit shows just the evidence and outcome.
if not st.session_state.site_submitted_deprivation_travel_hotspots:
    write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/deprivation_travel_hotspots.html",
    )
    st.iframe(
        "app/assets/terminal_working/deprivation_travel_hotspots.html", height=375
    )

hotspots_selection_map = make_selection_map(
    partial(render_deprivation_travel_hotspots_maps, hotspots_gdf),
    "deprivation_travel_hotspots",
)
hotspots_selection_map()

render_notes_textbox()

if st.session_state.site_submitted_deprivation_travel_hotspots:
    render_navigation(HOTSPOTS_DEPRIVATION_TRAVEL)
