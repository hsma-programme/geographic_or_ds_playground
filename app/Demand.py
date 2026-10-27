from pathlib import Path
import streamlit as st
from app.utils import (
    render_navigation,
    write_terminal_html,
    page_styling,
    select_site_from_current_evidence,
    render_prior_choice_recap,
    write_crt_html,
)
from app.utils_investigations import DEMAND
from app.maps import render_demand_map, make_selection_map

st.set_page_config(initial_sidebar_state="expanded", layout="wide")
page_styling()

st.title("Demand")

intro_text = """
> Your analyst has delivered a map of the population aged 50-84 - the people you've been asked to prioritise. Yellow areas have the most people, purple the fewest. Hover over an area to see its exact count.
<br><br>
> The analyst then becomes pixellated and returns to the cloud until they are next required.
<br><br>
> You hope the map works.
"""

# Once a decision has been made on this page, drop the analyst intro so a
# revisit shows just the evidence and outcome.
if not st.session_state.site_submitted_demand:
    char_count, reveal_speed = write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/demand.html",
    )
    cola, colb = st.columns([0.6, 0.4])
    cola.iframe(Path("app/assets/terminal_working/demand.html"), height=250)

    # Swap the CRT image just after the text finishes typing. The terminal and
    # CRT are separate iframes, so they can't signal each other - this is an
    # estimate from the text's length and speed.
    swap_delay_ms = char_count * reveal_speed + 600

    generated_crt = write_crt_html(
        image_path="app/assets/demand.png",
        output_path="app/assets/crt_working/demand.html",
        curvature=0.3,
        scanlines=0.6,
        next_image_path="app/assets/demand_2.png",
        swap_delay_ms=swap_delay_ms,
    )
    colb.iframe(Path(generated_crt))

    render_prior_choice_recap(DEMAND)

demand_selection_map = make_selection_map(
    render_demand_map,
    "demand",
    instruction=(
        "Click a blue pin to choose a site. The red pins are the existing CDCs. "
        "This map shows raw demand - everyone aged 50-84, not just the demand "
        "that isn't currently being met."
    ),
)
demand_selection_map()

if st.session_state.site_submitted_demand:
    render_navigation(DEMAND)
