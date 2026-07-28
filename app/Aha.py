import streamlit as st
from app.utils import write_terminal_html

st.set_page_config(initial_sidebar_state="expanded", layout="wide")

intro_text = """
> But wait!
<br><br>
> A new person runs into the room. The sound of the 80s hit 'I am the one and only' seems to follow them.
<br><br>
> "I heard you have a location optimization problem. I came as soon as I could".
<br><br>
> They flick their action-hero hair back. The sound of a synthesizer swells in the distance.
<br><br>
> "The optimiser is ready to run. Let's take a look..."
"""

char_count, reveal_speed = write_terminal_html(
    intro_text,
    output_path="app/assets/terminal_working/demand.html",
)

st.iframe("app/assets/terminal_working/demand.html", height=275)

if st.button(
    "Click to boot the optimiser!",
    key="btn_optimise_5_sites",
    icon=":material/rocket_launch:",
    width="stretch",
):
    st.switch_page("app/Optimise_5_Sites.py")
