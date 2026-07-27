import streamlit as st
from app.utils import (
    render_navigation,
    write_terminal_html,
    page_styling,
    render_notes_textbox,
    setup_lokigi_site_problem_2sfca_pt,
)
from app.utils_investigations import TWO_SFCA_PT
from app.maps import render_2sfca_map, make_selection_map
from functools import partial

st.set_page_config(initial_sidebar_state="collapsed", layout="wide")
page_styling()

st.title("Who Can Actually Reach a CDC? (by public transport)")

problem = setup_lokigi_site_problem_2sfca_pt()

intro_text = """
> "Same calculation, different assumption," your analyst says. "This time, nobody's driving."
<br><br>
> "It's the same two-step floating catchment area score as before - capacity, competition and travel distance rolled into one - but the travel times now come from buses and trains rather than cars. For a lot of Devon, that changes everything."
<br><br>
> "Watch how much more of the map turns red. A patient without a car might live the same number of miles from a CDC as their neighbour, but a missing bus route can put it effectively out of reach. These are often exactly the people who can least afford a taxi or a day off work."
<br><br>
> "Same catch as the car version," they add. "This is all worked out from the four CDCs open today - the candidate pins are there for you to choose from, not to show what adding one would do."
<br><br>
> "The travel limits above are longer than the car version on purpose - public transport journeys simply take more time. Try a few, and see whose access quietly disappears."
<br><br>
> They gesture at the map and fall silent, letting it make the argument for them.
"""

# Once a decision has been made on this page, drop the analyst intro so a
# revisit shows just the evidence and outcome.
if not st.session_state.site_submitted_2sfca_pt:
    write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/2sfca_pt.html",
    )
    st.iframe("app/assets/terminal_working/2sfca_pt.html", height=400)

# The proposed (blue) markers on this map remain clickable and drive the site
# selection; render_2sfca_map returns the st_folium result for that flow.
sfca_pt_selection_map = make_selection_map(
    partial(render_2sfca_map, problem, "pt", [60, 90, 120], 90),
    "2sfca_pt",
)
sfca_pt_selection_map()

render_notes_textbox()

if st.session_state.site_submitted_2sfca_pt:
    render_navigation(TWO_SFCA_PT)
