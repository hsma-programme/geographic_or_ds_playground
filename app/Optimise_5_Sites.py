import streamlit as st
from app.utils import (
    page_styling,
    load_devon_sites,
    RANK_METRIC_ASCENDING,
    RANK_METRIC_LABELS,
    PARETO_METRICS,
    metric_spreads,
    objective_champions,
    compromise_options,
)
import time
from PIL import Image
import pandas as pd
import pickle

st.set_page_config(initial_sidebar_state="expanded", layout="wide")
page_styling()

st.title("Optimise")

if st.session_state.confirmed_site_final is not None:
    selected_site = st.session_state.confirmed_site_final
else:
    st.error("No site selected. Falling back to default.")
    selected_site = "Tiverton - Lowman Way"


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


# Cache the ~2MB pickled solution object so it deserialises once and is shared
# across reruns and sessions, instead of being unpickled on every rerun. The
# page only reads from it (solution_df, ranking, plotting), so sharing is safe.
@st.cache_resource
def load_car_5_solution():
    with open("data/solution_car_5.pkl", "rb") as f:
        return pickle.load(f)


solution = load_car_5_solution()

# st.write(solution.show_solutions())

existing_sites = load_devon_sites()
existing_sites = existing_sites[existing_sites["Existing"] == "Yes"][
    "Facility_Name"
].to_list()

st.info(
    f"You selected {selected_site} as the best overall solution.\n\nDoes the optimiser agree?"
)

run = st.button(
    "Click here to run the optimiser", icon=":material/screen_search_desktop:"
)

status = st.empty()

if run:
    st.session_state["optimise_5_sites_ran"] = True

    with st.spinner("The optimiser is starting up..."):
        time.sleep(3)

    status.write("The optimiser is evaluating all possible combinations of 5 sites")

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
if st.session_state.get("optimise_5_sites_ran"):
    # Computed here, before anything is rendered, so the shortlist below and
    # the plots in tabs 2-3 all read from the same is_pareto_optimal /
    # dominated_by columns rather than tab 2 computing them again later.
    solution.compute_pareto_front(metrics=PARETO_METRICS)

    solution_df_display = (
        solution.solution_df.copy()
        .drop(columns=["site_indices", "problem_df"])
        .round(2)
    )

    solution_df_display["site"] = solution_df_display["site_names"].apply(
        lambda x: [i for i in x if i not in existing_sites][0]
    )

    solution_df_display = solution_df_display.drop(columns="site_names")

    # Full-precision copy for ranking/matching - rounding solution_df_display to
    # 2dp can create ties (e.g. several combinations rounding to the same
    # coverage percentage) that a sort then resolves inconsistently, silently
    # picking the wrong "best" row. Only solution_df_display (rounded) is used
    # for the table shown to the user, never for ranking.
    solution_df_ranking = solution.solution_df.copy()
    solution_df_ranking["site"] = solution_df_ranking["site_names"].apply(
        lambda x: [i for i in x if i not in existing_sites][0]
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

    metric_by_col = {m.column: m for m in PARETO_METRICS}

    def format_metric_value(column: str, value: float) -> str:
        if column == "proportion_within_coverage_threshold":
            return f"{value * 100:.1f}% covered within 30 min"
        m = metric_by_col[column]
        if m.unit:
            return f"{value:.1f} {m.unit} ({m.label})"
        return f"{value:.2f} ({m.label})"

    champions = objective_champions(solution_df_ranking, site_col="site")
    spreads = metric_spreads(solution_df_ranking)
    compromises = compromise_options(solution_df_ranking, site_col="site")
    n_total = len(solution_df_ranking)
    n_front = int(solution_df_ranking["is_pareto_optimal"].sum())

    st.markdown(
        f"The optimiser compared all **{n_total}** possible combinations against "
        f"**{len(PARETO_METRICS)}** different measures. **{n_front} of them are "
        "defensible** - nothing else beats them across the board. Each is the "
        "best answer to a different question."
    )

    badge_counts: dict[str, int] = {}
    for champ in champions:
        for badge in champ["badges"]:
            badge_counts[badge] = badge_counts.get(badge, 0) + 1

    for champ in champions:
        with st.container(border=True):
            solo_badges = [b for b in champ["badges"] if badge_counts[b] == 1]
            joint_badges = [b for b in champ["badges"] if badge_counts[b] > 1]
            badge_parts = []
            if solo_badges:
                badge_parts.append("best for " + ", ".join(solo_badges))
            if joint_badges:
                badge_parts.append("joint best for " + ", ".join(joint_badges))

            st.markdown(
                f":material/location_on: **{champ['site']}** — "
                + "; ".join(badge_parts)
            )

            badge_cols = [
                m.column for m in PARETO_METRICS if m.label in champ["badges"]
            ]
            st.caption(
                " · ".join(
                    format_metric_value(col, champ["values"][col])
                    for col in badge_cols
                )
            )

            weakest_label, weakest_rank, weakest_n = champ["weakest"]
            st.caption(
                f"Gives ground on: {weakest_label} "
                f"({ordinal(weakest_rank)} of {weakest_n})"
            )

    if compromises:
        plural = len(compromises) != 1
        st.caption(
            f"{len(compromises)} further combination{'s' if plural else ''} "
            f"{'are' if plural else 'is'} never beaten across the board, but not "
            "the best at any single measure either."
        )

    # Flagged by an outright tie for the best value, not by the raw spread -
    # spread is in different units per metric (minutes vs a 0-1 proportion vs
    # a ratio), so a single absolute threshold would flag every proportion-
    # or ratio-based metric as "flat" regardless of whether it actually
    # separates the field. A genuine tie for best is scale-independent: it
    # means the badge doesn't even uniquely distinguish one option.
    flat_spreads = [
        (metric_by_col[col].label, s)
        for col, s in spreads.items()
        if s["n_tied_at_best"] > 1
    ]
    if flat_spreads:
        flat_bits = "; ".join(
            f"{label} varies by only {s['spread']:.2f} across all {n_total} options, "
            f"with {s['n_tied_at_best']} tied for best"
            for label, s in flat_spreads
        )
        st.caption(
            f"Worth noting: {flat_bits}. A badge on a measure this flat is worth "
            "less than one on a measure that genuinely separates the field."
        )

    champion_sites = {c["site"] for c in champions}
    selected_row = solution_df_ranking[solution_df_ranking["site"] == selected_site].iloc[0]

    if selected_site in champion_sites:
        selected_badges = next(
            c["badges"] for c in champions if c["site"] == selected_site
        )
        st.info(
            f"Your choice, **{selected_site}**, is one of the shortlisted options above - "
            f"it's best for {', '.join(selected_badges)}."
        )
    elif selected_row["is_pareto_optimal"]:
        st.info(
            f"Your choice, **{selected_site}**, is on the shortlist of defensible options - "
            "nothing beats it across the board - but it isn't the best at any single measure."
        )
    else:
        n_dominators = len(selected_row["dominated_by"])
        st.warning(
            f"Your choice, **{selected_site}**, is beaten outright by "
            f"{n_dominators} other combination{'s' if n_dominators != 1 else ''} - "
            "at least one alternative does at least as well on every measure, and "
            "better on some."
        )

    st.divider()

    weighted = ordinal(
        get_solution_rank(
            solution_df_ranking, selected_site, "weighted_average", ascending=True
        )
    )
    average = ordinal(
        get_solution_rank(
            solution_df_ranking, selected_site, "unweighted_average", ascending=True
        )
    )
    p90 = ordinal(
        get_solution_rank(
            solution_df_ranking, selected_site, "90th_percentile", ascending=True
        )
    )
    maximum = ordinal(
        get_solution_rank(solution_df_ranking, selected_site, "max", ascending=True)
    )
    coverage = ordinal(
        get_solution_rank(
            solution_df_ranking,
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
                ],
                format_func=lambda m: RANK_METRIC_LABELS[m].capitalize(),
                horizontal=True,
            )
            col1, col2 = st.columns(2)

            with col1:
                st.subheader(f"Best Solution Based on {RANK_METRIC_LABELS[sort_by]}")
                ax = solution.plot_best_combination(
                    solution_rank=1,
                    sort_by=sort_by,
                    plot_regions_not_meeting_threshold=True
                    if sort_by == "proportion_within_coverage_threshold"
                    else False,
                )
                st.pyplot(ax.figure)
            with col2:
                st.subheader("Your Selected Solution")
                ax = solution.plot_best_combination(
                    solution_rank=get_solution_rank(
                        solution_df_ranking,
                        selected_site,
                        sort_by,
                        ascending=RANK_METRIC_ASCENDING[sort_by],
                    ),
                    plot_regions_not_meeting_threshold=True
                    if sort_by == "proportion_within_coverage_threshold"
                    else False,
                    sort_by=sort_by,
                )
                st.pyplot(ax.figure)

        plot_best_sols()

    with tab_4:
        # Select only the columns actually shown before handing off to
        # st.dataframe - it Arrow-serialises every column of whatever frame
        # it's given (even ones excluded via column_order below), and
        # solution_df_display still carries dict-valued equity-group columns
        # that Arrow can't represent, which otherwise raises a (recovered,
        # but noisy) conversion warning.
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

    st.divider()
    st.subheader("But wait...")
    if st.button(
        "Yet another person runs into the room...",
        key="btn_continue_optimise_6",
        icon=":material/celebration:",
        width="stretch",
    ):
        st.switch_page("app/Optimise_6_Sites.py")
