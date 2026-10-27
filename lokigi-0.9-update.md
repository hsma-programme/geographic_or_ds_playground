## Highlights

This release adds the ability to rank/prune site searches on **any** computed metric (`solve(rank_on=...)`), a raft of tools for reporting **population impact vs. a baseline** and **capacity utilisation**, first-class handling of **unreachable travel costs** (instead of sentinel values like `9999`), and several stakeholder-facing reporting helpers (`show_solutions_summary()`, `decision_summary()`). It also includes a handful of breaking renames — read below before upgrading.

## ⚠️ Breaking changes

- **`ParetoMetric` → `Metric`.** It now covers Pareto fronts *and* `solve(rank_on=...)`. No alias — `from lokigi.multiobjective import ParetoMetric` now raises `ImportError`. Fields/defaults/methods are unchanged, just the name.
- **`rank_on` in post-hoc reporting/plotting is renamed to `sort_by`.** `rank_on` in `solve()` *searches* (only what it keeps can ever be returned); the old `rank_on` on reporting methods only *re-sorts* whatever `solve()` already kept. Having both named `rank_on` was a standing source of confusion — reaching for the wrong one silently produced a weaker answer instead of an error. Affects `show_solutions()`, `show_solutions_summary()`, `return_best_combination_details()`/`_site_indices()`/`_site_names()`, `site_allocation_summary()`, `site_capacity_summary()`, `two_step_floating_catchment()`, `plot_best_combination()`, `plot_n_best_combinations()`/`_bar()`, `plot_site_allocation_summary()`, `plot_site_capacity_summary()`, `plot_allocated_utilisation()`, `plot_solution_comparison()`, `plot_travel_time_distribution()`, `check_solution_equity()`, `plot_top_n_solution_equity()`, `plot_combination_by_equity()`, and the `'rank_on'` config key in `plot_solution_sets_comparison()`/`SolutionComparator.plot_comparison()`. All now take `sort_by=`. No alias.
- **GRASP now applies `unreachable_cost` to the solutions it returns, not only the ones it searches.** With `unreachable_cost` set, a multi-solution GRASP pool could previously come back mis-ordered (`grasp_num_solutions=1` was unaffected).
- **Tertile equity metrics now honour `add_equity_data(disadvantaged_end=...)`.** `avg_lower_third_bins`/`avg_upper_third_bins`, `inter_tertile_ratio`/`_description`, and `population_impact_by_equity_group()`'s band ordering previously assumed the lowest raw values were always most disadvantaged. Numbers change for problems registered with `disadvantaged_end="high"`; `"low"`/unset problems are unaffected.
- **`site_allocation_summary()`'s `total_demand` column is renamed `allocated_demand`**, to sit next to `site_capacity_summary()`'s new `capacity` column. (Unrelated to — and doesn't affect — `population_impact_summary()`'s `total_demand` or `SiteProblem.total_demand`.)

## ✨ New features

- **Rank on any metric** — `solve(rank_on=...)` searches and prunes on any computed metric (`inter_tertile_ratio`, `90th_percentile`, `demand_beyond_threshold_45`, ...), not just what `objectives` implies. Takes a bare column name or a `Metric` for explicit direction (e.g. `direction="closest_to_target"`). New `objectives="custom"` model for ranking with no other constraints. See the new `custom_ranking_metric` example.
- **Capacity reporting** — `site_capacity_summary()`, `plot_site_capacity_summary()`, `plot_allocated_utilisation()` compare a solution's allocated demand against registered site capacity (`add_sites(capacity_col=...)`). Diagnostic only.
- **Stakeholder-facing summaries** — `show_solutions_summary()` (plain-English `solution_df`, sections shown only when the underlying data was registered) and `describe_solution_columns()` (grouped column reference).
- **Population impact vs. baseline** — `evaluate_baseline()`, `population_impact_summary()`, `solve(baseline=...)`, plus reporting/plotting helpers: `population_impact_phrase()`, `population_impact_worst_affected()`, `decision_summary()`, `plot_population_impact_map()`, `plot_population_impact_histogram()`, `population_impact_by_equity_group()`, `plot_population_impact_by_equity_group()`, and `site_reallocation_matrix()`/`plot_site_reallocation_matrix()`.
- **Unreachable travel costs, handled properly** — `add_travel_matrix(allow_missing=, treat_as_missing=)` lets genuinely unreachable O-D pairs be `NaN` instead of a corrupting sentinel like `9999`. Averages now exclude unreachable regions (reporting `regions_unreachable`/`demand_unreachable` alongside), `solve(unreachable_cost=...)` gives an explicit ranking-only cost policy, and every solution map now renders unreachable regions as a distinct grey fill instead of leaving an invisible hole.
- Absolute coverage headcounts alongside existing proportions; `SiteProblem.total_demand`; `beyond_thresholds` for "left behind" cutoffs; `caption` on `plot_accessibility()`/`plot_site_utilisation()`.

## 🐛 Fixes

- `describe_models()` pointed at a nonexistent `solve_pmedian()` method.
- Several colour bars/axes showed raw column names instead of plain-English labels with units (`plot_best_combination()`, `plot_n_best_combinations()`, `check_solution_equity()`, `plot_combination_by_equity()`, `plot_region_geometry_layer()`, `plot_population_impact_by_equity_group()`).
- `check_solution_equity()`'s bar chart didn't indicate which end was "most deprived"; now ordered per `disadvantaged_end`.
- `plot_region_geometry_layer()`'s plain branch ignored `plot_region_of_interest_only` and raised `UnboundLocalError` when set.
- `plot_solution_sets_comparison()` panels autoscaled colour bars independently, making differently-scaled solutions (e.g. car vs. public transport) look misleadingly similar; now share a colour scale by default (`shared_color_scale=False` to opt out).
- `gap_absolute_description` always said "units" regardless of the travel matrix's registered unit.
- `plot_combination_by_equity()` panels didn't state region/population counts, making sparse groups look falsely "fine".
- `plot_population_impact_histogram()`'s KDE y-axis label was a meaningless stats term; now plain-English with an explanatory caption.
- Accessibility/evaluation methods crashed with a cryptic pandas `TypeError` when no travel matrix/demand was registered; now raise a clear `ValueError`.
- `get_hotspots()` and friends surfaced a libpysal `FutureWarning` on every run; also pinned `esda<3` to avoid a silent change in `Moran_Local`'s p-values.
- Interactive maps rendered fully zoomed out when initialised inside a hidden container (e.g. non-first Quarto `revealjs` slides/tabsets); now self-correct via a one-shot `ResizeObserver`.
- Pinned a minimum numba version to prevent build failures from resolving to a very old version.
