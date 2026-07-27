import streamlit as st
from functools import partial
from app.utils import (
    render_navigation,
    write_terminal_html,
    page_styling,
    load_demand_deprivation_hotspots,
    render_notes_textbox,
)
from app.utils_investigations import HOTSPOTS_DEMAND_DEPRIVATION
from app.maps import render_demand_deprivation_hotspots_maps, make_selection_map

st.set_page_config(initial_sidebar_state="collapsed", layout="wide")
page_styling()

st.title("Demand & Deprivation Hotspots")

hotspots_gdf = load_demand_deprivation_hotspots()

intro_text = """
> Your analyst has taken the two maps you asked for - demand and deprivation - and combined them into one.
<br><br>
> They explain that on their own, a busy area or a deprived area is only half the story. What you really want are the places that are *both*: high demand and high deprivation together.
<br><br>
> They tell you to use the buttons above the map to switch views. "Priority typology" colours every area by whether it is high or low on demand and on deprivation - the red areas are high on both. "Statistical hotspots" is fussier: it only lights up clusters that are unlikely to be down to chance.
<br><br>
> They remind you that you can still hover over the red and blue markers to see the CDCs, and click a blue one to make your recommendation.
<br><br>
> They mutter something about "Moran's I" and "spatial autocorrelation", notice you have stopped listening, and retreat to the safety of their spreadsheet.
"""

char_count, reveal_speed = write_terminal_html(
    intro_text,
    output_path="app/assets/terminal_working/demand_deprivation_hotspots.html",
)

st.iframe("app/assets/terminal_working/demand_deprivation_hotspots.html", height=375)

hotspots_selection_map = make_selection_map(
    partial(render_demand_deprivation_hotspots_maps, hotspots_gdf),
    "demand_deprivation_hotspots",
)
hotspots_selection_map()

render_notes_textbox()

if st.session_state.site_submitted_demand_deprivation_hotspots:
    render_navigation(HOTSPOTS_DEMAND_DEPRIVATION)
