import streamlit as st
from app.utils import page_styling, load_devon_sites
import time
from PIL import Image
import pandas as pd
import pickle
from lokigi.multiobjective import ParetoMetric

st.set_page_config(initial_sidebar_state="collapsed", layout="wide")
page_styling()

st.title("Optimise")

# TODO: HARDCODED for development purposes
selected_site = "Okehampton - Exeter Road Industrial Estate"


def get_gif_duration(filename):
    with Image.open(filename) as gif:
        total_duration_ms = 0

        try:
            while True:
                total_duration_ms += gif.info.get("duration", 100)
                gif.seek(gif.tell() + 1)
        except EOFError:
            pass

    return total_duration_ms / 1000


gif_path = "data/solution_car_5.gif"

with open("data/solution_car_5.pkl", "rb") as f:
    solution = pickle.load(f)

# st.write(solution.show_solutions())

existing_sites = load_devon_sites()
existing_sites = existing_sites[existing_sites["Existing"] == "Yes"][
    "Facility_Name"
].to_list()

st.info(
    f"You selected {selected_site} as the best solution.\n\nDoes the optimiser agree?"
)

run = st.button("Click here to run the optimiser")

if run:
    with st.spinner("The optimiser is starting up..."):
        time.sleep(3)

    st.write("The optimiser is evaluating all possible combinations of 5 sites")

    duration = get_gif_duration(gif_path)

    progress = st.progress(0)

    gif_placeholder = st.empty()
    gif_placeholder.image(gif_path)

    for i in range(100):
        time.sleep(duration / 100)
        progress.progress(i + 1)

    best_combo = solution.return_best_combination_site_names()
    best_additional = [i for i in best_combo if i not in existing_sites]

    gif_placeholder.success(
        f"Based on the impact on weighted average travel time alone, the optimiser finds the best additional site to be {best_additional[0]}."
    )

    solution_df_display = (
        solution.solution_df.copy()
        .drop(columns=["site_indices", "problem_df"])
        .round(2)
    )

    solution_df_display["site"] = solution_df_display["site_names"].apply(
        lambda x: [i for i in x if i not in existing_sites][0]
    )

    solution_df_display = solution_df_display.drop(columns="site_names")

    st.dataframe(
        solution_df_display,
        hide_index=True,
        column_order=[
            "solution_rank",
            "site",
            "weighted_average",
            "unweighted_average",
            "90th_percentile",
            "max",
            "proportion_within_coverage_threshold",
            "inter_tertile_ratio",
            "avg_lower_third_bins",
            "avg_upper_third_bins",
        ],
        column_config={
            "solution_rank": st.column_config.NumberColumn(
                "Rank",
                format="%d",
            ),
            "site": st.column_config.TextColumn(
                "Site(s)",
            ),
            "weighted_average": st.column_config.NumberColumn(
                "Weighted average (mins)",
                format="%.1f",
            ),
            "unweighted_average": st.column_config.NumberColumn(
                "Average (mins)",
                format="%.1f",
            ),
            "90th_percentile": st.column_config.NumberColumn(
                "90th percentile (mins)",
                format="%.1f",
            ),
            "max": st.column_config.NumberColumn(
                "Maximum (mins)",
                format="%.1f",
            ),
            "proportion_within_coverage_threshold": st.column_config.NumberColumn(
                "Coverage (%)",
                format="%.1f",
            ),
            "inter_tertile_ratio": st.column_config.NumberColumn(
                "Inter-tertile ratio",
                format="%.2f",
            ),
            "avg_lower_third_bins": st.column_config.NumberColumn(
                "Average Car Travel (lowest third)",
                format="%.1f",
            ),
            "avg_upper_third_bins": st.column_config.NumberColumn(
                "Average Car Travel (highest third)",
                format="%.1f",
            ),
        },
    )

    def ordinal(n: int) -> str:
        """Convert an integer to its ordinal representation."""
        if 10 <= n % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix}"

    def get_solution_rank(
        solution_df: pd.DataFrame,
        selected_site: str,
        metric: str,
        ascending: bool = False,
    ) -> int:
        """
        Return the 1-based rank of a site for a given metric.
        """
        sorted_df = solution_df.sort_values(metric, ascending=ascending).reset_index(
            drop=True
        )

        matches = sorted_df.index[sorted_df["site"] == selected_site]

        if len(matches) == 0:
            raise ValueError(f"'{selected_site}' not found in dataframe.")

        return matches[0] + 1

    weighted = ordinal(
        get_solution_rank(
            solution_df_display, selected_site, "weighted_average", ascending=True
        )
    )
    average = ordinal(
        get_solution_rank(
            solution_df_display, selected_site, "unweighted_average", ascending=True
        )
    )
    p90 = ordinal(
        get_solution_rank(
            solution_df_display, selected_site, "90th_percentile", ascending=True
        )
    )
    maximum = ordinal(
        get_solution_rank(solution_df_display, selected_site, "max", ascending=True)
    )
    coverage = ordinal(
        get_solution_rank(
            solution_df_display,
            selected_site,
            "proportion_within_coverage_threshold",
            ascending=False,
        )
    )

    st.markdown(f"""
Your solution is the:

- **{weighted}** best in terms of weighted average car travel time.
- **{average}** best in terms of **un**weighted average car travel time.
- **{p90}** best in terms of 90th percentile car travel time.
- **{maximum}** best in terms of maximum car travel time.
- **{coverage}** best in terms of the demand covered within 30 minutes of a site by car.
""")

    st.subheader("Comparing the best solutions across multiple metrics")

    metrics = [
        ParetoMetric(
            column="weighted_average",
            direction="lower_better",
            label="weighted average travel time",
            unit="minutes",
        ),
        ParetoMetric(
            column="max",
            direction="lower_better",
            label="maximum travel time",
            unit="minutes",
        ),
        ParetoMetric(
            column="proportion_within_coverage_threshold",
            direction="higher_better",
            label="proportion within coverage threshold",
        ),
        ParetoMetric(
            column="inter_tertile_ratio",
            direction="lower_better",
            label="ratio of weighted travel times in IMD 1-3 to IMD 7-10",
        ),
        ParetoMetric(
            column="avg_lower_third_bins",
            direction="lower_better",
            label="average travel time for those in IMD 1-3",
            unit="minutes",
        ),
    ]

    solution.compute_pareto_front(metrics=metrics)

    st.pyplot(solution.plot_pareto_summary(width_multiplier=3))

    st.caption(
        "An inter-tertile ratio of below 1 means those in IMD 1-3 (most deprived) have a shorter travel time on average than those in IMD 7-10 (least deprived)"
    )

    st.pyplot(solution.plot_pareto_facets())
