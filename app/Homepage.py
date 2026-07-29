import streamlit as st
from app.utils import (
    write_terminal_html,
    investigation_button,
    MAXIMUM_BRIEFINGS,
    render_capacity_status,
    write_crt_html,
    page_styling,
    TERMINAL_DEFAULT_SPEED,
)
from app.utils_investigations import DEMAND, TRAVEL_CAR, DEPRIVATION
from num2words import num2words

st.set_page_config(initial_sidebar_state="collapsed", layout="wide")
page_styling()

st.title("Welcome")

cola, colb = st.columns([0.7, 0.3])

intro_text = f"""
> You are a senior manager who has been given funding for an additional community diagnostic centre (CDC) in Devon.
<br><br>
> You have been told to improve access for those between 50 and 85.
<br><br>
> People may only use CDCs within Devon. They cannot cross the Devon border to access a different CDC.
<br><br>
> You have been assigned a rather junior analyst who can provide information, but can only follow very specific instructions.
<br><br>
> Due to capacity constraints, your analyst can provide you with a maximum of {num2words(MAXIMUM_BRIEFINGS)} briefings on areas of your choosing.
<br><br>
> Some of these will take your analyst an afternoon; others the better part of a fortnight. The briefing count does not know the difference - much like most budgets don't.
<br><br>
> The frazzled-looking data team lead has assured you it will be plenty.
<br><br>
> What is your first request to your data analyst?
"""

reveal_speed = TERMINAL_DEFAULT_SPEED if not st.session_state.homepage_visited else 0

write_terminal_html(
    intro_text,
    output_path="app/assets/terminal_working/homepage.html",
    reveal_speed_ms=reveal_speed,
)

st.session_state.homepage_visited = True

with cola:
    st.iframe("app/assets/terminal_working/homepage.html")

with colb:
    generated_crt = write_crt_html(
        image_path="app/assets/homepage.jpeg",
        output_path="app/assets/crt_working/homepage.html",
        curvature=0.5,
        scanlines=0.6,
    )
    st.iframe(generated_crt)

render_capacity_status()

col1, col2, col3 = st.columns(3)

with col1:
    investigation_button(DEMAND)

with col2:
    investigation_button(DEPRIVATION)

with col3:
    investigation_button(TRAVEL_CAR)
