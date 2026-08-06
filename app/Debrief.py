from pathlib import Path
import streamlit as st
from app.utils import (
    page_styling,
    write_terminal_html,
    INVESTIGATION_ID_TO_SITE_KEY,
    total_analyst_days,
    MAXIMUM_BRIEFINGS,
    NOTES_STATE_KEY,
)
from app.utils_investigations import ALL_INVESTIGATIONS

st.set_page_config(initial_sidebar_state="expanded", layout="wide")
page_styling()

st.title("Debrief")

intro_text = """
> Your analyst reappears one last time, note in hand.
<br><br>
> "Before you file this away," they say, "three things worth remembering about what you just did."
"""

write_terminal_html(
    intro_text,
    output_path="app/assets/terminal_working/debrief.html",
)
st.iframe(Path("app/assets/terminal_working/debrief.html"), height=175)

st.subheader("What each briefing was actually asking")
st.caption(
    "Every analysis on this site drew a map, but underneath every map was a "
    "single number that \"best\" was implicitly judged against - and it was "
    "rarely the same number twice."
)

for visit in st.session_state.pages_visited:
    investigation = ALL_INVESTIGATIONS.get(visit["id"])
    site_key = INVESTIGATION_ID_TO_SITE_KEY.get(visit["id"])
    chosen = st.session_state.get(f"confirmed_site_{site_key}") if site_key else None

    with st.container(border=True):
        st.markdown(f"**{visit['step']}. {visit['title']}**")
        if investigation is not None:
            st.caption(f"Implicitly asking about: {investigation.implicit_measure}")
        if chosen is not None:
            st.markdown(f":material/location_on: You picked **{chosen['Site']}** here.")

if st.session_state.confirmed_site_final is not None:
    st.info(
        f"Your final recommendation was **{st.session_state.confirmed_site_final}**.",
        icon=":material/flag:",
    )

notes = st.session_state.get(NOTES_STATE_KEY, "").strip()
if notes:
    st.write("")
    st.subheader("The notes you gathered along the way")
    st.info(notes.replace("\n", "  \n"))

st.divider()
st.subheader("The budget didn't know the difference")
n_briefings = len(st.session_state.pages_visited)
days = total_analyst_days()
briefing_word = "briefing" if n_briefings == 1 else "briefings"
st.markdown(
    f"You spent **{n_briefings}** of your **{MAXIMUM_BRIEFINGS}** {briefing_word}. "
    f"Behind that flat count, your analyst actually logged **{days:g} days** of "
    "work - anywhere from half a day (raw demand) to five days (public "
    "transport travel times) per briefing. Every briefing cost you one slot "
    "either way."
)

st.divider()
st.subheader("Three things worth remembering")

st.markdown(
    "**1. There was no single number that settled this.** Every \"best site\" "
    "you saw depended on which question you happened to ask - demand alone, "
    "deprivation alone, travel time, capacity-adjusted access, or how many "
    "people are still left behind. Different, equally reasonable questions "
    "pointed at different sites."
)
st.markdown(
    "**2. Changing what the optimiser ranks on changes who wins.** The "
    "\"Rank On...\" control on the Optimise pages ran the exact same "
    "brute-force search each time - it only ever re-sorted results that had "
    "already been computed - and still moved the top answer. A location "
    "optimisation result is only ever an answer to the specific objective it "
    "was told to optimise."
)
st.markdown(
    "**3. The direction \"equity\" points was a choice, not a fact.** This "
    "analysis scored the inter-tertile ratio as *lower is better* - rewarding "
    "an option that actively closes the gap for the most deprived areas - "
    "rather than scoring it against a target of 1.0, which would have "
    "rewarded even spread instead and shortlisted different sites. Both are "
    "defensible. Neither is neutral."
)
