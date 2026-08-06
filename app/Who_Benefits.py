from pathlib import Path
import streamlit as st
import pickle
from lokigi.site_solutions import SolutionComparator
from app.utils import (
    page_styling,
    write_terminal_html,
    load_devon_sites,
    evaluate_car_baseline,
    MEANINGFUL_CHANGE_MINUTES,
    RANK_METRIC_PANEL_CAPTION,
    _overlay_solution_sites,
)

st.set_page_config(initial_sidebar_state="expanded", layout="wide")
page_styling()

st.title("Who Actually Benefits?")

if st.session_state.confirmed_site_final is not None:
    selected_site = st.session_state.confirmed_site_final
else:
    st.error("No site selected. Falling back to default.")
    selected_site = "Tiverton - Lowman Way"


# Same name and body as Optimise_5_Sites.py's own load_car_5_solution() -
# every page script runs under the module name "__main__", so this
# deliberately hits the same @st.cache_resource entry rather than loading
# (and mutating) a second copy of the ~2MB pickle. That's the wanted
# behaviour here, unlike Optimise_6_Sites.py's load_car_5_solution_df():
# this page needs the same solution Optimise_5 already showed, not an
# independent copy.
@st.cache_resource
def load_car_5_solution():
    with open("data/solution_car_5.pkl", "rb") as f:
        return pickle.load(f)


solution = load_car_5_solution()

existing_sites = load_devon_sites()
existing_sites = existing_sites[existing_sites["Existing"] == "Yes"][
    "Facility_Name"
].to_list()

baseline = evaluate_car_baseline()

intro_text = """
> "The shortlist tells you who's defensible," your analyst says. "It doesn't tell you who actually benefits, or by how much, or whether the people already worst off are among them."
<br><br>
> "A region-wide average can hide a large, concentrated effect just as easily as it can hide nothing at all. Let's find out which one you're looking at - for your choice, and for the optimiser's own pick."
"""

write_terminal_html(
    intro_text,
    output_path="app/assets/terminal_working/who_benefits.html",
)
st.iframe(Path("app/assets/terminal_working/who_benefits.html"), height=200)

config_user = {"site_names": existing_sites + [selected_site]}
comp_user = SolutionComparator(
    baseline, solution, labels=("Today", f"Your choice ({selected_site})")
)

st.subheader(f"Your choice: {selected_site}")
st.markdown(
    comp_user.decision_summary(
        meaningful_change_threshold=MEANINGFUL_CHANGE_MINUTES,
        config_b=config_user,
        worst_affected_n=3,
    )
)

impact_user = comp_user.population_impact_summary(
    meaningful_change_threshold=MEANINGFUL_CHANGE_MINUTES,
    config_b=config_user,
    as_dict=True,
)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(
        "People with a meaningfully shorter journey",
        f"{impact_user['demand_improved']:,.0f}",
    )
    st.caption(f"{impact_user['proportion_demand_improved']:.1%} of the population.")
with col2:
    st.metric(
        "Avg. minutes saved for those who benefit",
        f"{impact_user['mean_reduction_among_improved']:.1f}",
    )
with col3:
    st.metric("Largest single saving", f"{impact_user['max_reduction']:.1f} min")
with col4:
    st.metric("Regions with a shorter journey", f"{impact_user['regions_improved']:,}")

st.divider()
st.subheader("Where does the benefit actually land?")

map_col, hist_col = st.columns(2)
with map_col:
    fig_map, ax_map = comp_user.plot_population_impact_map(
        direction="improved",
        meaningful_change_threshold=MEANINGFUL_CHANGE_MINUTES,
        config_b=config_user,
        title=None,
    )
    _overlay_solution_sites(
        ax_map, solution.site_problem, existing_sites + [selected_site]
    )
    st.pyplot(fig_map)
    st.caption(RANK_METRIC_PANEL_CAPTION["proportion_demand_improved"])
with hist_col:
    fig_hist, ax_hist = comp_user.plot_population_impact_histogram(
        config_b=config_user,
        kind="kde",
        title=None,
        caption="",
    )
    ax_hist.set_xlabel("Travel time to nearest site (minutes)")
    legend = ax_hist.get_legend()
    if legend is not None:
        for text in legend.get_texts():
            text.set_fontsize(8)
    st.pyplot(fig_hist)
    st.caption(RANK_METRIC_PANEL_CAPTION["mean_reduction_among_improved"])

st.divider()
st.subheader("Is the benefit spread evenly by deprivation?")
st.caption(
    "Share of each deprivation band's *own* population - not a raw headcount - "
    "with a meaningfully shorter journey. A candidate can win on the region-wide "
    "average while barely moving the most deprived deciles, or even leaving some "
    "of them worse off; both bars are shown for every band so that wouldn't be hidden."
)
fig_equity, _ = comp_user.plot_population_impact_by_equity_group(
    meaningful_change_threshold=MEANINGFUL_CHANGE_MINUTES,
    config_b=config_user,
)
st.pyplot(fig_equity)

st.divider()
st.subheader("Whose caseload does the new site actually relieve?")
st.caption(
    "Read this alongside \"How well-used are existing CDCs?\" - NHS Nightingale "
    "Exeter is already running over its weekly capacity today (1,590 against "
    "1,500). If the new site's column below draws demand away from Exeter "
    "specifically, that's a capacity story no travel-time metric captures on its "
    "own; if it draws from elsewhere, Exeter's capacity problem is untouched."
)
fig_realloc, _ = comp_user.plot_site_reallocation_matrix(
    config_b=config_user, changed_only=True
)
st.pyplot(fig_realloc)

st.divider()
st.subheader("Your choice vs. the optimiser's own pick")

best_row = solution.return_best_combination_details()
best_site = next(
    s for s in best_row["site_names"].iloc[0] if s not in existing_sites
)

if best_site == selected_site:
    st.info(
        f"The optimiser's own top-ranked pick is the same site you chose - "
        f"**{selected_site}**. Nothing to compare here."
    )
else:
    config_best = {"solution_rank": 1}
    comp_best = SolutionComparator(
        baseline, solution, labels=("Today", f"The optimiser's pick ({best_site})")
    )
    impact_best = comp_best.population_impact_summary(
        meaningful_change_threshold=MEANINGFUL_CHANGE_MINUTES,
        config_b=config_best,
        as_dict=True,
    )

    user_col, best_col = st.columns(2)
    with user_col:
        st.markdown(f"**Your choice: {selected_site}**")
        st.metric(
            "People with a meaningfully shorter journey",
            f"{impact_user['demand_improved']:,.0f}",
            f"{impact_user['proportion_demand_improved']:.1%} of the population",
        )
        st.metric(
            "Avg. minutes saved for those who benefit",
            f"{impact_user['mean_reduction_among_improved']:.1f}",
        )
    with best_col:
        st.markdown(f"**The optimiser's pick: {best_site}**")
        st.metric(
            "People with a meaningfully shorter journey",
            f"{impact_best['demand_improved']:,.0f}",
            f"{impact_best['proportion_demand_improved']:.1%} of the population",
        )
        st.metric(
            "Avg. minutes saved for those who benefit",
            f"{impact_best['mean_reduction_among_improved']:.1f}",
        )

st.divider()
st.warning(
    "**Nobody's journey gets longer on this page, and that is not a finding - "
    "it's an artefact of the question.** We only ever *added* a site, and adding "
    "can't push anyone further from their nearest centre. The moment a real "
    "service change closes or moves something, this same analysis fills with "
    "red, and \"how many people are worse off, and who are they?\" becomes the "
    "first question anyone should ask.",
    icon=":material/warning:",
)

st.divider()
if st.button(
    "Yet another person runs into the room...",
    key="btn_continue_optimise_6",
    icon=":material/celebration:",
    width="stretch",
):
    st.switch_page("app/Optimise_6_Sites.py")
