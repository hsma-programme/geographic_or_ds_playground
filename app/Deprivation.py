import streamlit as st
from app.utils import (
    write_terminal_html,
    render_navigation,
    page_styling,
    render_notes_textbox,
    TERMINAL_DEFAULT_SPEED,
)
from app.utils_investigations import DEPRIVATION
from app.maps import render_deprivation_map, make_selection_map

st.set_page_config(initial_sidebar_state="collapsed", layout="wide")
page_styling()


st.title("Deprivation")

intro_text = """
    <br><br>

    You know that it has been found that women in more deprived areas have
        <br>- lower breast cancer incidence.
        <br>- significantly higher mortality rates.
        <br>- poorer screening uptake.

    <br><br>

    You ask your analyst to show deprivation and they deliver following map, but do not offer any interpretation.
    """

# Once a decision has been made on this page, drop the analyst intro so a
# revisit shows just the evidence and outcome.
if not st.session_state.site_submitted_deprivation:
    reveal_speed = 0 if st.session_state.deprivation_page_visited else TERMINAL_DEFAULT_SPEED
    write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/deprivation_page.html",
        reveal_speed_ms=reveal_speed,
    )
    st.session_state.deprivation_page_visited = True

    st.iframe("app/assets/terminal_working/deprivation_page.html")

select_map = make_selection_map(render_deprivation_map, "deprivation")
select_map()


render_notes_textbox()

if st.session_state.site_submitted_deprivation:
    render_navigation(DEPRIVATION)
