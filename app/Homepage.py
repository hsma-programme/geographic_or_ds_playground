from pathlib import Path
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

cola, colb = st.columns([0.6, 0.4])

intro_text = """
> You are a senior manager who has been given funding for an additional community diagnostic centre (CDC) in Devon.
<br><br>
> You have been told to improve access for those between 50 and 85, particularly for those from more deprived areas.
<br><br>
> People may only use CDCs within Devon. They cannot cross the Devon border to access a different CDC.
<br><br>
> You have been assigned a rather junior analyst who can provide information, but can only follow very specific instructions.
"""

intro_text_pt_2 = f"""
> Due to capacity constraints, your analyst can provide you with a maximum of {num2words(MAXIMUM_BRIEFINGS)} briefings on areas of your choosing. The frazzled-looking data team lead has assured you it will be plenty.
<br><br>
> (While some of these will take your analyst an afternoon, and others the better part of a fortnight, the briefing count mysteriously does not know the difference).
<br><br>
> What is your first request to your data analyst?
"""

reveal_speed = TERMINAL_DEFAULT_SPEED if not st.session_state.homepage_visited else 0

char_count, _ = write_terminal_html(
    intro_text,
    output_path="app/assets/terminal_working/homepage.html",
    reveal_speed_ms=reveal_speed,
    stay_blinking=False,
)

st.session_state.homepage_visited = True

with cola:
    st.iframe(Path("app/assets/terminal_working/homepage.html"))

with colb:
    generated_crt = write_crt_html(
        image_path="app/assets/homepage.png",
        output_path="app/assets/crt_working/homepage.html",
        curvature=0.5,
        scanlines=0.6,
    )
    st.iframe(Path(generated_crt))

# Pause between one piece of text finishing and the next appearing.
pause_ms = 375 if reveal_speed else 0

# Hold the second block until the first has finished typing. The two blocks are
# separate iframes, so they can't signal each other - this is an estimate from
# the first block's length and speed.
pt_2_delay_ms = char_count * reveal_speed + pause_ms

pt_2_char_count, _ = write_terminal_html(
    intro_text_pt_2,
    output_path="app/assets/terminal_working/homepage_pt_2.html",
    reveal_speed_ms=reveal_speed,
    start_delay_ms=pt_2_delay_ms,
)

st.iframe(Path("app/assets/terminal_working/homepage_pt_2.html"))

# Likewise hold the buttons and briefing count until the second block is done.
# visibility is animated alongside opacity so the buttons can't be clicked
# while they're still invisible.
if reveal_speed:
    actions_delay_ms = pt_2_delay_ms + pt_2_char_count * reveal_speed + pause_ms
    st.markdown(
        f"""<style>
        @keyframes homepage-actions-reveal {{
            from {{ opacity: 0; visibility: hidden; }}
            to {{ opacity: 1; visibility: visible; }}
        }}
        .st-key-homepage_actions {{
            animation: homepage-actions-reveal 0.6s ease {actions_delay_ms}ms both;
        }}
        </style>""",
        unsafe_allow_html=True,
    )

with st.container(key="homepage_actions"):
    col1, col2, col3 = st.columns(3)

    with col1:
        investigation_button(DEMAND)

    with col2:
        investigation_button(DEPRIVATION)

    with col3:
        investigation_button(TRAVEL_CAR)

    render_capacity_status()

st.write("")
