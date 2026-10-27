from pathlib import Path
import streamlit as st
from app.utils import (
    write_terminal_html,
    render_navigation,
    page_styling,
    TERMINAL_DEFAULT_SPEED,
    render_prior_choice_recap,
)
from app.utils_investigations import DEPRIVATION
from app.maps import render_deprivation_map, make_selection_map

st.set_page_config(initial_sidebar_state="expanded", layout="wide")
page_styling()


st.title("Deprivation")

intro_text = """
    <br><br>

    You know that it has been found that people in more deprived areas often have
    significantly higher mortality rates and poorer screening uptake.
    <br><br>
    You ask your analyst to show deprivation and they deliver following map, but do not offer any interpretation.
    <br><br>
    You turn around and they are gone. You are on your own.
    """

# Once a decision has been made on this page, drop the analyst intro so a
# revisit shows just the evidence and outcome.
if not st.session_state.site_submitted_deprivation:
    reveal_speed = (
        0 if st.session_state.deprivation_page_visited else TERMINAL_DEFAULT_SPEED
    )
    write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/deprivation_page.html",
        reveal_speed_ms=reveal_speed,
    )
    st.session_state.deprivation_page_visited = True

    st.iframe(Path("app/assets/terminal_working/deprivation_page.html"))
    render_prior_choice_recap(DEPRIVATION)

select_map = make_selection_map(render_deprivation_map, "deprivation")
select_map()

if st.session_state.site_submitted_deprivation:
    render_navigation(DEPRIVATION)
