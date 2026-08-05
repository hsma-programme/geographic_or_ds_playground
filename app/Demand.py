from pathlib import Path
import streamlit as st
from app.utils import (
    render_navigation,
    write_terminal_html,
    page_styling,
    select_site_from_current_evidence,
    render_prior_choice_recap,
)
from app.utils_investigations import DEMAND
from app.maps import render_demand_map, make_selection_map

st.set_page_config(initial_sidebar_state="expanded", layout="wide")
page_styling()

st.title("Demand")

intro_text = """
> Your analyst has delivered the following map.
<br><br>
> They tell you that you can hover over the red icons (the current CDCs) and the blue icons (the proposed CDCs) to find out more.
<br><br>
> They also tell you that you can hover over each coloured region to see the exact count of people 50-84 in the region.
<br><br>
> They let you know that yellow is the highest demand, and purple means lower demand. They mention that you can use the + and - buttons in the top left to zoom in and out.
<br><br>
> They then become pixellated and return to the cloud until they are next required. You hope the map works.
"""

# Once a decision has been made on this page, drop the analyst intro so a
# revisit shows just the evidence and outcome.
if not st.session_state.site_submitted_demand:
    write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/demand.html",
    )
    st.iframe(Path("app/assets/terminal_working/demand.html"), height=300)
    render_prior_choice_recap(DEMAND)

demand_selection_map = make_selection_map(render_demand_map, "demand")
demand_selection_map()

if st.session_state.site_submitted_demand:
    render_navigation(DEMAND)
