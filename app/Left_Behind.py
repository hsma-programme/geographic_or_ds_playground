from pathlib import Path
import pandas as pd
import streamlit as st
from app.utils import (
    render_navigation,
    write_terminal_html,
    page_styling,
    render_prior_choice_recap,
    load_devon_geography,
    evaluate_car_baseline,
    demand_by_equity_band,
)
from app.utils_investigations import LEFT_BEHIND
from app.maps import render_left_behind_map, make_selection_map
from functools import partial

st.set_page_config(initial_sidebar_state="expanded", layout="wide")
page_styling()

st.title("Who Is Left Behind Today?")

baseline = evaluate_car_baseline()
baseline_row = baseline.solution_df.iloc[0]
total_demand = baseline.site_problem.total_demand

best_solution_df = baseline.return_best_combination_details()["problem_df"].iloc[0]
region_geometry = load_devon_geography()
best_solution_gdf = region_geometry.merge(
    best_solution_df, left_on="LSOA21NM", right_on="LSOA 2021 Name"
)

intro_text = """
> "Every map so far has coloured the problem in," your analyst says, "but none of them has actually counted it."
<br><br>
> "So here's today's network on its own - the four CDCs open right now, nothing proposed, nothing hypothetical. Just: how many people are currently more than 45 or 60 minutes from any of them by car, and are they spread evenly or not."
<br><br>
> "Spoiler," they add, not looking up from their screen. "It's not even."
"""

# Once a decision has been made on this page, drop the analyst intro, the
# headline numbers and the equity chart so a revisit shows just the map and
# the outcome - mirroring how make_selection_map() itself already collapses
# down to a one-line confirmation once submitted.
if not st.session_state.site_submitted_left_behind:
    write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/left_behind.html",
    )
    st.iframe(Path("app/assets/terminal_working/left_behind.html"), height=275)
    render_prior_choice_recap(LEFT_BEHIND)

    demand_45 = baseline_row["demand_beyond_threshold_45"]
    demand_60 = baseline_row["demand_beyond_threshold_60"]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("More than 45 minutes from any CDC today", f"{demand_45:,.0f}")
        st.caption(
            f"{demand_45 / total_demand:.1%} of the 50-84 population across Devon."
        )
    with col2:
        st.metric("More than 60 minutes from any CDC today", f"{demand_60:,.0f}")
        st.caption(
            f"{demand_60 / total_demand:.1%} of the 50-84 population across Devon."
        )

    st.subheader("Is that gap spread evenly?")
    st.caption(
        "Share of each deprivation band more than 45 minutes from any CDC today - "
        "normalised by that band's own population, not a raw headcount, so the "
        "biggest band doesn't automatically look the worst."
    )

    equity_counts = baseline_row["demand_beyond_threshold_45_by_equity_group"]
    band_totals = demand_by_equity_band()
    equity_df = pd.DataFrame(
        {
            "IMD decile (1 = most deprived)": decile,
            "Share more than 45 min away": equity_counts[decile] / band_totals[decile],
        }
        for decile in sorted(equity_counts)
    ).set_index("IMD decile (1 = most deprived)")
    st.bar_chart(equity_df, y="Share more than 45 min away")

    st.subheader("Where are they?")

left_behind_selection_map = make_selection_map(
    partial(render_left_behind_map, best_solution_gdf), "left_behind"
)
left_behind_selection_map()

if st.session_state.site_submitted_left_behind:
    render_navigation(LEFT_BEHIND)
