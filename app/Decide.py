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

if not st.session_state.site_submitted_final:
    decisions = []

    for key in SITE_SELECTION_SUBMITTABLE:
        if "final" not in key:
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

    st.write("<br><br>", unsafe_allow_html=True)

    selected_site_final = st.pills(
        "Select your final choice from all of the available sites by clicking on the site name below.",
        selectable_sites,
    )

    st.write("<br><br>", unsafe_allow_html=True)

    if st.button(
        "Make your choice.",
        key="btn_make_choice_5_sites",
        icon=":material/balance:",
        use_container_width=True,
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
        use_container_width=True,
    ):
        st.switch_page("app/Aha.py")
