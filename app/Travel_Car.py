import streamlit as st
from app.utils import (
    render_navigation,
    solve_car_existing_travel,
    page_styling,
    load_devon_geography,
    load_population_weighted_centroids,
    TERMINAL_DEFAULT_SPEED,
    write_terminal_html,
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


intro_text = f"""
> The analyst presents you with the following map of how long it takes to travel from the centre of each LSOA to its nearest site.
<br><br>
> They tell you that you can swap between each LSOA showing the travel time, the nearest centre, or colour each LSOA by whether it's within a certain travel time of its nearest centre using the buttons above the map.
<br><br>
> "One thing to flag," they add, nodding at the blue pins. "Those colours are all worked out from the sites open today. Clicking a candidate pin just tells us which one you'd pick - it doesn't show you what travel times would look like if it were actually built."
<br><br>
> They scurry off quickly before you can ask any further questions, muttering something about needing to reticulate some splines.
<br><br>
> The map looms large on your screen. You must explore it yourself.
"""

# Once a decision has been made on this page, drop the analyst intro (and its
# typing animation) so a revisit shows just the evidence and outcome.
if not st.session_state.site_submitted_car_travel:
    write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/travel_car.html",
        reveal_speed_ms=TERMINAL_DEFAULT_SPEED,
    )

    st.iframe("app/assets/terminal_working/travel_car.html")

# Note the session key doesn't follow the name of the page as the automated rules would
# make it display weirdly
car_travel_selection_map = make_selection_map(
    partial(render_travel_maps, best_solution_gdf), "car_travel"
)
car_travel_selection_map()

if st.session_state.site_submitted_car_travel:
    render_navigation(TRAVEL_CAR)
