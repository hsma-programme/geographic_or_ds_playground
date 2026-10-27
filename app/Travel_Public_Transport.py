from pathlib import Path
import streamlit as st
from app.utils import (
    render_navigation,
    load_devon_geography,
    solve_pt_travel,
    page_styling,
    TERMINAL_DEFAULT_SPEED,
    write_terminal_html,
    render_prior_choice_recap,
)
from app.utils_investigations import TRAVEL_PT
from app.maps import render_travel_maps, make_selection_map
from functools import partial


st.set_page_config(initial_sidebar_state="expanded", layout="wide")
page_styling()

st.title("Travel Time - by Public Transport")

solution = solve_pt_travel()

best_solution_df = solution.return_best_combination_details()["problem_df"].iloc[0]

region_geometry = load_devon_geography()

best_solution_gdf = region_geometry.merge(
    best_solution_df, left_on="LSOA21NM", right_on="LSOA 2021 Name"
)

intro_text = """
> The analyst returns with the same map - travel from the centre of each LSOA, a small area of around 1,500 people, to its nearest CDC - but this time by public transport.
<br><br>
> They warn you the numbers look rather different this time. Public transport in rural Devon is not for the faint-hearted.
<br><br>
> They have now used the phrase "transport modelling is more complicated than people realise" on seventeen separate occasions. You have stopped counting out loud.
"""

# Once a decision has been made on this page, drop the analyst intro (and its
# typing animation) so a revisit shows just the evidence and outcome.
if not st.session_state.site_submitted_public_transport:
    write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/travel_public_transport.html",
        reveal_speed_ms=TERMINAL_DEFAULT_SPEED,
    )

    st.iframe(Path("app/assets/terminal_working/travel_public_transport.html"))
    render_prior_choice_recap(TRAVEL_PT)

# Note the session key doesn't follow the name of the page as the automated rules
# would make it display weirdly
pt_travel_selection_map = make_selection_map(
    partial(
        render_travel_maps, best_solution_gdf, "by public transport", max_threshold=180
    ),
    "public_transport",
)
pt_travel_selection_map()

if st.session_state.site_submitted_public_transport:
    render_navigation(TRAVEL_PT)
