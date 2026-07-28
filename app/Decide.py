import streamlit as st
from app.utils import (
    page_styling,
    write_terminal_html,
    SITE_SELECTION_SUBMITTABLE,
    load_devon_sites,
    NOTES_STATE_KEY,
)

st.set_page_config(initial_sidebar_state="expanded", layout="wide")
page_styling()

st.title("Your Decision")

if not st.session_state.site_submitted_final:
    decisions = []

    for key in SITE_SELECTION_SUBMITTABLE:
        if "final" not in key:
            decisions.append(st.session_state[f"confirmed_site_{key}"])

    valid_decisions = [decision for decision in decisions if decision is not None]

    intro_text = """
> Your analyst has gone quiet. Query after query, map after map - and now, apparently, no more.
<br><br>
> They slide a single sheet across the desk: every site you picked, and what you were looking at when you picked it.
<br><br>
> It is, they mention without quite meeting your eye, not the same site every time.
"""

    write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/decide.html",
    )
    st.iframe("app/assets/terminal_working/decide.html", height=200)

    n = len(valid_decisions)
    distinct_sites = {decision["Site"] for decision in valid_decisions}
    n_distinct = len(distinct_sites)
    briefing_word = "briefing" if n == 1 else "briefings"

    if n_distinct == 1:
        st.subheader(f"{n} {briefing_word}. One site, every time.")
        st.caption(
            f"Every one of your {n} {briefing_word} pointed to the same place. "
            "Let's see if the maths agrees."
        )
    else:
        site_word = "site" if n_distinct == 1 else "sites"
        st.subheader(f"{n} {briefing_word}. {n_distinct} different {site_word}.")
        st.caption(
            "Different evidence pointed you in different directions. That's not "
            "a mistake - it's the whole reason this exercise exists."
        )

    st.write("")

    for decision in valid_decisions:
        with st.container(border=True):
            st.markdown(
                f":material/location_on: **{decision['Site']}** — {decision['What']}"
            )

    devon_sites = load_devon_sites()
    selectable_sites = devon_sites[devon_sites["Existing"] == "No"]

    notes = st.session_state.get(NOTES_STATE_KEY, "").strip()
    if notes:
        st.write("<br>", unsafe_allow_html=True)
        st.markdown("**The notes you gathered as you explored the evidence:**")
        # Preserve the user's line breaks when rendering as markdown.
        st.info(notes.replace("\n", "  \n"))

    st.write("<br>", unsafe_allow_html=True)

    intro_text = """
    > Your final report and recommendation is due today.
    <br><br>
    > You pause, the cursor in your report flashing. What site are you going to recommend?
    """

    write_terminal_html(
        intro_text,
        output_path="app/assets/terminal_working/decide_2.html",
    )
    st.iframe("app/assets/terminal_working/decide_2.html", height=120)

    st.write("<br>", unsafe_allow_html=True)

    selected_site_final = st.pills(
        "Select your final choice from all of the available sites by clicking on the site name below.",
        selectable_sites,
    )

    st.write("<br><br>", unsafe_allow_html=True)

    if st.button(
        "Make your choice.",
        key="btn_make_choice_5_sites",
        icon=":material/balance:",
        width="stretch",
        disabled=selected_site_final is None,
    ):
        if not st.session_state.site_submitted_final:
            st.session_state.confirmed_site_final = selected_site_final
            st.session_state.site_submitted_final = True
        st.switch_page("app/Aha.py")
else:
    if st.button(
        "You made your choice already. Click here to proceed.",
        key="btn_make_choice_5_sites",
        icon=":material/balance:",
        width="stretch",
    ):
        st.switch_page("app/Aha.py")
