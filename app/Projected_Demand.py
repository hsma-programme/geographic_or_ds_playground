import streamlit as st
from app.utils import (
    render_navigation,
    write_terminal_html,
    page_styling,
    render_prior_choice_recap,
)
from app.utils_investigations import PROJECTED_DEMAND
from app.maps import render_projected_demand_map, make_selection_map

st.set_page_config(initial_sidebar_state="expanded", layout="wide")
page_styling()

st.title("Projected Demand")

intro_text = """
> Your analyst has run the 50-84 population forward 10 years and delivered the following map.
<br><br>
> They tell you that today's highest-demand areas aren't necessarily tomorrow's. Devon's rural and coastal districts are ageing faster than its cities, as older residents retire in and younger residents leave for work elsewhere.
<br><br>
> They suggest you switch between "Projected Growth", "Projected 50-84 Population", and "Projected Total Population" using the options above the map to see how the picture changes.
<br><br>
> They let you know that yellow is the highest value for whichever metric you've selected, and purple means lower.
<br><br>
> You hear a sound you haven't heard for nearly twenty years - the dial-up tone. You realise it is coming from the analyst. You decide it is best not to question this and turn your attention to the map.
"""

# Once a decision has been made on this page, drop the analyst intro so a
# revisit shows just the evidence and outcome.
if not st.session_state.site_submitted_projected_demand:
    write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/projected_demand.html",
    )
    st.iframe("app/assets/terminal_working/projected_demand.html", height=375)
    render_prior_choice_recap(PROJECTED_DEMAND)

projected_demand_selection_map = make_selection_map(
    render_projected_demand_map, "projected_demand"
)
projected_demand_selection_map()

if st.session_state.site_submitted_projected_demand:
    render_navigation(PROJECTED_DEMAND)
