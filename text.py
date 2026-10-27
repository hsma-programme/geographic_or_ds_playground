PARETO_CHART = """
### How to read this chart

This chart compares the best shortlisted location options across several different objectives.

Each coloured line represents one possible configuration of sites. Each vertical axis is a different measure that matters when deciding between options, such as average travel time or equity.

Because each measure uses different units (minutes, percentages, ratios, etc.), the values have been rescaled so they can be shown on the same chart.

**Higher is always better.** A point near the top of an axis means that option performs well on that measure; a point near the bottom means it performs less well. The small numbers at the top and bottom of each axis show the original values for context.

### Why are there several "best" options?

**There is no single option that is best on every measure.**

Instead, each coloured line is a Pareto-optimal solution. This means that you cannot improve it on one objective without making it worse on at least one other objective.

For example, one option may achieve the shortest average travel time, while another provides fairer access between communities. Neither is universally better—they simply represent different trade-offs.

The grey lines are options that were not shortlisted because another solution performs at least as well on every measure and better on at least one. There is therefore little reason to choose them.

### How to use this chart

Rather than asking "Which option is best?", this chart helps answer:

- Which option best reflects our priorities?
- How much travel time are we willing to trade for better equity?
- Is a small improvement in one measure worth a larger reduction in another?

The chart is designed to support discussion about these trade-offs. Once organisational priorities have been agreed, the Pareto-optimal solution that best aligns with those priorities can be selected.
"""

PARETO_BREAKDOWN_CHART = """
### How to read this chart

Each panel focuses on one Pareto-optimal option and explains what makes it a credible candidate.

The bold coloured line shows how that option performs across each objective. The faint background lines show all the other shortlisted options, providing context without distracting from the option being discussed.

Each vertical axis represents a different objective, such as average travel time or equity. As these measures use different units, they have been scaled independently so that they can be shown on the same chart.

Higher is always better. A point near the top of an axis indicates strong performance for that objective, while a point near the bottom indicates that the option gives up performance in that area in order to achieve gains elsewhere.

The labels beside each point show the actual value for that measure, while the text above the chart summarises:

- Which sites are included in this configuration.
- How many other designs this option outperforms (that is, how many solutions it dominates).
- Its main strengths, showing where it ranks highly compared with all candidate designs.
- Its main trade-offs, showing where other designs perform better.

### How to use this chart

There is no universally best option. Every shortlisted configuration represents a different balance between competing objectives.

This chart is designed to help answer questions such as:

- If we prioritise reducing average travel times, which option should we choose?
- If improving equity is our primary objective, what do we give up elsewhere?
- Which combination of sites best reflects our organisational priorities?

By reviewing each shortlisted option individually, you can understand why it has been selected, what benefits it offers, and what compromises it requires before making a final choice.
"""
