import streamlit as st
from app.utils import (
    page_styling,
    write_terminal_html,
    SITE_SELECTION_SUBMITTABLE,
    load_devon_sites,
)

st.set_page_config(initial_sidebar_state="collapsed", layout="wide")
page_styling()

st.write("")
st.write("")

decisions = []

for key in SITE_SELECTION_SUBMITTABLE:
    decisions.append(st.session_state[f"confirmed_site_{key}"])

decision_string = [
    f"You chose {decision['Site']} for {decision['What'].lower().replace('_', ' ')}"
    for decision in decisions
    if decision is not None
]

st.info(
    f"""
    {"\n\n".join(decision_string)}
    """
)


devon_sites = load_devon_sites()
selectable_sites = devon_sites[devon_sites["Existing"] == "No"]


st.pills("Select your final choice.", selectable_sites)


intro_text = """
> But wait!
<br><br>
> A new computer person runs into the room. The sound of the 80s hit 'I am the one and only' seems to follow them.
<br><br>
> "I heard you have a location optimization problem. I came as soon as I could".
<br><br>
> They flick their action-hero hair back.
<br><br>
> "The optimiser is ready to run. Let's take a look..."
"""

char_count, reveal_speed = write_terminal_html(
    intro_text,
    output_path="app/assets/terminal_working/demand.html",
)

st.iframe("app/assets/terminal_working/demand.html", height=275)


if st.button(
    "Make your choice.",
    key="btn_optimise_5_sites",
    icon=":material/balance:",
    use_container_width=True,
):
    st.switch_page("app/Optimise_5_Sites.py")
