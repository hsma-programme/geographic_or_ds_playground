from pathlib import Path
import streamlit as st
from app.utils import (
    render_navigation,
    solve_car_existing_travel,
    page_styling,
    load_devon_geography,
    load_population_weighted_centroids,
    TERMINAL_DEFAULT_SPEED,
    write_terminal_html,
    render_prior_choice_recap,
)
from app.utils_investigations import TRAVEL_CAR
from app.maps import render_travel_maps, make_selection_map
from functools import partial

st.set_page_config(initial_sidebar_state="expanded", layout="wide")
page_styling()

st.title("Travel Time - by Car")

solution = solve_car_existing_travel()

best_solution_df = solution.return_best_combination_details()["problem_df"].iloc[0]


region_geometry = load_devon_geography()
pwc = load_population_weighted_centroids(snapped=True)

# st.write(best_solution_df)


best_solution_gdf = region_geometry.merge(
    best_solution_df, left_on="LSOA21NM", right_on="LSOA 2021 Name"
)


intro_text = """
> The analyst presents a map of how long it takes to drive from the centre of each LSOA - a small statistical area of around 1,500 people - to its nearest CDC. Hover over an area to see its time.
<br><br>
> They scurry off before you can ask any further questions, muttering something about needing to reticulate some splines.
"""

# Once a decision has been made on this page, drop the analyst intro (and its
# typing animation) so a revisit shows just the evidence and outcome.
if not st.session_state.site_submitted_car_travel:
    write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/travel_car.html",
        reveal_speed_ms=TERMINAL_DEFAULT_SPEED,
    )

    st.iframe(Path("app/assets/terminal_working/travel_car.html"))
    render_prior_choice_recap(TRAVEL_CAR)

# Note the session key doesn't follow the name of the page as the automated rules would
# make it display weirdly
car_travel_selection_map = make_selection_map(
    partial(render_travel_maps, best_solution_gdf), "car_travel"
)
car_travel_selection_map()

if st.session_state.site_submitted_car_travel:
    render_navigation(TRAVEL_CAR)
