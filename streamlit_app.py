import streamlit as st
from app.utils import SITE_SELECTION_SUBMITTABLE, handle_scroll_to_top
from app.persistence import (
    get_store,
    load_into_session,
    save,
    maybe_restore_page,
    record_current_page,
    CURRENT_PAGE_KEY,
)

st.set_page_config(initial_sidebar_state="collapsed", layout="wide")

# Browser-local persistence so a refresh / dropped websocket / container restart
# doesn't wipe a user's progress. The store is built once per run (it renders a
# hidden localStorage component); if the optional component isn't installed this
# is a no-op and the app behaves exactly as before.
progress_store = get_store()

states = [
    "catchment_page_visited",
    "demand_deprivation_hotspots_page_visited",
    "demand_page_visited",
    "deprivation_page_visited",
    "homepage_visited",
    "optimize_page_visited",
    "travel_page_visited",
]

for state in states:
    if state not in st.session_state:
        st.session_state[state] = False

if "pages_visited" not in st.session_state:
    st.session_state.pages_visited = []

# A single shared notepad that follows the user across every evidence page.
if "user_notes" not in st.session_state:
    st.session_state.user_notes = ""

# The page the user is currently on (persisted so a refresh returns them here).
if CURRENT_PAGE_KEY not in st.session_state:
    st.session_state[CURRENT_PAGE_KEY] = ""

if "homepage_visited" not in st.session_state:
    st.session_state.homepage_visited = False

# Add in a state ensuring they see at least one DEMAND-related page before unlocking
# the 'make a recommendation' button
if "observed_one_demand_page" not in st.session_state:
    st.session_state.observed_one_demand_page = False

# Add in a state ensuring they see at least one ACCESSIBILITY-related page before unlocking
# the 'make a recommendation' button
if "observed_one_accessibility_page" not in st.session_state:
    st.session_state.observed_one_accessibility_page = False


# Set up session keys relating to site submissions
for i in SITE_SELECTION_SUBMITTABLE:
    if f"confirmed_site_{i}" not in st.session_state:
        st.session_state[f"confirmed_site_{i}"] = None
    if f"site_submitted_{i}" not in st.session_state:
        st.session_state[f"site_submitted_{i}"] = False


# Layer any previously-saved progress on top of the freshly-seeded defaults,
# before the page renders.
load_into_session(progress_store)


pages = [
        st.Page("app/Homepage.py", title="Welcome!", visibility="hidden"),
        st.Page("app/Demand.py", title="Where is our demand?", visibility="hidden"),
        st.Page(
            "app/Deprivation.py", title="Where is there high need?", visibility="hidden"
        ),
        st.Page(
            "app/Demand_Deprivation_Hotspots.py",
            title="Where do areas of both high demand and high deprivation occur?",
            visibility="hidden",
        ),
        # Transport pages without cross-border travel to nearest CDCs
        st.Page(
            "app/Travel_Car.py",
            title="What does travel by car look like now?",
            visibility="hidden",
        ),
        st.Page(
            "app/Travel_Public_Transport.py",
            title="What does travel by public transport look like now?",
            visibility="hidden",
        ),
        st.Page(
            "app/Deprivation_Travel_Hotspots.py",
            title="Where do high deprivation and high travel times intersect?",
            visibility="hidden",
        ),
        st.Page(
            "app/Demand_Travel_Hotspots.py",
            title="Where do high demand and high travel times intersect?",
            visibility="hidden",
        ),
        # 2 step floating catchment area pages: fuse capacity, demand and travel
        # into a single accessibility score. They depend on the utilisation page's
        # capacity figures (see prerequisites in app/utils_investigations.py).
        st.Page(
            "app/Catchment_2sfca_car.py",
            title="Who can actually reach a CDC? (car)",
            visibility="hidden",
        ),
        st.Page(
            "app/Catchment_2sfca_pt.py",
            title="Who can actually reach a CDC? (public transport)",
            visibility="hidden",
        ),
        # Explore the utilisation of existing CDCs (capacity vs catchment)
        st.Page(
            "app/Utilisation.py",
            title="How well-used are existing CDCs?",
            visibility="hidden",
        ),
        # Display projected demand
        st.Page(
            "app/Projected_Demand.py",
            title="Where will demand be in the future?",
            visibility="hidden",
        ),
        # This page will also have a summary of all of the information they have uniquely collected.
        st.Page("app/Decide.py", title="What's your Decision?", visibility="hidden"),
        # Next, we go to the optimization page.
        st.Page(
            "app/Optimise_5_Sites.py",
            title="What does the maths say? (one new site)",
            visibility="hidden",
        ),
        st.Page(
            "app/Optimise_6_Sites.py",
            title="What does the maths say? (two new sites)",
            visibility="hidden",
        ),
        st.Page(
            "app/Aha.py",
            title="A new challenger appears!",
            visibility="hidden",
        ),
]

pg = st.navigation(pages)

# After progress is restored, bring the user back to the page they were on when
# they last left (refresh/crash), then record where they are now.
pages_by_path = {p.url_path: p for p in pages}
maybe_restore_page(pg, pages_by_path)
record_current_page(pg)

# If a decision was just submitted, scroll back to the top of the page.
handle_scroll_to_top()

pg.run()

# Persist any changes made during this run (writes only when the snapshot
# actually changed, so unchanged reruns cost nothing).
save(progress_store)
