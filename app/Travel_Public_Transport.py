import streamlit as st
from app.utils import (
    render_navigation,
    load_devon_geography,
    setup_lokigi_site_problem_pt,
    page_styling,
    TERMINAL_DEFAULT_SPEED,
    write_terminal_html,
    render_notes_textbox,
)
from app.utils_investigations import TRAVEL_PT
from app.maps import render_travel_maps, make_selection_map
import time
from functools import partial


st.set_page_config(initial_sidebar_state="collapsed", layout="wide")
page_styling()

st.title("Travel Time - by Public Transport")

problem = setup_lokigi_site_problem_pt()

solution = problem.solve(p=4)

best_solution_df = solution.return_best_combination_details()["problem_df"].iloc[0]

region_geometry = load_devon_geography()

best_solution_gdf = region_geometry.merge(
    best_solution_df, left_on="LSOA21NM", right_on="LSOA 2021 Name"
)

intro_text = f"""
> The analyst returns with the same map as before, but this time the travel times are for public transport rather than the car.
<br><br>
> They tell you that you can swap between each LSOA showing the travel time, the nearest centre, or colour each LSOA by whether it's within a certain travel time of its nearest centre using the buttons above the map.
<br><br>
> "Same catch as last time," they add. "The colours only reflect the sites open today - the candidate pins are there for you to pick from, not to show what would happen if one were actually built."
<br><br>
> They warn you that the numbers can look rather different this time, and that public transport in rural Devon is not for the faint-hearted.
<br><br>
> They have now used the phrase "transport modelling is more complicated than people realise" on seventeen separate occasions. You have stopped counting out loud.
"""

char_count, reveal_speed = write_terminal_html(
    intro_text,
    output_path="app/assets/terminal_working/travel_public_transport.html",
    reveal_speed_ms=TERMINAL_DEFAULT_SPEED,
)

st.iframe("app/assets/terminal_working/travel_public_transport.html")

typing_duration = (char_count * reveal_speed) / 1000
time.sleep(typing_duration)

# Note the session key doesn't follow the name of the page as the automated rules
# would make it display weirdly
pt_travel_selection_map = make_selection_map(
    partial(render_travel_maps, best_solution_gdf), "public_transport"
)
pt_travel_selection_map()

render_notes_textbox()

if st.session_state.site_submitted_public_transport:
    render_navigation(TRAVEL_PT)
