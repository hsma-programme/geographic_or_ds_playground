from pathlib import Path
import streamlit as st
from app.utils import (
    page_styling,
    load_devon_sites,
    write_terminal_html,
    best_combination_title,
    RANK_METRIC_ASCENDING,
    RANK_METRIC_LABELS,
    PARETO_METRICS,
    metric_spreads,
    objective_champions,
    compromise_options,
    ordinal,
    render_objective_champions,
    render_ordinal_rank_summary,
)
import time
from PIL import Image
import pandas as pd
import pickle

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

st.iframe(Path("app/assets/terminal_working/optimise_6_sites.html"), height=325)


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
    # Computed here, before anything is rendered, so the shortlist below and
    # the plots in tabs 2-3 all read from the same is_pareto_optimal /
    # dominated_by columns rather than tab 2 computing them again later.
    solution.compute_pareto_front(metrics=PARETO_METRICS)

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

    # Full-precision copy, mirroring Optimise_5_Sites.py's solution_df_ranking -
    # the shortlist (champions/spreads/compromises) must read exact values,
    # never the 2dp-rounded solution_df_display, for the same reason ranking
    # does: rounding creates ties a sort then resolves inconsistently.
    solution_df_ranking = solution.solution_df.copy()
    solution_df_ranking["site"] = solution_df_ranking["site_names"].apply(
        lambda x: ", ".join(i for i in x if i not in existing_sites)
    )

    champions = objective_champions(solution_df_ranking, site_col="site")
    spreads = metric_spreads(solution_df_ranking)
    compromises = compromise_options(solution_df_ranking, site_col="site")
    n_total = len(solution_df_ranking)
    n_front = int(solution_df_ranking["is_pareto_optimal"].sum())

    st.markdown(
        f"The optimiser compared all **{n_total}** possible two-site combinations "
        f"against **{len(PARETO_METRICS)}** different measures. **{n_front} of them "
        "are defensible** - nothing else beats them across the board. Each is the "
        "best answer to a different question."
    )

    render_objective_champions(champions, spreads, compromises, n_total)

    champion_sites = {c["site"] for c in champions}
    pairs_with_selected = solution_df_ranking[
        solution_df_ranking["site_names"].apply(lambda names: selected_site in names)
    ]
    best_row = (
        pairs_with_selected.sort_values("weighted_average")
        .reset_index(drop=True)
        .iloc[0]
    )
    partner = next(
        s for s in best_row["site_names"] if s not in existing_sites and s != selected_site
    )

    if best_row["site"] in champion_sites:
        partner_badges = next(
            c["badges"] for c in champions if c["site"] == best_row["site"]
        )
        st.info(
            f"The best pairing that still includes your choice, **{selected_site}**, "
            f"adds **{partner}** - together they're one of the shortlisted options "
            f"above, best for {', '.join(partner_badges)}."
        )
    elif best_row["is_pareto_optimal"]:
        st.info(
            f"The best pairing that still includes your choice, **{selected_site}**, "
            f"adds **{partner}** - together they're on the shortlist of defensible "
            "options, though not the best at any single measure."
        )
    else:
        n_dominators = len(best_row["dominated_by"])
        st.warning(
            f"The best pairing that still includes your choice, **{selected_site}**, "
            f"adds **{partner}** - but that pair is beaten outright by "
            f"{n_dominators} other combination{'s' if n_dominators != 1 else ''}."
        )

    st.divider()

    def get_best_rank_including_site(
        solution_df: pd.DataFrame,
        selected_site: str,
        metric: str,
        ascending: bool = False,
    ) -> int:
        """Return the 1-based rank (best-first, by ``metric``) of the best
        two-site combination that still includes ``selected_site``.

        kind="mergesort" (stable) to match lokigi's own internal ordering -
        see the note on app.utils.get_solution_rank; this rank is handed
        straight back to plot_best_combination(solution_rank=...), so an
        unstable sort can point at a different row within a tie group than
        the one lokigi then plots."""
        sorted_df = solution_df.sort_values(
            metric, ascending=ascending, kind="mergesort"
        ).reset_index(drop=True)

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
        sites from the single-site page, for the given metric. Stable sort so
        this names the same two sites that page itself showed."""
        ranked = solution_5_df.sort_values(
            metric, ascending=ascending, kind="mergesort"
        ).reset_index(drop=True)
        return {ranked.iloc[0]["site"], ranked.iloc[1]["site"]}

    def true_best_pair(metric: str, ascending: bool) -> set[str]:
        """The actual best two-site combination for the given metric. Sorts the
        full-precision solution_df, not the rounded display copy - rounding to
        2dp can create ties (e.g. several combinations rounding to the same
        coverage percentage) that a sort then resolves inconsistently, which
        can silently pick the wrong "best" row. kind="mergesort" for the same
        reason, one level down: genuine ties still exist at full precision,
        and this pair is compared against the one drawn in the left-hand
        panel, which lokigi picks with a stable sort."""
        ranked = solution.solution_df.sort_values(
            metric, ascending=ascending, kind="mergesort"
        ).reset_index(drop=True)
        return {i for i in ranked.iloc[0]["site_names"] if i not in existing_sites}

    n_combinations = len(solution_df_display)

    render_ordinal_rank_summary(
        lambda metric: get_best_rank_including_site(
            solution.solution_df,
            selected_site,
            metric,
            ascending=RANK_METRIC_ASCENDING[metric],
        )
    )

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
            sort_by = st.radio(
                "Rank On...",
                [
                    "weighted_average",
                    "unweighted_average",
                    "90th_percentile",
                    "max",
                    "proportion_within_coverage_threshold",
                    "inter_tertile_ratio",
                    "proportion_demand_improved",
                    "mean_reduction_among_improved",
                    "demand_beyond_threshold_45",
                ],
                format_func=lambda m: RANK_METRIC_LABELS[m].capitalize(),
                horizontal=True,
                key="rank_on_6",
            )

            plot_threshold = sort_by == "proportion_within_coverage_threshold"
            ascending = RANK_METRIC_ASCENDING[sort_by]

            # solution.solution_df (full precision), not solution_df_display -
            # see the note on true_best_pair() above.
            comparison_rank = get_best_rank_including_site(
                solution.solution_df, selected_site, sort_by, ascending=ascending
            )

            # lokigi's own default title reports whichever metric solve() was
            # told to rank on - frozen into the pickle, so it named
            # "proportion demand improved" (as a raw 0-1 proportion) whatever
            # this radio was set to. title=None + our own set_title() puts the
            # metric the user actually picked, in its own units, on the map.
            def plot_with_title(solution_rank):
                ax = solution.plot_best_combination(
                    solution_rank=solution_rank,
                    sort_by=sort_by,
                    plot_regions_not_meeting_threshold=plot_threshold,
                    title=None,
                )
                # The row lokigi itself selected for this rank, via its own
                # public accessor - so the numbers in the title always belong
                # to the map beside them.
                plotted_row = solution.return_best_combination_details(
                    sort_by=sort_by, top_n=solution_rank
                ).iloc[solution_rank - 1]
                ax.set_title(
                    best_combination_title(
                        plotted_row,
                        sort_by,
                        n_sites=solution.n_sites,
                        solution_rank=solution_rank,
                    ),
                    fontsize=12,
                )
                return ax

            col1, col2 = st.columns(2)

            with col1:
                st.subheader(f"Best Solution Based on {RANK_METRIC_LABELS[sort_by]}")
                st.pyplot(plot_with_title(1).figure)
            with col2:
                st.subheader(f"Best Solution Still Including {selected_site}")
                st.pyplot(plot_with_title(comparison_rank).figure)

            sort_by_label = RANK_METRIC_LABELS[sort_by]

            st.caption(
                f"Out of all {n_combinations} possible two-site combinations, this is "
                f"the best one that still keeps **{selected_site}** - it ranks "
                f"**{ordinal(comparison_rank)}** overall by {sort_by_label}."
            )

            naive_pair = naive_top_two_pair(sort_by, ascending)
            best_pair = true_best_pair(sort_by, ascending)
            if naive_pair == best_pair:
                st.caption(
                    f"For {sort_by_label}, simply combining the two best *individual* "
                    "sites from the single-site page would have found this same best pair."
                )
            else:
                st.caption(
                    f"For {sort_by_label}, the two best *individual* sites from the "
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
            "is_pareto_optimal",
            "weighted_average",
            "unweighted_average",
            "90th_percentile",
            "max",
            "proportion_within_coverage_threshold",
            "inter_tertile_ratio",
            "avg_lower_third_bins",
            "avg_upper_third_bins",
            "demand_improved",
            "proportion_demand_improved",
            "mean_reduction_among_improved",
            "demand_beyond_threshold_45",
            "demand_beyond_threshold_60",
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
                "is_pareto_optimal": st.column_config.CheckboxColumn(
                    "Defensible?",
                    help="Nothing else in this list beats it across every measure at once.",
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
                    format="percent",
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
                "demand_improved": st.column_config.NumberColumn(
                    "People with a shorter journey",
                    format="%.0f",
                ),
                "proportion_demand_improved": st.column_config.NumberColumn(
                    "Share with a shorter journey (%)",
                    format="percent",
                ),
                "mean_reduction_among_improved": st.column_config.NumberColumn(
                    "Avg. minutes saved for those who benefit",
                    format="%.1f",
                ),
                "demand_beyond_threshold_45": st.column_config.NumberColumn(
                    "Still >45 min away",
                    format="%.0f",
                ),
                "demand_beyond_threshold_60": st.column_config.NumberColumn(
                    "Still >60 min away",
                    format="%.0f",
                ),
            },
        )

    with tab_2:
        st.subheader("Comparing the best solutions across multiple metrics")

        # Pareto front already computed above, on the same PARETO_METRICS used
        # for the objective-champion shortlist, so this plots exactly what
        # produced that shortlist rather than a separately-defined metric set.
        st.pyplot(solution.plot_pareto_summary(width_multiplier=3))

        st.caption(
            "An inter-tertile ratio below 1 means those in IMD 1-3 (most deprived) travel "
            "less on average than those in IMD 7-10 (least deprived). This tool scores lower "
            "as always better here - a deliberate choice to reward actively cutting travel "
            "times for the most deprived group, not just narrowing the gap to zero."
        )

    with tab_3:
        st.caption(
            "Each panel below zooms into one option from the Pareto front on the "
            "previous tab - the ones no other combination beats on every measure "
            "at once - showing exactly where it's strongest and where it gives "
            "ground, ranked against every combination the optimiser evaluated."
        )
        st.pyplot(solution.plot_pareto_facets())
