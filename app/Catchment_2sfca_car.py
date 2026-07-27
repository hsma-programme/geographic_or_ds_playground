import streamlit as st
from app.utils import (
    render_navigation,
    write_terminal_html,
    page_styling,
    render_notes_textbox,
    setup_lokigi_site_problem_2sfca_car,
)
from app.utils_investigations import TWO_SFCA_CAR
from app.maps import render_2sfca_map, make_selection_map
from functools import partial

st.set_page_config(initial_sidebar_state="collapsed", layout="wide")
page_styling()

st.title("Who Can Actually Reach a CDC? (by car)")

problem = setup_lokigi_site_problem_2sfca_car()

intro_text = """
> "Travel time only tells you half the story," your analyst says, sliding a single map across the desk. "This one puts three things together at once."
<br><br>
> "It takes how much capacity each CDC has, how many people can reach it, and how far away it is - and works out how much diagnostic capacity is realistically available to the people living in each area. Analysts call it a two-step floating catchment area, or 2SFCA. You can think of it as 'slots per person, once you account for everyone queueing ahead of them'."
<br><br>
> "Green areas are comfortably served. Red areas are stretched thin - and the deepest red areas can't reach any CDC at all within the travel limit. The clever part: two neighbourhoods the same distance from a CDC can still end up very different colours, if one of them is sharing that centre with far more people."
<br><br>
> "Use the buttons above the map to change how far you assume people are willing to drive. Then see who gets left behind."
<br><br>
> They leave the map with you and quietly refill their coffee.
"""

char_count, reveal_speed = write_terminal_html(
    intro_text,
    output_path="app/assets/terminal_working/2sfca_car.html",
)

st.iframe("app/assets/terminal_working/2sfca_car.html", height=400)

# The proposed (blue) markers on this map remain clickable and drive the site
# selection; render_2sfca_map returns the st_folium result for that flow.
sfca_car_selection_map = make_selection_map(
    partial(render_2sfca_map, problem, "car", [30, 45, 60], 45),
    "2sfca_car",
)
sfca_car_selection_map()

render_notes_textbox()

if st.session_state.site_submitted_2sfca_car:
    render_navigation(TWO_SFCA_CAR)
