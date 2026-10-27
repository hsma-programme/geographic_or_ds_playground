from pathlib import Path
import streamlit as st
from app.utils import (
    render_navigation,
    write_terminal_html,
    page_styling,
    render_prior_choice_recap,
)
from app.utils_investigations import UTILISATION
from app.maps import render_utilisation_map, make_selection_map

st.set_page_config(initial_sidebar_state="expanded", layout="wide")
page_styling()

st.title("Current CDC Utilisation")

intro_text = """
> Your analyst returns with two maps. On the left, the four existing CDCs: blue centres have spare capacity, red ones are at or beyond it, and bigger circles are busier. On the right, where the people aged 50-84 live.
<br><br>
> They have ten other analyses to complete today, so have not had time to add their interpretation.
<br><br>
> "Read them together," they suggest. "A full centre next to lots of demand is a very different problem from a quiet centre in an empty area."
<br><br>
> They dissolve into a cloud of static, leaving you to interpret the maps.
"""

# Once a decision has been made on this page, drop the analyst intro so a
# revisit shows just the evidence and outcome.
if not st.session_state.site_submitted_utilisation:
    write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/utilisation.html",
    )
    st.iframe(Path("app/assets/terminal_working/utilisation.html"), height=275)
    render_prior_choice_recap(UTILISATION)

utilisation_selection_map = make_selection_map(render_utilisation_map, "utilisation")
utilisation_selection_map()

if st.session_state.site_submitted_utilisation:
    render_navigation(UTILISATION)
