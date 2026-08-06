import pandas as pd
import numpy as np
import streamlit as st
import geopandas
import html
import re
from app.utils_investigations import ALL_INVESTIGATIONS, Investigation
import base64
from PIL import Image
from io import BytesIO
from pathlib import Path
import os
from lokigi.site import SiteProblem
from lokigi.site_solutions import SolutionComparator
from lokigi.multiobjective import Metric
from matplotlib.transforms import Bbox
from matplotlib.colors import ListedColormap
import matplotlib.pyplot as plt

TERMINAL_DEFAULT_SPEED = 10
TERMINAL_COLOUR = "yellow"
MAXIMUM_BRIEFINGS = 6

# What counts as a "meaningfully" shorter journey when comparing a candidate
# network against today's. 5 minutes, not 0 - at 0 the metric degenerates into
# "everyone who would switch to the new site", which is a catchment headcount
# dressed up as an improvement measure.
MEANINGFUL_CHANGE_MINUTES = 5.0
COVERAGE_THRESHOLD_MINUTES = 30
LEFT_BEHIND_THRESHOLDS = [45, 60]

# Shared basemap for every folium/leaflet map in the app, so switching styles
# only requires changing this one value. CartoDB Voyager keeps roads/labels
# visible (unlike Positron) while staying more muted than default OpenStreetMap.
BASEMAP_TILES = "cartodbvoyager"

# Which direction "best" sorts in for each optimiser solution_df metric - lower
# is better for every travel-time-style column, higher is better for coverage.
# Used on the Optimise pages so a rank looked up externally (e.g. "where does
# my chosen site fall for this metric?") lines up with lokigi's own internal
# ranking convention in SiteSolutionSet.plot_best_combination (documented as
# "highest for coverage proportions, lowest for travel costs").
RANK_METRIC_ASCENDING = {
    "weighted_average": True,
    "unweighted_average": True,
    "90th_percentile": True,
    "max": True,
    "proportion_within_coverage_threshold": False,
    "inter_tertile_ratio": True,
    "proportion_demand_improved": False,
    "mean_reduction_among_improved": False,
    "demand_beyond_threshold_45": True,
}

# Human-readable phrasing for each optimiser metric column, for embedding in
# sentences (lower-case) or as st.radio options (via .capitalize()). Keeps
# raw pandas column names like "proportion_within_coverage_threshold" off the
# screen - they're meaningful to whoever wrote the analysis, not the exec
# reading the page.
RANK_METRIC_LABELS = {
    "weighted_average": "weighted average travel time",
    "unweighted_average": "unweighted average travel time",
    "90th_percentile": "90th percentile travel time",
    "max": "maximum travel time",
    # Names the actual cutoff rather than "the travel time threshold": this
    # metric and demand_beyond_threshold_45 below are both threshold measures
    # and both draw a two-colour map, so without the numbers in the labels the
    # only thing telling them apart on screen is which map is on the tab.
    "proportion_within_coverage_threshold": (
        f"coverage within {COVERAGE_THRESHOLD_MINUTES} minutes"
    ),
    "inter_tertile_ratio": "equity (inter-tertile ratio)",
    "proportion_demand_improved": "people with a meaningfully shorter journey",
    "mean_reduction_among_improved": "minutes saved for those who benefit",
    "demand_beyond_threshold_45": "people still more than 45 minutes away",
}

# How each "rank on" metric's own value should read in a plot title, keyed by
# the same columns as RANK_METRIC_LABELS above. Each formatter takes one row
# of solution_df and returns just the value part of the line.
#
# These exist because lokigi's default plot title can't report the metric the
# Optimise pages' radio actually selected: it reports SiteSolutionSet.
# ranking_metric, the Metric frozen into the pickle by solve(rank_on=...), so
# every title read "Ranked on Proportion demand improved: 0.1" no matter what
# the user picked - a raw 0-1 proportion at 1dp, for a metric they hadn't
# chosen. See best_combination_title() below.
#
# Plain formatters rather than more lokigi Metric objects (as in
# PARETO_METRICS) because Metric.format_value() renders a headcount as
# "49306" - no thousands separator, which is exactly what makes a
# population number hard to read at a glance.
#
# Proportions carry their absolute headcount alongside them: "10.0%" of Devon
# is a number nobody can act on until it's also "52,140 people".
RANK_METRIC_TITLE_VALUE = {
    "weighted_average": lambda row: f"{row['weighted_average']:.1f} minutes",
    "unweighted_average": lambda row: f"{row['unweighted_average']:.1f} minutes",
    "90th_percentile": lambda row: f"{row['90th_percentile']:.1f} minutes",
    "max": lambda row: f"{row['max']:.1f} minutes",
    "proportion_within_coverage_threshold": lambda row: (
        f"{row['proportion_within_coverage_threshold']:.1%} "
        f"({row['demand_within_coverage_threshold']:,.0f} people)"
    ),
    "inter_tertile_ratio": lambda row: f"{row['inter_tertile_ratio']:.2f}",
    "proportion_demand_improved": lambda row: (
        f"{row['proportion_demand_improved']:.1%} "
        f"({row['demand_improved']:,.0f} people)"
    ),
    "mean_reduction_among_improved": lambda row: (
        f"{row['mean_reduction_among_improved']:.1f} minutes"
    ),
    "demand_beyond_threshold_45": lambda row: (
        f"{row['demand_beyond_threshold_45']:,.0f} people"
    ),
}


# Order of the "Rank On..." radio on the Solution Comparison tab, shared by
# both Optimise pages. Deliberately not RANK_METRIC_LABELS' own order: the two
# threshold measures sit next to each other, so the reader meets "coverage
# within 30 minutes" and "people still more than 45 minutes away" as an
# obvious pair of related questions rather than stumbling on the second one
# four options later and taking it for a repeat of the first.
SOLUTION_COMPARISON_METRICS = [
    "weighted_average",
    "unweighted_average",
    "90th_percentile",
    "max",
    "proportion_within_coverage_threshold",
    f"demand_beyond_threshold_{LEFT_BEHIND_THRESHOLDS[0]}",
    "inter_tertile_ratio",
    "proportion_demand_improved",
    "mean_reduction_among_improved",
]

# Columns summarised in the "your solution is the Nth best..." bullet list on
# each Optimise page. A deliberate subset of RANK_METRIC_LABELS - narrower
# than the tab-1 "rank on" radio (which also offers inter_tertile_ratio and
# mean_reduction_among_improved) because this bullet list is meant to be
# skimmed as one paragraph, not read as a full menu of every measure the
# optimiser can rank on.
ORDINAL_RANK_SUMMARY_METRICS = [
    "weighted_average",
    "unweighted_average",
    "90th_percentile",
    "max",
    "proportion_within_coverage_threshold",
    "proportion_demand_improved",
    "demand_beyond_threshold_45",
]

# The multi-objective metric set used on the Optimise pages, both for the
# lokigi Pareto-front computation and for the objective-champion shortlist
# that replaces a single "best on weighted average travel time" headline.
# Defined once here rather than copy-pasted per page so the two Optimise
# pages and the shortlist helpers below always agree on what "an objective"
# means.
#
# weighted_average stays in deliberately: the page becomes a story about it
# losing an argument to the other measures, not about it being quietly
# dropped. max and proportion_within_coverage_threshold are not - they
# remain available on the tab-1 "rank on" radio and in the results table,
# but a p-median average and a threshold count don't tell you anything about
# *how many people* actually benefit, which is the point of this shortlist.
#
# proportion_demand_improved (people with a meaningfully shorter journey,
# see MEANINGFUL_CHANGE_MINUTES) is the replacement headline: it and
# weighted_average can and do disagree, because a site can shave a little
# off everyone's average while changing almost nobody's actual journey.
#
# mean_reduction_among_improved (minutes saved for those who benefit) is
# deliberately left OUT of this Pareto set, though it's still offered on the
# tab-1 radio and shown in the results table. Including it pushed the
# defensible shortlist from 5/14 to 9/14 on the 5-site solution (24/91 on
# the 6-site one) - too large a fraction of the field to read as a punchy
# "these are the contenders" shortlist. Dropping it restores a tighter
# 4/14 and 5/91 (verified against the regenerated pickles).
#
# inter_tertile_ratio is deliberately scored "lower is better", not "closest
# to 1.0" - this is a stance, not just a modelling default. It rewards
# actively reducing travel time for the most deprived group relative to the
# least deprived (progressive universalism), rather than treating perfect
# evenness as the ideal. Scoring it against a target of 1.0 instead would
# both change which options make the shortlist and loosen the Pareto front
# considerably (verified: 9/14 vs 4/14 on the 5-site solution).
PARETO_METRICS = [
    Metric(
        column="weighted_average",
        direction="lower_better",
        label="average travel time",
        unit="minutes",
    ),
    Metric(
        column="proportion_demand_improved",
        direction="higher_better",
        label="people with a meaningfully shorter journey",
        as_percentage=True,
    ),
    Metric(
        column="inter_tertile_ratio",
        direction="lower_better",
        label="equity (inter-tertile ratio)",
        # 2dp, not Metric's default 1dp: the whole ratio sits in a narrow
        # band around parity (0.83-1.06 across the 6-site combinations), so
        # at 1dp most options collapse onto "0.9" or "1.0" and a card can
        # claim a site is 12th of 14 on a measure reading exactly what the
        # winner reads. Matches the 2dp used in the Solution Breakdown table
        # and the map titles.
        decimals=2,
    ),
    Metric(
        column="avg_lower_third_bins",
        direction="lower_better",
        label="travel time for the most deprived third",
        unit="minutes",
    ),
]


def metric_spreads(
    solution_df: pd.DataFrame, metrics: list[Metric] = PARETO_METRICS
) -> dict[str, dict]:
    """
    For each metric, how much the enumerated solutions actually differ.

    Returns {column: {"min", "max", "spread", "n_tied_at_best"}}. Used to
    flag objectives where the "best" option only just edges out a crowd of
    others tied right behind it (or ties with several others outright) - a
    badge on a measure like that is worth less than one on a measure that
    genuinely separates the field.
    """
    spreads = {}
    for m in metrics:
        col = solution_df[m.column]
        best = col.min() if m.direction != "higher_better" else col.max()
        spreads[m.column] = {
            "min": col.min(),
            "max": col.max(),
            "spread": col.max() - col.min(),
            "n_tied_at_best": int(np.isclose(col, best).sum()),
        }
    return spreads


def objective_champions(
    solution_df: pd.DataFrame,
    site_col: str = "site",
    metrics: list[Metric] = PARETO_METRICS,
) -> list[dict]:
    """
    Find, for each objective, every solution tied for the best value on it,
    then group by site so a solution that wins on several objectives at
    once appears once with all its badges attached.

    Requires `solution_df["is_pareto_optimal"]` to already be set (i.e.
    `solution.compute_pareto_front(metrics=...)` has run) - champions are
    Pareto-optimal by construction (nothing beats the best value on its own
    winning metric), but this asserts it rather than assuming it, since an
    exact tie on every metric is the one edge case where it could fail.

    Returns a list of dicts, one per champion site, each with:
    - "site": the site name (or joined site names for multi-site solutions)
    - "badges": list of metric labels this site is (jointly) best on
    - "values": {column: raw value} for every metric, for display
    - "weakest": (label, rank, n, column) for the metric this site ranks
      worst on - the column is carried so the caller can pull that metric's
      own value out of "values" and render it in the metric's units

    Ordered by number of badges (most first), then by weighted_average, so
    the strongest all-rounder leads and ties resolve deterministically.
    """
    champions: dict[str, dict] = {}

    for m in metrics:
        best = (
            solution_df[m.column].min()
            if m.direction != "higher_better"
            else solution_df[m.column].max()
        )
        winners = solution_df[np.isclose(solution_df[m.column], best)]
        for _, row in winners.iterrows():
            site = row[site_col]
            entry = champions.setdefault(
                site,
                {
                    "site": site,
                    "badges": [],
                    "values": {mm.column: row[mm.column] for mm in metrics},
                    "_row": row,
                },
            )
            entry["badges"].append(m.label)

    ranks = pd.DataFrame(
        {
            m.column: solution_df[m.column].rank(
                method="min", ascending=(m.direction != "higher_better")
            )
            for m in metrics
        },
        index=solution_df.index,
    )
    n_total = len(solution_df)

    for site, entry in champions.items():
        row_idx = entry["_row"].name
        row_ranks = ranks.loc[row_idx]
        weakest_col = row_ranks.idxmax()
        weakest_label = next(m.label for m in metrics if m.column == weakest_col)
        entry["weakest"] = (
            weakest_label,
            int(row_ranks[weakest_col]),
            n_total,
            weakest_col,
        )
        assert bool(entry["_row"].get("is_pareto_optimal", True)), (
            f"Champion '{site}' is not Pareto-optimal - unexpected unless "
            "every metric is tied across the whole solution set."
        )
        del entry["_row"]

    return sorted(
        champions.values(),
        key=lambda e: (-len(e["badges"]), e["values"]["weighted_average"]),
    )


def compromise_options(
    solution_df: pd.DataFrame,
    site_col: str = "site",
    metrics: list[Metric] = PARETO_METRICS,
) -> list[str]:
    """
    Pareto-optimal solutions that are not the (joint) best on any single
    objective - never beaten across the board, but not the champion of
    anything either. Empty whenever the champion set already covers the
    whole Pareto front (verified true for the 5-site solution; the 6-site
    solution has 6 such compromise options alongside its 5 champions).
    """
    champion_sites = {
        c["site"] for c in objective_champions(solution_df, site_col, metrics)
    }
    front = solution_df[solution_df["is_pareto_optimal"]]
    return [s for s in front[site_col] if s not in champion_sites]


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

    kind="mergesort" (stable) because this rank is handed straight back to
    lokigi as `plot_best_combination(solution_rank=...)`, which sorts with
    mergesort internally. Ties are routine here - `max` takes only 2 distinct
    values across the 14 five-site combinations - and pandas' default
    quicksort is not stable, so the two orderings disagreed within a tie
    group and the "your selected solution" panel plotted a different site
    than the heading above it named.
    """
    sorted_df = solution_df.sort_values(
        metric, ascending=ascending, kind="mergesort"
    ).reset_index(drop=True)

    matches = sorted_df.index[sorted_df["site"] == selected_site]

    if len(matches) == 0:
        raise ValueError(f"'{selected_site}' not found in dataframe.")

    return matches[0] + 1


def format_metric_value(metric: Metric, value: float) -> str:
    """
    Render one metric's value with its label for a champion-badge caption,
    e.g. "23.4 minutes (average travel time)". Delegates the number
    formatting itself to Metric.format_value(), which already knows how to
    render a percentage vs. a unit vs. a bare ratio.
    """
    return f"{metric.format_value(value)} ({metric.label})"


def best_combination_title(
    solution_row: pd.Series,
    sort_by: str,
    n_sites: int,
    solution_rank: int = 1,
) -> str:
    """
    Build the title for one of the side-by-side maps on the Optimise pages,
    replacing lokigi's default (which names whichever metric solve() ranked
    on, not the one the page's "Rank On..." radio is currently set to).

    `solution_row` must be the row lokigi actually plotted - fetch it with
    SiteSolutionSet.return_best_combination_details(sort_by=..., top_n=rank)
    so it goes through lokigi's own ordering rather than a second sort here.

    Reads e.g.:

        3rd best solution for 5 sites
        Ranked on people with a meaningfully shorter journey: 10.0% (52,140 people)
        Weighted Average: 22.1 minutes
        Maximum: 61.2 minutes
    """
    if solution_rank == 1:
        prefix = f"Best solution for {n_sites} sites"
    else:
        prefix = f"{ordinal(solution_rank)} best solution for {n_sites} sites"

    # Name the sites this combination actually adds. "Best solution for 5
    # sites" is true of every panel on the page - what distinguishes one
    # combination from another is the one (or two) new sites on top of the
    # existing network, and the map only says so via a pin label the reader
    # has to hunt for among the required sites' labels.
    #
    # additional_site_names is lokigi's own list of the non-required sites in
    # the combination, so this stays correct without the page having to pass
    # in which sites are existing.
    # One added site goes inline; two or more get a line each. Facility names
    # here run to 40-odd characters ("Okehampton - Exeter Road Industrial
    # Estate"), so "adds A and B" on one line makes the title wider than the
    # map under it - and since st.pyplot scales the saved figure to its
    # column width, a wider title means a visibly smaller map in each of the
    # two side-by-side columns.
    added = list(solution_row.get("additional_site_names", []) or [])
    added_lines = []
    if len(added) == 1:
        prefix = f"{prefix}: adds {added[0]}"
    elif added:
        added_lines = [f"adds {added[0]}"] + [f"and {name}" for name in added[1:]]

    ranked_on = (
        f"Ranked on {RANK_METRIC_LABELS[sort_by]}: "
        f"{RANK_METRIC_TITLE_VALUE[sort_by](solution_row)}"
    )

    lines = [prefix, *added_lines, ranked_on]

    # The two context lines lokigi shows for a p-median objective, kept so
    # both panels stay comparable on the standard measures - minus whichever
    # one the ranked-on line has already just reported, so the same number
    # never appears twice in consecutive lines.
    if sort_by != "weighted_average":
        lines.append(
            f"Weighted Average: {solution_row['weighted_average']:.1f} minutes"
        )
    if sort_by != "max":
        lines.append(f"Maximum: {solution_row['max']:.1f} minutes")

    # Mirrors lokigi's own _unreachable_metrics_fragment: the travel-time
    # metrics above are computed over reachable demand only, so a demand
    # location with no feasible journey would otherwise vanish from the
    # summary with nothing to say it had been excluded. 0 across every row of
    # both current solution pickles - kept so a regenerated solve that does
    # have unreachable regions can't silently lose the caveat.
    n_unreachable = int(solution_row["regions_unreachable"])
    if n_unreachable:
        region_word = "region" if n_unreachable == 1 else "regions"
        lines.append(f"{n_unreachable} {region_word} unreachable")

    return "\n".join(lines)


# Explanatory captions for the Solution Comparison panels whose plot isn't a
# plain travel-time map. Each one says what the colours mean, since none of
# these plots carries that in a legend.
RANK_METRIC_PANEL_CAPTION = {
    "proportion_within_coverage_threshold": (
        f"**Red** areas are further than {COVERAGE_THRESHOLD_MINUTES} minutes from "
        "their nearest site; **blue** areas are within it. This is the "
        f"{COVERAGE_THRESHOLD_MINUTES}-minute question - see "
        f"\"people still more than {LEFT_BEHIND_THRESHOLDS[0]} minutes away\" for the "
        "same map drawn at the point where distance stops being an inconvenience "
        "and starts being a reason not to go."
    ),
    "proportion_demand_improved": (
        "Only the areas whose journey actually gets meaningfully shorter are "
        f"coloured - at least {MEANINGFUL_CHANGE_MINUTES:.0f} minutes off today's "
        "travel time. Grey is everywhere the new site changes nothing. Darker blue "
        "means a bigger saving. Watch the area-versus-people trap here: Devon's "
        "rural areas are large and sparsely populated, so a big patch of blue can "
        "be far fewer people than a small one over a town. The headcount in the "
        "title is the number that counts."
    ),
    "mean_reduction_among_improved": (
        "Journey times across Devon today against journey times with the new site, "
        "weighted by population. Height is the **share** of people at that journey "
        "time, not a headcount - the area under each curve is the whole population, "
        "so the two curves are directly comparable even though only some people "
        "move. The dashed lines mark each side's average. Most of Devon is "
        "unaffected, so the curves overlap heavily: the gap between them is the "
        "whole benefit. Note too that a large improved area on the map for "
        "\"people with a meaningfully shorter journey\" may be very few people - "
        "this view is by people, that one is by area."
    ),
    "inter_tertile_ratio": (
        "Average travel time for each deprivation decile, most deprived first, "
        "weighted by population. The dashed lines are the two numbers the ratio "
        "divides: the **most deprived third** (deciles 1-4) over the **least "
        "deprived third** (deciles 8-10). Below 1 means the most deprived travel "
        "less far on average. The shape across the bars matters as much as the "
        "ratio - deprivation isn't geographically tidy, so no map can show you this."
    ),
    f"demand_beyond_threshold_{LEFT_BEHIND_THRESHOLDS[0]}": (
        f"**Orange** areas are still more than {LEFT_BEHIND_THRESHOLDS[0]} minutes "
        "from their nearest site once the new site opens; **blue** areas are within "
        "it. The same picture, and the same colours, as the Left Behind page - but "
        f"after the money has been spent. Note this is a longer cutoff than the "
        f"{COVERAGE_THRESHOLD_MINUTES}-minute coverage map, so more of Devon "
        "qualifies as within it."
    ),
}


# Two-colour scheme for the "still more than 45 minutes away" map,
# deliberately different from the red/blue lokigi draws the 30-minute coverage
# map in - the two panels answer different questions and shouldn't look
# interchangeable. These are the same orange/blue the Travel by Car and Left
# Behind pages already use for their own threshold maps, so a reader meets
# this palette as "the left-behind map" they have seen before.
LEFT_BEHIND_BEYOND_COLOUR = "#ef8a62"
LEFT_BEHIND_WITHIN_COLOUR = "#67a9cf"

# Colours for the equity panel's bars: the most-deprived third, the middle,
# and the least-deprived third. The two ends are what the inter-tertile ratio
# actually divides, so they carry colour and the middle stays neutral.
EQUITY_MOST_DEPRIVED_COLOUR = "#c2603f"
EQUITY_MIDDLE_COLOUR = "#c9c9c9"
EQUITY_LEAST_DEPRIVED_COLOUR = "#3f7fa8"


def _equity_tertile_bands(bands):
    """
    Split sorted equity bands into (most-deprived, middle, least-deprived)
    thirds, matching how lokigi computes avg_lower_third_bins /
    avg_upper_third_bins - `np.array_split` into three chunks, lowest IMD
    decile first (this repo registers every problem with
    `disadvantaged_end="low"`, i.e. decile 1 = most deprived).

    With Devon's ten deciles that is 1-4 / 5-7 / 8-10, NOT the even 1-3 /
    4-7 / 8-10 the phrase "tertile" suggests - array_split puts the
    remainder in the first chunk. Verified against the solution pickles:
    averaging the demand-weighted band means over these exact chunks
    reproduces avg_lower_third_bins and avg_upper_third_bins to the decimal.
    """
    return [list(chunk) for chunk in np.array_split(sorted(bands), 3)]


def _plot_equity_tertiles(row):
    """
    Bar chart behind the inter-tertile ratio: demand-weighted average travel
    time for each IMD decile, most deprived first, with the two tertile
    averages the ratio is actually built from drawn across their own bars.

    The ratio on its own is a single number around 1 whose direction most
    readers have to stop and reason about ("is lower better here?"). The
    shape it summarises - whether travel time climbs or falls as deprivation
    falls - is the thing worth seeing, and a travel-time map can't show it at
    all, since deprivation isn't geographically contiguous.

    Reads the per-band values straight off the solution row
    (`weighted_by_equity_group`), the same demand-weighted numbers lokigi
    averages into the metric, rather than recomputing an unweighted mean per
    band - which is what `check_solution_equity()` plots, and differs enough
    (band 3: 18.8 weighted vs 16.5 unweighted) that a reader adding the bars
    up would not get the ratio in the title.
    """
    per_band = row["weighted_by_equity_group"]
    most, middle, least = _equity_tertile_bands(per_band)
    ordered = most + middle + least

    colours = (
        [EQUITY_MOST_DEPRIVED_COLOUR] * len(most)
        + [EQUITY_MIDDLE_COLOUR] * len(middle)
        + [EQUITY_LEAST_DEPRIVED_COLOUR] * len(least)
    )

    _, ax = plt.subplots(figsize=(9, 6))
    ax.bar(
        range(len(ordered)),
        [per_band[b] for b in ordered],
        color=colours,
        edgecolor="white",
    )
    ax.set_xticks(range(len(ordered)))
    ax.set_xticklabels([str(b) for b in ordered])
    ax.set_xlabel("IMD decile (1 = most deprived), most to least deprived")
    ax.set_ylabel("Average travel time (minutes)")

    # The two numbers the ratio divides, drawn only across the bars they
    # average, so it reads as "these bars against those bars".
    for label, bands, value, colour in (
        (
            "most deprived third",
            most,
            row["avg_lower_third_bins"],
            EQUITY_MOST_DEPRIVED_COLOUR,
        ),
        (
            "least deprived third",
            least,
            row["avg_upper_third_bins"],
            EQUITY_LEAST_DEPRIVED_COLOUR,
        ),
    ):
        start = ordered.index(bands[0]) - 0.5
        ax.hlines(
            value,
            start,
            start + len(bands),
            color=colour,
            linestyle="--",
            linewidth=2,
        )
        ax.annotate(
            f"{label}: {value:.1f} min",
            (start + len(bands) / 2, value),
            textcoords="offset points",
            # Clear of the line rather than sitting on it, with a backing box
            # so it stays legible where it crosses a bar.
            xytext=(0, 12),
            ha="center",
            fontsize=9,
            color=colour,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.5, "alpha": 0.85},
        )

    ax.margins(y=0.15)
    return ax


@st.cache_resource
def evaluate_combination_at_threshold(site_names: tuple[str, ...], threshold: float):
    """
    One specific combination of sites, re-evaluated against an arbitrary
    coverage threshold, as a one-solution SiteSolutionSet.

    lokigi's threshold map (`plot_best_combination(
    plot_regions_not_meeting_threshold=True)`) colours regions by the
    `within_threshold` flag computed at solve time - here 30 minutes, the
    coverage threshold the whole solution set was solved against. There is no
    kwarg to redraw it at a different cutoff, and overriding the stored
    threshold would relabel the map without recolouring it. Re-evaluating the
    combination at the threshold we actually want is what makes the colours
    and the label agree.

    `site_names` is a tuple rather than a list so it can be a cache key.
    Verified against the pickled solution set: the 45-minute re-evaluation
    reproduces its `demand_beyond_threshold_45` exactly.
    """
    return setup_lokigi_site_problem_car().evaluate_baseline(
        site_names=list(site_names), threshold_for_coverage=threshold
    )


def _overlay_solution_sites(ax, site_problem, site_names):
    """
    Draw a solution's sites onto a plot that doesn't already show them,
    using the same shapes as lokigi's own maps: triangles for the sites that
    are already open, circles for the ones this solution adds.

    plot_population_impact_map()'s own `show_sites="all"` marks every
    *candidate* site on the problem, open or not, which on this page reads as
    though all fourteen had been built.
    """
    sites = site_problem.candidate_sites
    chosen = sites[sites["Facility_Name"].isin(site_names)]
    existing = chosen[chosen["Existing"] == "Yes"]
    added = chosen[chosen["Existing"] != "Yes"]

    if not existing.empty:
        existing.plot(ax=ax, color="black", marker="^", markersize=45, label="Required sites")
    if not added.empty:
        added.plot(
            ax=ax,
            color="black",
            marker="o",
            markersize=45,
            label="Additional selected sites",
        )
    ax.legend(loc="upper right", fontsize=9)


def solution_panel_figure(solution, sort_by, solution_rank):
    """
    The figure for one side of the Solution Comparison tab's two panels.

    Most metrics get lokigi's travel-time map, but three of them are asking a
    question that map can't answer, and get a purpose-built plot instead:

    - "people with a meaningfully shorter journey" -> where the improvements
      actually land (`plot_population_impact_map(direction="improved")`),
      rather than a travel-time map that looks near-identical whether 8% or
      18% of Devon benefits;
    - "minutes saved for those who benefit" -> the before/after distribution
      of journey times (`plot_population_impact_histogram`), the only view
      that shows the journey times themselves moving;
    - "people still more than 45 minutes away" -> a threshold map drawn at 45
      minutes (see evaluate_combination_at_threshold), not at the 30-minute
      coverage threshold everything else uses.

    The first two compare against today's network via a SolutionComparator,
    with `config_b` picking the same solution `solution_rank`/`sort_by` picks
    for every other panel - cross-checked against solution_df: the comparator
    reports the same demand_improved and mean_reduction_among_improved values
    that the title prints.

    Returns the Figure. The title is set here so every panel is labelled the
    same way whatever it plots.
    """
    plotted_row = solution.return_best_combination_details(
        sort_by=sort_by, top_n=solution_rank
    ).iloc[solution_rank - 1]
    site_names = list(plotted_row["site_names"])
    config_b = {"sort_by": sort_by, "solution_rank": solution_rank}

    n_added = len(list(plotted_row.get("additional_site_names", []) or []))
    comparator = SolutionComparator(
        evaluate_car_baseline(),
        solution,
        labels=(
            "Today's network",
            f"With the new site{'s' if n_added != 1 else ''}",
        ),
    )

    if sort_by == "proportion_demand_improved":
        _, ax = comparator.plot_population_impact_map(
            direction="improved",
            meaningful_change_threshold=MEANINGFUL_CHANGE_MINUTES,
            config_b=config_b,
            title=None,
        )
        _overlay_solution_sites(ax, solution.site_problem, site_names)
    elif sort_by == "mean_reduction_among_improved":
        _, ax = comparator.plot_population_impact_histogram(
            config_b=config_b,
            kind="kde",
            title=None,
            # lokigi writes its own caption into the figure explaining that a
            # KDE's height is a share rather than a headcount. Suppressed here
            # and folded into RANK_METRIC_PANEL_CAPTION below, so all the
            # explanation for a panel sits in one place, styled like the rest
            # of the page, instead of half inside the image.
            caption="",
        )
        # "Travel cost" is the library's internal framing; on this page it is
        # always minutes in a car.
        ax.set_xlabel("Travel time to nearest site (minutes)")
        # Shrink the existing legend in place rather than calling ax.legend()
        # again - lokigi builds it from explicit proxy handles, which a bare
        # ax.legend() can't rediscover, so re-calling it silently replaces a
        # four-entry legend with an empty one.
        legend = ax.get_legend()
        if legend is not None:
            for text in legend.get_texts():
                text.set_fontsize(8)
    elif sort_by == f"demand_beyond_threshold_{LEFT_BEHIND_THRESHOLDS[0]}":
        ax = evaluate_combination_at_threshold(
            tuple(site_names), LEFT_BEHIND_THRESHOLDS[0]
        ).plot_best_combination(
            plot_regions_not_meeting_threshold=True,
            title=None,
            # lokigi takes the first two colours of `cmap` for the two
            # threshold categories, beyond-first - so this is (beyond,
            # within), and it keeps this map visibly distinct from the
            # 30-minute coverage map's red/blue.
            cmap=ListedColormap(
                [LEFT_BEHIND_BEYOND_COLOUR, LEFT_BEHIND_WITHIN_COLOUR]
            ),
        )
    elif sort_by == "inter_tertile_ratio":
        ax = _plot_equity_tertiles(plotted_row)
    else:
        ax = solution.plot_best_combination(
            solution_rank=solution_rank,
            sort_by=sort_by,
            plot_regions_not_meeting_threshold=(
                sort_by == "proportion_within_coverage_threshold"
            ),
            title=None,
        )

    ax.set_title(
        best_combination_title(
            plotted_row,
            sort_by,
            n_sites=solution.n_sites,
            solution_rank=solution_rank,
        ),
        fontsize=12,
    )
    return ax.figure


def shared_map_bbox(*figures):
    """
    One savefig `bbox_inches` box that fits every figure passed in, for
    rendering maps side by side in equal-width columns.

    st.pyplot saves with bbox_inches="tight", which crops each figure to its
    own content - so two maps whose titles differ in length (they always do:
    one names the site the optimiser picked, the other the user's) come out
    as images of different widths. Streamlit then scales each to its column
    width, and the wider image renders shorter, leaving the two maps
    different sizes and vertically out of step. Cropping both to the union
    of their tight boxes makes the saved images pixel-identical in size, so
    they scale to the same height and line up.

    Pass the result to every one of those figures:
    `st.pyplot(fig, bbox_inches=shared_map_bbox(fig_a, fig_b))`.
    """
    return Bbox.union(
        [fig.get_tightbbox(fig.canvas.get_renderer()) for fig in figures]
    )


def render_objective_champions(
    champions: list[dict],
    spreads: dict[str, dict],
    compromises: list[str],
    n_total: int,
    metrics: list[Metric] = PARETO_METRICS,
) -> None:
    """
    Render the objective-champion shortlist as one bordered card per site,
    followed by the compromise-count and flat-spread captions. Shared by
    both Optimise pages so the shortlist looks and reads identically -
    `champions`/`spreads`/`compromises` come from `objective_champions()` /
    `metric_spreads()` / `compromise_options()` above.
    """
    metric_by_col = {m.column: m for m in metrics}

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

            badge_cols = [m.column for m in metrics if m.label in champ["badges"]]
            st.caption(
                " · ".join(
                    format_metric_value(metric_by_col[col], champ["values"][col])
                    for col in badge_cols
                )
            )

            # The value, not just the rank: "3rd of 14" says where this site
            # sits in the field but nothing about how much is actually being
            # given up - 3rd of 14 could be a hair behind the leader or half
            # the benefit. Formatted by the metric itself, so it matches the
            # badge values directly above it (percentage, minutes or ratio).
            weakest_label, weakest_rank, weakest_n, weakest_col = champ["weakest"]
            weakest_metric = metric_by_col[weakest_col]
            weakest_value = weakest_metric.format_value(champ["values"][weakest_col])
            st.caption(
                f"Gives ground on: {weakest_label} "
                f"({ordinal(weakest_rank)} of {weakest_n}, {weakest_value})"
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


def render_ordinal_rank_summary(rank_of) -> None:
    """
    Render the "Your solution is the Nth best..." bullet list shared by both
    Optimise pages, over ORDINAL_RANK_SUMMARY_METRICS.

    `rank_of(metric)` must return the 1-based rank for that metric - callers
    supply this as a closure since the two pages rank differently (a single
    site's own rank vs. the best two-site pairing that still includes it).
    """
    bullets = "\n".join(
        f"- **{ordinal(rank_of(m))}** best in terms of {RANK_METRIC_LABELS[m]}."
        for m in ORDINAL_RANK_SUMMARY_METRICS
    )
    st.markdown(f"Your solution is the:\n\n{bullets}\n")


SITE_SELECTION_SUBMITTABLE = [
    "demand",
    "deprivation",
    "car_travel",
    "public_transport",
    "2sfca_car",
    "2sfca_pt",
    "utilisation",
    "projected_demand",
    "demand_deprivation_hotspots",
    "demand_travel_hotspots",
    "deprivation_travel_hotspots",
    "left_behind",
    "final",
]

# Human-readable phrasing for each SITE_SELECTION_SUBMITTABLE key, for
# embedding in sentences (lower-case) describing which page a site choice
# came from - e.g. "You chose X for travel by car" rather than the raw
# "car_travel" key.
SITE_SELECTION_LABELS = {
    "demand": "demand",
    "deprivation": "deprivation",
    "car_travel": "travel by car",
    "public_transport": "travel by public transport",
    "2sfca_car": "accessibility by car (2SFCA)",
    "2sfca_pt": "accessibility by public transport (2SFCA)",
    "utilisation": "CDC utilisation",
    "projected_demand": "projected demand",
    "demand_deprivation_hotspots": "demand & deprivation hotspots",
    "demand_travel_hotspots": "demand & travel hotspots",
    "deprivation_travel_hotspots": "deprivation & travel hotspots",
    "left_behind": "who's left behind today",
    "final": "your final decision",
}

# Investigation ids (used by ``pages_visited`` and the investigation graph in
# utils_investigations.py) don't always match the SITE_SELECTION_SUBMITTABLE /
# confirmed_site_* keys used for site choices - a few pages' site keys drifted
# from their investigation id. This maps id -> site key so the two can be
# joined (see ``most_recent_prior_choice``).
INVESTIGATION_ID_TO_SITE_KEY = {
    "demand": "demand",
    "deprivation": "deprivation",
    "travel_car": "car_travel",
    "travel_pt": "public_transport",
    "hotspots_combined": "demand_deprivation_hotspots",
    "hotspots_demand_travel": "demand_travel_hotspots",
    "hotspots_deprivation_travel": "deprivation_travel_hotspots",
    "2sfca_car": "2sfca_car",
    "2sfca_pt": "2sfca_pt",
    "utilisation": "utilisation",
    "projected_demand": "projected_demand",
    "left_behind": "left_behind",
}


# Load datasets
@st.cache_data
def load_travel_matrix_car():
    return pd.read_csv("data/devon_miu_travel_matrix.csv")


@st.cache_data
def load_travel_matrix_public():
    return pd.read_csv("data/devon_miu_travel_matrix_public_transport.csv")


@st.cache_data
def load_population_weighted_centroids(snapped=True):
    if snapped:
        return geopandas.read_file("data/travel_matrix_generation/snapped_pwc.gpkg")
    else:
        return geopandas.read_file(
            "data/travel_matrix_generation/LSOA_PopCentroids_EW_2021_V4_-4541397882496207062.gpkg"
        )


@st.cache_data
def load_devon_sites():
    existing_cdcs = pd.read_csv("data/devon_cdcs.csv")
    return geopandas.GeoDataFrame(
        existing_cdcs,  # Our pandas dataframe
        geometry=geopandas.points_from_xy(
            existing_cdcs[
                "Longitude"
            ],  # Our 'x' column (horizontal position of points)
            existing_cdcs["Latitude"],  # Our 'y' column (vertical position of points)
        ),
        crs="EPSG:4326",
    )


@st.cache_data
def load_cdc_utilisation():
    # Made-up weekly capacity vs. weekly caseload for the four *existing* CDCs.
    # These are illustrative teaching figures, not real activity data. Proposed
    # (not-yet-built) sites are deliberately absent - they have no utilisation.
    return pd.read_csv("data/devon_cdc_utilisation.csv")


@st.cache_data
def load_devon_sites_with_utilisation():
    """Existing CDCs as a GeoDataFrame with weekly_capacity / weekly_caseload
    columns merged in (proposed sites get NaN - they aren't built yet)."""
    sites = load_devon_sites()
    return sites.merge(load_cdc_utilisation(), on="Facility_Name", how="left")


@st.cache_data
def load_devon_geography():
    return geopandas.read_file("data/LSOA_Devon_2021_EW_BSC_V4.gpkg")


@st.cache_data
def load_deprivation():
    return pd.read_csv("data/devon_imd_2025_2021_LSOAs.csv")


@st.cache_data
def load_demand():
    return pd.read_csv("data/demand_MF_50_84.csv")


@st.cache_data
def demand_by_equity_band() -> dict[int, float]:
    """Total 50-84 population in each IMD decile (1 = most deprived).

    Used to normalise the raw headcounts in a solution_df's
    *_by_equity_group columns into shares of each band's own population -
    a raw headcount makes the biggest band look worst regardless of how
    deprived it actually is.
    """
    merged = load_demand().merge(
        load_deprivation(), left_on="LSOA 2021 Name", right_on="LSOA name (2021)"
    )
    totals = merged.groupby(
        "Index of Multiple Deprivation (IMD) Decile (where 1 is most deprived 10% of LSOA"
    )["MF50-84"].sum()
    return totals.to_dict()


@st.cache_data
def create_demand_gdf():
    devon_gdf = load_devon_geography()
    demand_df = load_demand()
    full_gdf = devon_gdf.merge(demand_df, left_on="LSOA21NM", right_on="LSOA 2021 Name")
    return full_gdf


@st.cache_data
def load_demand_projected():
    return pd.read_csv("data/demand_MF_50_84_projected_2036.csv")


@st.cache_data
def create_projected_demand_gdf():
    devon_gdf = load_devon_geography()
    current_df = load_demand()
    projected_df = load_demand_projected()

    growth_df = current_df[["LSOA 2021 Name", "MF50-84", "Total"]].merge(
        projected_df[["LSOA 2021 Name", "MF50-84", "Total"]],
        on="LSOA 2021 Name",
        suffixes=(" (Now)", " (2036)"),
    )
    growth_df["MF50-84 Growth"] = (
        growth_df["MF50-84 (2036)"] - growth_df["MF50-84 (Now)"]
    )
    growth_df["MF50-84 Growth (%)"] = (
        (growth_df["MF50-84 (2036)"] / growth_df["MF50-84 (Now)"] - 1) * 100
    ).round(1)

    full_gdf = devon_gdf.merge(
        projected_df, left_on="LSOA21NM", right_on="LSOA 2021 Name"
    ).merge(
        growth_df[["LSOA 2021 Name", "MF50-84 Growth", "MF50-84 Growth (%)"]],
        on="LSOA 2021 Name",
    )
    return full_gdf


@st.cache_data
def create_deprivation_gdf():
    devon_gdf = load_devon_geography()
    deprivation_df = load_deprivation()
    full_gdf = devon_gdf.merge(
        deprivation_df, left_on="LSOA21NM", right_on="LSOA name (2021)"
    )
    return full_gdf


@st.cache_data
def load_demand_deprivation_hotspots():
    # Precomputed offline by data/generate_hotspots.py so the page doesn't run
    # Local Moran's I (spatial weights + permutation inference over 729 LSOAs)
    # live on every session. Re-run that script if the demand/deprivation inputs
    # change. Returns a GeoDataFrame with cluster_type / attribute_typology /
    # combined_score / p_value columns keyed to the Devon LSOA geometry.
    return pd.read_pickle("data/demand_deprivation_hotspots.pkl")


@st.cache_data
def load_demand_travel_hotspots():
    # Precomputed offline by data/generate_demand_travel_hotspots.py (a
    # solution-level analysis: it solves the existing-CDCs / car-travel problem
    # first, then runs Local Moran's I on demand vs travel time). Re-run that
    # script if the demand/car-travel inputs change. Returns a GeoDataFrame with
    # cluster_type / attribute_typology / combined_score / p_value / min_cost
    # columns keyed to the Devon LSOA geometry.
    return pd.read_pickle("data/demand_travel_hotspots.pkl")


@st.cache_data
def load_deprivation_travel_hotspots():
    # Precomputed offline by data/generate_deprivation_travel_hotspots.py (a
    # solution-level analysis: it solves the existing-CDCs / car-travel problem
    # first, then runs Local Moran's I on deprivation vs travel time). Re-run that
    # script if the deprivation/car-travel inputs change. Returns a GeoDataFrame
    # with cluster_type / attribute_typology / combined_score / p_value / min_cost
    # columns keyed to the Devon LSOA geometry.
    return pd.read_pickle("data/deprivation_travel_hotspots.pkl")


def _sr_only_text(text: str) -> str:
    """Plain-text fallback for the typewriter div: `<br>`s become line breaks,
    any other markup is stripped, then the result is HTML-escaped for safe
    embedding. Read immediately by screen readers/JS-disabled browsers, since
    the animated div is aria-hidden and only reveals its text via `innerHTML`
    once the char-by-char JS typing effect finishes.
    """
    collapsed = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    collapsed = re.sub(r"<[^>]+>", "", collapsed)
    return html.escape(collapsed, quote=True)


def write_terminal_html(
    text: str,
    output_path: str = "app/assets/terminal.html",
    colour: str = TERMINAL_COLOUR,
    glow_amount: float = 0.7,
    reveal_speed_ms: int = TERMINAL_DEFAULT_SPEED,
    cursor: str = "block",
    stay_blinking: bool = True,
):
    with open("app/assets/terminal.css") as f:
        css = f.read()
    with open("app/assets/terminal.js") as f:
        js = f.read()

    safe_text = html.escape(text, quote=True)
    sr_text = _sr_only_text(text)
    strong_pct = int(glow_amount * 100)
    soft_pct = int(glow_amount * 40)

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<style>
    {css}
    :root {{
        --terminal-colour: {colour};
        --terminal-glow-strong: color-mix(in srgb, {colour} {strong_pct}%, transparent);
        --terminal-glow-soft: color-mix(in srgb, {colour} {soft_pct}%, transparent);
    }}
</style>
</head>
<body>
  <div id="typewrite" class="typeing" aria-hidden="true" data-text="{safe_text}"></div>
  <div class="sr-only" role="status">{sr_text}</div>
  <script>
    var REVEAL_SPEED_MS = {reveal_speed_ms};
    var CURSOR = {repr(cursor)};
    var STAY_BLINKING = {"true" if stay_blinking else "false"};
    {js}
  </script>
</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(html_content)

    return len(text), reveal_speed_ms


def write_crt_html(
    image_path: str,
    output_path: str = "app/assets/crt_render.html",
    curvature: float = 0.15,
    scanlines: float = 0.3,
    vignette: float = 0.2,
):
    """
    Writes a self-contained HTML file applying CRTFilter.js to a target image,
    matching the architecture of your working terminal generator.
    """
    # 1. Read the local JavaScript file source
    # (Using utf-8 to ensure smooth reading across different OS environments)
    with open("app/assets/CRTFilter.js", "r", encoding="utf-8") as f:
        js_library = f.read()

    # 2. Convert the image asset to a base64 string
    image = Image.open(image_path)
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    image_b64 = base64.b64encode(buffered.getvalue()).decode()

    # 3. Generate the self-contained HTML
    # Note: We use type="module" so the browser handles the library's ES exports flawlessly.
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0;
            padding: 0;
            background-color: transparent;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
        }}
        canvas {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
        }}
    </style>
</head>
<body>

    <canvas id="crtCanvas"></canvas>

    <script type="module">
        // Inject the library directly into the module scope
        {js_library}

        // The library exports 'CRTFilterWebGL' natively.
        // Because we are inside a type="module" script, it is perfectly accessible here.
        const canvas = document.getElementById('crtCanvas');
        const ctx = canvas.getContext('2d');

        const img = new Image();
        img.src = "data:image/png;base64,{image_b64}";

        img.onload = function() {{
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);

            try {{
                // Initialize using the actual configuration keys required by the library
                const crt = new CRTFilterWebGL(canvas, {{
                    curvature: {curvature},
                    scanlineIntensity: {scanlines},
                    vignette: {vignette}
                }});

                // Fire up the animation frame render cycle
                crt.start();
            }} catch (e) {{
                console.error("CRTFilter runtime exception:", e);
            }}
        }};
    </script>
</body>
</html>"""

    # 4. Write out the static HTML file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_path


def record_page_visited(investigation: Investigation) -> None:
    """Record a visit to an investigation page by ID."""
    visited_ids = [v["id"] for v in st.session_state.pages_visited]
    if investigation.id not in visited_ids:
        step = len(st.session_state.pages_visited) + 1
        st.session_state.pages_visited.append(
            {
                "step": step,
                "id": investigation.id,
                "title": investigation.title,
                "analyst_days": investigation.analyst_days,
            }
        )


def most_recent_prior_choice(current_investigation_id: str) -> dict | None:
    """The most recently confirmed site from an earlier investigation, if any.

    Walks ``pages_visited`` newest-first (skipping the current page) and
    returns the first ``{"What": ..., "Site": ...}`` dict that actually has a
    confirmed site recorded - so a page that was visited but left without
    submitting (possible via direct URL navigation, which bypasses the
    button-only gating) is skipped rather than returned as a false memory.
    """
    for visit in reversed(st.session_state.pages_visited):
        if visit["id"] == current_investigation_id:
            continue
        site_key = INVESTIGATION_ID_TO_SITE_KEY.get(visit["id"])
        if site_key is None:
            continue
        choice = st.session_state.get(f"confirmed_site_{site_key}")
        if choice is not None:
            return choice
    return None


def render_prior_choice_recap(investigation: Investigation) -> None:
    """Remind the user what they last committed to, before they see new evidence.

    Without this, every evidence page renders identically regardless of what
    came before it: the investigation graph gates *which* pages you can
    reach, but nothing downstream reads what happened upstream. This is the
    cheapest way to make earlier choices visibly carry forward - and it sets
    up the "did this change your mind?" question every subsequent page is
    implicitly asking.
    """
    prior = most_recent_prior_choice(investigation.id)
    if prior is None:
        return
    st.info(
        f"Last time you committed to a site, you picked **{prior['Site']}** "
        f"— based on {prior['What']}. Let's see what this page adds.",
        icon=":material/history:",
    )


def _prerequisites_met(investigation: Investigation) -> bool:
    visited_ids = {v["id"] for v in st.session_state.pages_visited}
    return all(p in visited_ids for p in investigation.prerequisites)


def _already_visited(investigation: Investigation) -> bool:
    visited_ids = {v["id"] for v in st.session_state.pages_visited}
    return investigation.id in visited_ids


def _missing_prerequisites(investigation: Investigation) -> list[str]:
    """IDs of this investigation's prerequisites not yet visited."""
    visited_ids = {v["id"] for v in st.session_state.pages_visited}
    return [p for p in investigation.prerequisites if p not in visited_ids]


def investigation_button(investigation: Investigation) -> None:
    """
    Render a single investigation button.

    - Locked (visible but disabled, naming what's still needed) if
      prerequisites are unmet - shows the curriculum exists rather than
      hiding it entirely.
    - Greyed out (non-clickable) if already visited.
    - Active and clickable otherwise.
    """
    button_key = f"inv_btn_{investigation.id}"

    if not _prerequisites_met(investigation):
        missing_titles = ", ".join(
            ALL_INVESTIGATIONS[p].title
            for p in _missing_prerequisites(investigation)
            if p in ALL_INVESTIGATIONS
        )
        st.html(f"""
            <div class="investigation-tile investigation-tile-locked">
                <span style="margin-right: 8px; flex-shrink: 0;">&#128274;</span>
                <span><strong>Locked</strong> - {investigation.analyst_prompt}<br>
                    <span class="investigation-tile-requires">Requires: {missing_titles}</span>
                </span>
            </div>
        """)
        return

    visited = _already_visited(investigation)

    # # Use Iconify API to grab the Lucide icon as a clean, static SVG image
    # # Lucide icons on Iconify use the prefix "lucide" (e.g., lucide/search)
    # icon_url = f"https://api.iconify.design/lucide/{investigation.icon}.svg"

    # icon_html = f"""
    #     <img src="{icon_url}"
    #          style="width:18px; height:18px; vertical-align:middle; margin-right:8px;
    #                 {"filter: opacity(0.4) grayscale(100%);" if visited else ""}" />
    # """

    if visited:
        icon_url = f"https://api.iconify.design/lucide/{investigation.icon}.svg"
        icon_html = f'<img src="{icon_url}" style="width:18px; height:18px; vertical-align:middle; margin-right:8px; filter: opacity(0.4) grayscale(100%);" />'
        # Render as static greyed-out tile — no button interaction
        st.html(f"""
            <div class="investigation-tile investigation-tile-visited">
                {icon_html}
                <span>✓ {investigation.analyst_prompt}</span>
            </div>
        """)
    else:
        streamlit_icon = f":material/{investigation.icon}:"

        # Once the analyst's briefing budget is spent, every remaining choice is
        # greyed out (disabled) - the only way forward is to make a decision.
        if st.button(
            investigation.analyst_prompt,
            key=button_key,
            icon=streamlit_icon,
            width="stretch",
            disabled=capacity_exhausted(),
        ):
            record_page_visited(investigation)
            st.switch_page(investigation.page)


# components/investigation_button.py (addition)


def render_navigation(current: Investigation) -> None:
    """
    Render the full navigation section for a given investigation page.
    Call once at the bottom of each page after content.
    """
    render_capacity_status()

    st.subheader("Recommended next steps")
    st.caption("More options may unlock as you progress through the problem.")
    recommended = [
        ALL_INVESTIGATIONS[inv_id]
        for inv_id in current.recommended_next
        if inv_id in ALL_INVESTIGATIONS
    ]
    # Locked entries sink to the bottom of the list (stable sort keeps
    # everything else in its existing order) - what you can act on right
    # now stays primary, what's still locked reads as secondary/aspirational.
    for inv in sorted(recommended, key=lambda inv: not _prerequisites_met(inv)):
        investigation_button(inv)

    other_investigations = [
        inv
        for inv_id, inv in ALL_INVESTIGATIONS.items()
        if inv_id not in set(current.recommended_next) | {current.id}
    ]

    if any(not _already_visited(inv) for inv in other_investigations):
        st.divider()
        st.subheader("Other available investigations")
        for inv in sorted(
            other_investigations, key=lambda inv: not _prerequisites_met(inv)
        ):
            investigation_button(inv)

    st.subheader("Other Actions")
    # Allow jumping to decisions page
    if st.button(
        "Review your decisions so far and make your choice.",
        key="btn_make_your_choice",
        icon=":material/balance:",
        width="stretch",
    ):
        st.switch_page("app/Decide.py")

    # Padding
    st.write("")
    st.write("")


def crt_filter_component(
    image_path: str, curvature: float, scanlines: float, vignette: float
):
    # 1. Prepare and read the Image
    image = Image.open(image_path)
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    image_b64 = base64.b64encode(buffered.getvalue()).decode()

    # 2. Read and patch the JS library
    try:
        js_lib_code = Path("app/assets/CRTFilter.js").read_text()

        # REMOVE the ES Module export syntax so the browser can run it as a normal script
        # This binds it to the global window scope safely inside our IIFE
        js_lib_code = js_lib_code.replace("export { CRTFilterWebGL };", "")
        js_lib_code = js_lib_code.replace("export default CRTFilterWebGL;", "")
    except FileNotFoundError:
        st.error("Could not find CRTFilter.js in app/assets/")
        return

    # Use a unique ID based on the path
    canvas_id = f"crt_{hash(image_path) & 0xFFFFFFFF}"

    html_code = f"""
    <div style="display: flex; justify-content: center; margin: 10px 0;">
        <canvas id="{canvas_id}" style="max-width: 100%; height: auto; border-radius: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.4);"></canvas>
    </div>

    <script>
        (function() {{
            // 1. Evaluate the modified library string safely
            if (typeof CRTFilterWebGL === 'undefined') {{
                {js_lib_code}
            }}

            const canvas = document.getElementById('{canvas_id}');
            if (!canvas) return;

            const ctx = canvas.getContext('2d');
            const img = new Image();
            img.src = "data:image/png;base64,{image_b64}";

            img.onload = function() {{
                // Apply source sizing
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.drawImage(img, 0, 0);

                try {{
                    // 2. Instantiate with the correct class name and parameters
                    const crt = new CRTFilterWebGL(canvas, {{
                        curvature: {curvature},
                        scanlineIntensity: {scanlines},
                        vignette: {vignette}
                    }});

                    # 3. Trigger the animation loop render lifecycle
                    crt.start();
                }} catch (e) {{
                    console.error("CRTFilter Execution Failure:", e);
                }}
            }};
        }})();
    </script>
    """

    st.html(html_code, unsafe_allow_javascript=True)


ANALYST_CAPACITY_MESSAGES = [
    {
        "analyses_remaining": 6,
        "message": (
            "Your analyst appears enthusiastic and optimistic. "
            "They have several coloured pens, a fresh notebook, and "
            "a coffee cup that is still warm."
        ),
    },
    {
        "analyses_remaining": 5,
        "message": "Your analyst appears a little less bright-eyed and bushy-tailed than when you "
        "first met them. Their coffee cup does not leave their sight.",
    },
    {
        "analyses_remaining": 4,
        "message": "Your analyst now appears to have upgraded to a hat with two coffee cups atttached and a straw. "
        "You make a note to review the coffee budget for the data department.",
    },
    {
        "analyses_remaining": 3,
        "message": "Your analyst appears to be disillusioned. They have been getting very angry about "
        "documentation (the lack of it) and data dictionaries (the absence of them) and something "
        "called a syntax error (an abundance of). You smile and nod politely.",
    },
    {
        "analyses_remaining": 2,
        "message": "Your analyst is mysteriously missing every time you try to talk to them. "
        "You swear you saw them exit via a ground-floor window when you approached "
        "the building recently, but you cannot prove this.",
    },
    {
        "analyses_remaining": 1,
        "message": "Your analyst informs you that they are considering a career in "
        "sheep farming. They have begun browsing rural property listings "
        "in Scotland during meetings. It may be prudent to reach a decision soon.",
    },
]


def analyses_used() -> int:
    """How many of the analyst's briefings have been spent so far.

    Each unique evidence page the user visits costs one briefing (see
    ``record_page_visited`` - revisits are free).
    """
    return len(st.session_state.pages_visited)


def analyses_remaining() -> int:
    """How many briefings the analyst can still provide."""
    return MAXIMUM_BRIEFINGS - analyses_used()


def total_analyst_days() -> float:
    """Cumulative analyst_days across every unique page visited so far.

    Purely informational - see render_capacity_status(). The briefing count
    is the only thing that actually gates progress; this never constrains
    anything, it just makes the (very uneven) real cost behind each flat
    "1 briefing" visible.
    """
    return sum(v["analyst_days"] for v in st.session_state.pages_visited)


def capacity_exhausted() -> bool:
    """True once every briefing has been spent."""
    return analyses_remaining() <= 0


def _capacity_message(remaining: int) -> str | None:
    """The analyst flavour text for a given number of remaining briefings."""
    for entry in ANALYST_CAPACITY_MESSAGES:
        if entry["analyses_remaining"] == remaining:
            return entry["message"]
    return None


def render_capacity_status() -> None:
    """Tell the user how many briefings they can still request.

    Uses the flavour text in ``ANALYST_CAPACITY_MESSAGES`` and escalates the
    styling (info -> warning -> error) as the budget runs down.
    """
    remaining = analyses_remaining()

    if remaining <= 0:
        st.error(
            f"Your analyst is out of capacity - all {MAXIMUM_BRIEFINGS} briefings "
            "have been used. You can no longer request new information, so it is "
            "time to make your decision.",
            icon=":material/hourglass_disabled:",
        )
    else:
        plural = "briefing" if remaining == 1 else "briefings"
        header = f"You can request **{remaining}** more {plural}."
        message = _capacity_message(remaining)
        body = f"{header}\n\n{message}" if message else header

        if remaining <= 2:
            st.warning(body, icon=":material/hourglass_bottom:")
        else:
            st.info(body, icon=":material/hourglass_top:")

    if st.session_state.pages_visited:
        days = total_analyst_days()
        n = len(st.session_state.pages_visited)
        briefing_word = "briefing" if n == 1 else "briefings"
        st.caption(
            f"Behind the scenes: your analyst has logged **{days:g} days** of work "
            f"across those {n} {briefing_word} so far - a reminder that the "
            "briefing count and the real cost aren't the same thing."
        )


def page_styling():
    with open("app/style.css", "r") as f:
        css_content = f.read()

    return st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)


# A one-shot "scroll back to the top" used after a decision is submitted, so the
# user lands at the top of the (now terminal-free) page instead of wherever the
# submit button happened to be. request_scroll_to_top() is called at submission;
# handle_scroll_to_top() runs once on the following rerun and consumes the flag.
SCROLL_TOP_FLAG = "_scroll_to_top"


def request_scroll_to_top():
    """Ask for the next run to scroll the page to the top."""
    st.session_state[SCROLL_TOP_FLAG] = True


def handle_scroll_to_top():
    """Emit the scroll-to-top JS if one was requested, then clear the flag."""
    if not st.session_state.get(SCROLL_TOP_FLAG):
        return
    st.session_state[SCROLL_TOP_FLAG] = False

    # A changing nonce makes Streamlit treat this as a fresh component each time,
    # so the scroll re-fires on repeat submissions rather than being cached.
    nonce = st.session_state.get("_scroll_nonce", 0) + 1
    st.session_state["_scroll_nonce"] = nonce

    # st.iframe (Streamlit >=1.60) auto-detects the HTML string and replaces the
    # deprecated st.components.v1.html.
    st.iframe(
        f"""<!DOCTYPE html>
<html><body><script>
    // {nonce}
    const doc = window.parent.document;
    const selectors = [
        'section.main',
        '[data-testid="stMain"]',
        '[data-testid="stAppViewContainer"]',
        '[data-testid="stMainBlockContainer"]',
    ];
    for (const sel of selectors) {{
        const el = doc.querySelector(sel);
        if (el) el.scrollTo({{top: 0, left: 0, behavior: "instant"}});
    }}
    window.parent.scrollTo({{top: 0, left: 0, behavior: "instant"}});
</script></body></html>""",
        height=1,
    )


# Streamlit only honours `initial_sidebar_state` on a session's very first
# page load - navigating between pages via st.switch_page/investigation tiles
# reuses the same mounted app, so a newly-active page's own
# initial_sidebar_state is silently ignored. This forces the sidebar open or
# closed via JS instead, but only once per navigation to a given page (tracked
# below) so it doesn't keep fighting a user who manually toggles it while
# staying on that page.
_SIDEBAR_FORCED_FOR_KEY = "_sidebar_forced_for_page"


def force_sidebar_state(expanded: bool, page_key: str) -> None:
    """Force the sidebar open/closed once per navigation to `page_key`."""
    if st.session_state.get(_SIDEBAR_FORCED_FOR_KEY) == page_key:
        return
    st.session_state[_SIDEBAR_FORCED_FOR_KEY] = page_key

    nonce = st.session_state.get("_sidebar_force_nonce", 0) + 1
    st.session_state["_sidebar_force_nonce"] = nonce
    desired = "true" if expanded else "false"

    st.iframe(
        f"""<!DOCTYPE html>
<html><body><script>
    // {nonce}
    const doc = window.parent.document;
    let attempts = 0;
    const tryToggle = () => {{
        attempts += 1;
        const sidebar = doc.querySelector('[data-testid="stSidebar"]');
        if (!sidebar) {{
            if (attempts < 40) setTimeout(tryToggle, 100);
            return;
        }}
        const isExpanded = sidebar.getAttribute("aria-expanded") === "true";
        if (isExpanded === {desired}) return;
        const btn = {desired}
            ? doc.querySelector('[data-testid="stExpandSidebarButton"]')
            : doc.querySelector('[data-testid="stSidebarCollapseButton"] button');
        if (btn) btn.click();
        else if (attempts < 40) setTimeout(tryToggle, 100);
    }};
    tryToggle();
</script></body></html>""",
        height=1,
    )


def select_site_from_current_evidence():

    devon_sites = load_devon_sites()
    options = devon_sites[devon_sites["Existing"] == "No"]

    selected = st.pills(
        label="Based on the evidence on this page only, what one site would you choose?",
        options=options,
    )

    return selected


@st.cache_data
def load_car_travel_matrix():
    return pd.read_csv("data/travel_matrix_car.csv")


@st.cache_data
def load_pt_travel_matrix():
    return pd.read_csv("data/travel_matrix_public_transport.csv")


@st.cache_resource
def setup_lokigi_site_problem_BASE():
    lokigi_site_problem = SiteProblem()

    lokigi_site_problem.add_demand(
        load_demand(), demand_col="MF50-84", location_id_col="LSOA 2021 Name"
    )

    lokigi_site_problem.add_region_geometry_layer(
        load_devon_geography(), common_col="LSOA21NM"
    )

    lokigi_site_problem.add_equity_data(
        load_deprivation(),
        equity_col="Index of Multiple Deprivation (IMD) Decile (where 1 is most deprived 10% of LSOA",
        common_col="LSOA name (2021)",
        label="IMD",
        disadvantaged_end="low",  # decile 1 = most deprived
    )

    return lokigi_site_problem


@st.cache_resource
def setup_lokigi_site_problem_car_existing():
    lokigi_site_problem = setup_lokigi_site_problem_BASE().copy()

    devon_sites = load_devon_sites()

    devon_sites = devon_sites[devon_sites["Existing"] == "Yes"]

    lokigi_site_problem.add_sites(
        devon_sites,
        candidate_id_col="Facility_Name",
    )

    lokigi_site_problem.add_travel_matrix(
        load_car_travel_matrix(), unit="minutes", source_col="from_id"
    )

    return lokigi_site_problem


@st.cache_resource
def solve_car_existing_travel():
    # D4 fix: the problem object was already cached, but Travel_Car.py called
    # .solve(p=4) itself at page top-level, so it re-ran on every full rerun.
    # p equals the number of existing sites here, so there's only one possible
    # combination to evaluate - but solve() still walks the whole brute-force
    # pipeline to find it, so caching the result (not just the problem) is what
    # actually avoids the repeat work.
    return setup_lokigi_site_problem_car_existing().solve(p=4)


@st.cache_resource
def setup_lokigi_site_problem_utilisation():
    # Utilisation is a baseline diagnostic of the *existing* sites: how much of
    # each site's capacity today's caseload uses. It needs neither travel matrix
    # nor solve() - just the sites registered with capacity/current-load columns.
    lokigi_site_problem = setup_lokigi_site_problem_BASE().copy()

    existing_sites = load_devon_sites_with_utilisation()
    existing_sites = existing_sites[existing_sites["Existing"] == "Yes"]

    lokigi_site_problem.add_sites(
        existing_sites,
        candidate_id_col="Facility_Name",
        capacity_col="weekly_capacity",
        current_load_col="weekly_caseload",
    )

    return lokigi_site_problem


@st.cache_resource
def setup_lokigi_site_problem_car():
    lokigi_site_problem = setup_lokigi_site_problem_BASE().copy()

    lokigi_site_problem.add_sites(
        load_devon_sites(),
        candidate_id_col="Facility_Name",
        required_sites_col="Existing",
    )

    lokigi_site_problem.add_travel_matrix(
        load_car_travel_matrix(), unit="minutes", source_col="from_id"
    )

    return lokigi_site_problem


@st.cache_resource
def evaluate_car_baseline():
    """Today's network (the 4 existing CDCs) evaluated on its own - no
    candidate site involved - for the Left Behind page. evaluate_baseline()
    defaults to the sites flagged via required_sites_col in
    setup_lokigi_site_problem_car(), i.e. exactly the existing network."""
    return setup_lokigi_site_problem_car().evaluate_baseline(
        threshold_for_coverage=COVERAGE_THRESHOLD_MINUTES,
        beyond_thresholds=LEFT_BEHIND_THRESHOLDS,
    )


@st.cache_resource
def setup_lokigi_site_problem_pt():
    lokigi_site_problem = setup_lokigi_site_problem_BASE().copy()

    lokigi_site_problem.add_sites(
        load_devon_sites(),
        candidate_id_col="Facility_Name",
        required_sites_col="Existing",
    )

    lokigi_site_problem.add_travel_matrix(
        load_pt_travel_matrix(),
        unit="minutes",
        source_col="from_id",
        allow_missing=True,
        treat_as_missing=9999,
    )

    return lokigi_site_problem


@st.cache_resource
def solve_pt_travel():
    # D4 fix, PT counterpart of solve_car_existing_travel() above - see that
    # function's comment for why caching the solve() call (not just the
    # problem setup) is what actually removes the per-rerun cost.
    # unreachable_cost is set well above any plausible journey time (the
    # longest real PT trip in the matrix is nowhere close) so the 109 cells
    # that treat_as_missing above converts to NaN are penalised rather than
    # silently dropped from ranking.
    return setup_lokigi_site_problem_pt().solve(p=4, unreachable_cost=360.0)


def _setup_lokigi_site_problem_2sfca(travel_matrix):
    # 2SFCA needs the three ingredients the earlier pages showed separately:
    # each existing site's capacity (supply), the population (demand, from BASE),
    # and how far apart they are (a travel matrix). Only the four *existing* CDCs
    # have capacity, so those are the sites we register. Proposed sites aren't
    # built and contribute no supply; they're overlaid on the map for selection
    # only, outside this lokigi problem.
    lokigi_site_problem = setup_lokigi_site_problem_BASE().copy()

    existing_sites = load_devon_sites_with_utilisation()
    existing_sites = existing_sites[existing_sites["Existing"] == "Yes"]

    lokigi_site_problem.add_sites(
        existing_sites,
        candidate_id_col="Facility_Name",
        capacity_col="weekly_capacity",
        current_load_col="weekly_caseload",
    )

    lokigi_site_problem.add_travel_matrix(
        travel_matrix,
        unit="minutes",
        source_col="from_id",
        allow_missing=True,
        treat_as_missing=9999,
    )

    return lokigi_site_problem


@st.cache_resource
def setup_lokigi_site_problem_2sfca_car():
    return _setup_lokigi_site_problem_2sfca(load_car_travel_matrix())


@st.cache_resource
def setup_lokigi_site_problem_2sfca_pt():
    return _setup_lokigi_site_problem_2sfca(load_pt_travel_matrix())


# A single, shared notepad follows the user across every evidence page. The
# durable copy lives under a plain (non-widget) session-state key - Streamlit
# clears widget-scoped state whenever a widget isn't rendered on the previous
# run, which happens every time the user changes page, so the text area itself
# cannot be relied on to persist. Instead the widget writes into the durable key
# via its on_change callback, and is re-seeded from it on every run.
NOTES_STATE_KEY = "user_notes"
_NOTES_WIDGET_KEY = "_user_notes_widget"


def _persist_notes():
    st.session_state[NOTES_STATE_KEY] = st.session_state[_NOTES_WIDGET_KEY]


def render_notes_textbox(key=None):
    """Render the running notepad that follows the user from page to page.

    All evidence pages share one notepad (``st.session_state["user_notes"]``),
    so notes written on earlier pages are already present here.

    ``key`` is accepted for backwards compatibility with existing call sites but
    is no longer used to scope the notes - all pages share one notepad.
    """
    st.session_state.setdefault(NOTES_STATE_KEY, "")

    st.subheader("Write down any additional thoughts you have.")
    st.caption(
        "These notes follow you from page to page, so you can build up your "
        "thinking as you go."
    )

    # Re-seed the widget from the durable copy every run (see note above), then
    # let its on_change callback write any edits straight back into it.
    st.session_state[_NOTES_WIDGET_KEY] = st.session_state[NOTES_STATE_KEY]
    st.text_area(
        label="Your Thoughts",
        label_visibility="hidden",
        key=_NOTES_WIDGET_KEY,
        on_change=_persist_notes,
        height=350,
    )

    st.write("")
    st.write("")
