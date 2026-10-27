from pathlib import Path
import streamlit as st
from app.utils import (
    render_navigation,
    write_terminal_html,
    page_styling,
    setup_lokigi_site_problem_2sfca_pt,
    render_prior_choice_recap,
)
from app.utils_investigations import TWO_SFCA_PT
from app.maps import render_2sfca_map, make_selection_map
from functools import partial

st.set_page_config(initial_sidebar_state="expanded", layout="wide")
page_styling()

st.title("Who Can Actually Reach a CDC? (by public transport)")

problem = setup_lokigi_site_problem_2sfca_pt()

intro_text = """
> "Same calculation, but nobody's driving," your analyst says. "Capacity, competition and travel time rolled into one - with buses and trains this time. For a lot of Devon, that changes everything."
<br><br>
> "Watch how much more of the map turns red. A patient without a car can live as close to a CDC as their neighbour and still be cut off by a missing bus route - and these are often the people who can least afford a taxi or a day off work."
<br><br>
> They gesture at the map and fall silent, letting it make the argument for them.
"""

# Once a decision has been made on this page, drop the analyst intro so a
# revisit shows just the evidence and outcome.
if not st.session_state.site_submitted_2sfca_pt:
    write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/2sfca_pt.html",
    )
    st.iframe(Path("app/assets/terminal_working/2sfca_pt.html"), height=300)
    render_prior_choice_recap(TWO_SFCA_PT)

# The proposed (blue) markers on this map remain clickable and drive the site
# selection; render_2sfca_map returns the st_folium result for that flow.
sfca_pt_selection_map = make_selection_map(
    partial(render_2sfca_map, problem, "pt", [60, 90, 120], 90),
    "2sfca_pt",
)
sfca_pt_selection_map()

if st.session_state.site_submitted_2sfca_pt:
    render_navigation(TWO_SFCA_PT)
