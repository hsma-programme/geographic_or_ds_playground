import streamlit as st
from app.utils import (
    page_styling,
    load_devon_sites,
    write_terminal_html,
    RANK_METRIC_ASCENDING,
    RANK_METRIC_LABELS,
)
import time
from PIL import Image
import pandas as pd
import pickle
from lokigi.multiobjective import ParetoMetric

st.set_page_config(initial_sidebar_state="expanded", layout="wide")
page_styling()

st.title("Optimise - again")

if st.session_state.confirmed_site_final is not None:
    selected_site = st.session_state.confirmed_site_final
else:
    st.error("No site selected. Falling back to default.")
    selected_site = "Tiverton - Lowman Way"

intro_text = """
> But wait!
<br><br>
> The head of the region runs into the room.
<br><br>
> "We found 5 million pounds down the back of the sofa in the lunch room. We can have two CDCs now!"
<br><br>
> You feel the blood drain from your face.
<br><br>
> The sound of 80s music swells. You both turn to look at the data scientist, who shrugs nonchalently.
<br><br>
> "I can just change one parameter and rerun it. Give me five minutes."
"""

char_count, reveal_speed = write_terminal_html(
    intro_text,
    output_path="app/assets/terminal_working/optimise_6_sites.html",
)

st.iframe("app/assets/terminal_working/optimise_6_sites.html", height=325)


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


gif_path = "data/solution_car_6.gif"


# Cache the ~9.5MB pickled solution object so it deserialises once and is
# shared across reruns and sessions, mirroring load_car_5_solution() below.
@st.cache_resource
def load_car_6_solution():
    with open("data/solution_car_6.pkl", "rb") as f:
        return pickle.load(f)


# The single-site solution_df from the previous page - reused here only to
# check whether "just stack the two best individual sites" would have found
# the true best pair (it doesn't always: see naive_top_two_pair() below).
#
# Deliberately named/typed differently from Optimise_5_Sites.py's own
# load_car_5_solution(): every page script runs under the same synthetic
# module name ("__main__", set by Streamlit's page executor), so an
# @st.cache_resource function here with the *same name and body* as one in
# another page would hash to the same cache key and the two pages would
# silently share one mutable SiteSolutionSet instance - including whatever
# compute_pareto_front() mutates into it there. cache_data (not
# cache_resource) sidesteps this even if a name collision recurs, since it
# hands back an independent copy on every call rather than a shared instance.
@st.cache_data
def load_car_5_solution_df():
    with open("data/solution_car_5.pkl", "rb") as f:
        return pickle.load(f).solution_df


solution = load_car_6_solution()

existing_sites = load_devon_sites()
existing_sites = existing_sites[existing_sites["Existing"] == "Yes"][
    "Facility_Name"
].to_list()

st.info(
    f"Your original choice was {selected_site}. With funding for a second site, "
    "does the optimiser include it - or would it pick two completely different sites instead?"
)

run = st.button(
    "Click here to rerun the optimiser", icon=":material/screen_search_desktop:"
)

status = st.empty()

if run:
    st.session_state["optimise_6_sites_ran"] = True

    with st.spinner("The optimiser is starting up..."):
        time.sleep(3)

    status.write("The optimiser is evaluating all possible combinations of 6 sites")

    duration = get_gif_duration(gif_path)

    progress = st.progress(0)

    gif_placeholder = st.empty()
    gif_placeholder.image(gif_path)

    for i in range(100):
        time.sleep(duration / 100)
        progress.progress(i + 1)

    gif_placeholder.empty()
    status.write("")

# Gated on the persisted flag, not the momentary `run` click, so results
# survive any full rerun (a widget interaction elsewhere on the page, a
# revisit after navigating away, a browser refresh) instead of vanishing
# and forcing a full re-watch of the spinner/GIF theatre above just to see
# them again. The animation itself only ever plays once, inside `if run:`.
if st.session_state.get("optimise_6_sites_ran"):
    best_combo = solution.return_best_combination_site_names()
    best_additional = [i for i in best_combo if i not in existing_sites]

    st.success(
        f"Based on the impact on weighted average travel time alone, the optimiser "
        f"finds the best additional two sites to be {best_additional[0]} and {best_additional[1]}."
    )

    # site_names stays on the dataframe (not dropped) - a combination's two new
    # sites are joined with ", " for display only, while the underlying list is
    # still needed below to find combinations that include the user's chosen
    # site (some facility names contain a literal comma, e.g. "Colin Campbell
    # Court, Plymouth", so splitting the display string back apart isn't safe).
    solution_df_display = (
        solution.solution_df.copy()
        .drop(columns=["site_indices", "problem_df"])
        .round(2)
    )

    solution_df_display["site"] = solution_df_display["site_names"].apply(
        lambda x: ", ".join(i for i in x if i not in existing_sites)
    )

    def ordinal(n: int) -> str:
        """Convert an integer to its ordinal representation."""
        if 10 <= n % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix}"

    def get_best_rank_including_site(
        solution_df: pd.DataFrame,
        selected_site: str,
        metric: str,
        ascending: bool = False,
    ) -> int:
        """Return the 1-based rank (best-first, by ``metric``) of the best
        two-site combination that still includes ``selected_site``."""
        sorted_df = solution_df.sort_values(metric, ascending=ascending).reset_index(
            drop=True
        )

        matches = sorted_df.index[
            sorted_df["site_names"].apply(lambda names: selected_site in names)
        ]

        if len(matches) == 0:
            raise ValueError(f"'{selected_site}' not found in any combination.")

        return matches.min() + 1

    # The single-site rankings from the previous page, with each row's one new
    # site pulled out - used below to check whether "just take the two best
    # individual sites" would have found the true best pair.
    solution_5_df = load_car_5_solution_df().copy()
    solution_5_df["site"] = solution_5_df["site_names"].apply(
        lambda x: [i for i in x if i not in existing_sites][0]
    )

    def naive_top_two_pair(metric: str, ascending: bool) -> set[str]:
        """The pair you'd get by just taking the two best-ranked *individual*
        sites from the single-site page, for the given metric."""
        ranked = solution_5_df.sort_values(metric, ascending=ascending).reset_index(
            drop=True
        )
        return {ranked.iloc[0]["site"], ranked.iloc[1]["site"]}

    def true_best_pair(metric: str, ascending: bool) -> set[str]:
        """The actual best two-site combination for the given metric. Sorts the
        full-precision solution_df, not the rounded display copy - rounding to
        2dp can create ties (e.g. several combinations rounding to the same
        coverage percentage) that a sort then resolves inconsistently, which
        can silently pick the wrong "best" row."""
        ranked = solution.solution_df.sort_values(
            metric, ascending=ascending
        ).reset_index(drop=True)
        return {i for i in ranked.iloc[0]["site_names"] if i not in existing_sites}

    n_combinations = len(solution_df_display)

    tab_1, tab_2, tab_3, tab_4 = st.tabs(
        [
            "Solution Comparison",
            "Multi-objective Overview",
            "Multi-objective Breakdown",
            "Solution Breakdown",
        ]
    )

    with tab_1:

        @st.fragment
        def plot_best_sols():
            rank_on = st.radio(
                "Rank On...",
                [
                    "weighted_average",
                    "unweighted_average",
                    "90th_percentile",
                    "max",
                    "proportion_within_coverage_threshold",
                    "inter_tertile_ratio",
                ],
                format_func=lambda m: RANK_METRIC_LABELS[m].capitalize(),
                horizontal=True,
                key="rank_on_6",
            )

            plot_threshold = rank_on == "proportion_within_coverage_threshold"
            ascending = RANK_METRIC_ASCENDING[rank_on]

            # solution.solution_df (full precision), not solution_df_display -
            # see the note on true_best_pair() above.
            comparison_rank = get_best_rank_including_site(
                solution.solution_df, selected_site, rank_on, ascending=ascending
            )

            col1, col2 = st.columns(2)

            with col1:
                st.subheader(f"Best Solution Based on {RANK_METRIC_LABELS[rank_on]}")
                ax = solution.plot_best_combination(
                    solution_rank=1,
                    rank_on=rank_on,
                    plot_regions_not_meeting_threshold=plot_threshold,
                )
                st.pyplot(ax.figure)
            with col2:
                st.subheader(f"Best Solution Still Including {selected_site}")
                ax = solution.plot_best_combination(
                    solution_rank=comparison_rank,
                    rank_on=rank_on,
                    plot_regions_not_meeting_threshold=plot_threshold,
                )
                st.pyplot(ax.figure)

            rank_on_label = RANK_METRIC_LABELS[rank_on]

            st.caption(
                f"Out of all {n_combinations} possible two-site combinations, this is "
                f"the best one that still keeps **{selected_site}** - it ranks "
                f"**{ordinal(comparison_rank)}** overall by {rank_on_label}."
            )

            naive_pair = naive_top_two_pair(rank_on, ascending)
            best_pair = true_best_pair(rank_on, ascending)
            if naive_pair == best_pair:
                st.caption(
                    f"For {rank_on_label}, simply combining the two best *individual* "
                    "sites from the single-site page would have found this same best pair."
                )
            else:
                st.caption(
                    f"For {rank_on_label}, the two best *individual* sites from the "
                    f"single-site page were **{' and '.join(sorted(naive_pair))}** - "
                    "but that isn't the best pair (shown on the left). Sites compete "
                    "for the same demand, so the jointly optimal choice can differ "
                    "from simply stacking your favourites."
                )

        plot_best_sols()

    with tab_4:
        # Select only the columns actually shown before handing off to
        # st.dataframe - it Arrow-serialises every column of whatever frame
        # it's given (even ones excluded via column_order below), and
        # solution_df_display still carries dict-valued equity-group columns
        # and nested per-row problem_df frames that Arrow can't represent,
        # which otherwise raises a (recovered, but noisy) conversion warning.
        display_columns = [
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
        ]
        st.dataframe(
            solution_df_display[display_columns],
            hide_index=True,
            column_order=display_columns,
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

    with tab_2:
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

    with tab_3:
        st.caption(
            "Each panel below zooms into one option from the Pareto front on the "
            "previous tab - the ones no other combination beats on every measure "
            "at once - showing exactly where it's strongest and where it gives "
            "ground, ranked against every combination the optimiser evaluated."
        )
        st.pyplot(solution.plot_pareto_facets())
