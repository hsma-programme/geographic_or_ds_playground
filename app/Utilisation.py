import streamlit as st
from app.utils import (
    render_navigation,
    write_terminal_html,
    page_styling,
)
from app.utils_investigations import UTILISATION
from app.maps import render_utilisation_map, make_selection_map

st.set_page_config(initial_sidebar_state="expanded", layout="wide")
page_styling()

st.title("Current CDC Utilisation")

intro_text = """
> Your analyst returns with two maps side by side.
<br><br>
> On the left are the four CDCs that already exist, each coloured by how much of its weekly capacity is currently being used: blue centres have spare capacity, red centres are running at or beyond what they were built to handle. The busier the site, the bigger the circle. Hover over (or click) each circle for its weekly capacity, actual caseload, and remaining room - the table below repeats these numbers.
<br><br>
> On the right is the underlying regional demand: the population aged 50-84 in each area, who are most likely to need CDC services. Darker areas mean more people.
<br><br>
> "Read them together," they suggest. "A centre that's already full sitting next to a lot of demand is a very different problem from a quiet centre in an empty area."
<br><br>
> They dissolve into a cloud of static, leaving you to interpret the maps.
"""

# Once a decision has been made on this page, drop the analyst intro so a
# revisit shows just the evidence and outcome.
if not st.session_state.site_submitted_utilisation:
    write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/utilisation.html",
    )
    st.iframe("app/assets/terminal_working/utilisation.html", height=400)

utilisation_selection_map = make_selection_map(render_utilisation_map, "utilisation")
utilisation_selection_map()

if st.session_state.site_submitted_utilisation:
    render_navigation(UTILISATION)
