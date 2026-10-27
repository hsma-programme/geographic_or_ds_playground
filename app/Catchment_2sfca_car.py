from pathlib import Path
import streamlit as st
from app.utils import (
    render_navigation,
    write_terminal_html,
    page_styling,
    setup_lokigi_site_problem_2sfca_car,
    render_prior_choice_recap,
)
from app.utils_investigations import TWO_SFCA_CAR
from app.maps import render_2sfca_map, make_selection_map
from functools import partial

st.set_page_config(initial_sidebar_state="expanded", layout="wide")
page_styling()

st.title("Who Can Actually Reach a CDC? (by car)")

problem = setup_lokigi_site_problem_2sfca_car()

intro_text = """
> "Travel time only tells you half the story," your analyst says. "This map also counts how much capacity each CDC has, and how many people are competing for it. Analysts call it a two-step floating catchment area, or 2SFCA. Think of it as 'slots per person, once you count everyone queueing ahead of you'."
<br><br>
> "The thing to notice: two areas the same distance from a CDC can end up very different colours, if one is sharing it with far more people."
<br><br>
> They leave the map with you and quietly refill their coffee. You could swear their mug has tripled in size.
"""

# Once a decision has been made on this page, drop the analyst intro so a
# revisit shows just the evidence and outcome.
if not st.session_state.site_submitted_2sfca_car:
    write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/2sfca_car.html",
    )
    st.iframe(Path("app/assets/terminal_working/2sfca_car.html"), height=300)
    render_prior_choice_recap(TWO_SFCA_CAR)

# The proposed (blue) markers on this map remain clickable and drive the site
# selection; render_2sfca_map returns the st_folium result for that flow.
sfca_car_selection_map = make_selection_map(
    partial(render_2sfca_map, problem, "car", [30, 45, 60], 45),
    "2sfca_car",
)
sfca_car_selection_map()

if st.session_state.site_submitted_2sfca_car:
    render_navigation(TWO_SFCA_CAR)
