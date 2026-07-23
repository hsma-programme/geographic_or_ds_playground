import streamlit as st
from app.utils import (
    render_navigation,
    write_terminal_html,
    page_styling,
)
from app.utils_investigations import PROJECTED_DEMAND
from app.maps import render_projected_demand_map, make_selection_map

st.set_page_config(initial_sidebar_state="collapsed", layout="wide")
page_styling()

st.title("Projected Demand")

intro_text = """
> Your analyst has run the 50-84 population forward 10 years and delivered the following map.
<br><br>
> They tell you that today's highest-demand areas aren't necessarily tomorrow's. Devon's rural and coastal districts are ageing faster than its cities, as older residents retire in and younger residents leave for work elsewhere.
<br><br>
> They suggest you switch between "Projected Growth", "Projected 50-84 Population", and "Projected Total Population" using the options above the map to see how the picture changes.
<br><br>
> They let you know that yellow is the highest value for whichever metric you've selected, and purple means lower. They mention that you can use the + and - buttons in the top left to zoom in and out.
<br><br>
> They then become pixellated and return to the cloud until they are next required. You wonder whether the site you'd choose today is still the right one for 2036.
"""

char_count, reveal_speed = write_terminal_html(
    intro_text,
    output_path="app/assets/terminal_working/projected_demand.html",
)

st.iframe("app/assets/terminal_working/projected_demand.html", height=275)

projected_demand_selection_map = make_selection_map(
    render_projected_demand_map, "projected_demand"
)
projected_demand_selection_map()

if st.session_state.site_submitted_projected_demand:
    render_navigation(PROJECTED_DEMAND)
