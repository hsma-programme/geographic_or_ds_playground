import streamlit as st
from app.utils import page_styling, load_devon_sites, write_terminal_html
import time
from PIL import Image
import pandas as pd
import pickle

st.set_page_config(initial_sidebar_state="collapsed", layout="wide")
page_styling()

st.title("Optimise - again")


intro_text = """
> But wait!
<br><br>
> The head of the region runs into the room.
<br><br>
> "We found 5 million pounds down the back of the sofa in the lunch room. We can have two CDCs now!"
<br><br>
> You feel the blood drain from your face.
<br><br>
> The sound of 80s music swells. You both turn to look at the data scientist, who shrugs nonchalently.
<br><br>
> "I can just change one parameter and rerun it. Give me five minutes."
"""

char_count, reveal_speed = write_terminal_html(
    intro_text,
    output_path="app/assets/terminal_working/optimise_6_sites.html",
)

st.iframe("app/assets/terminal_working/optimise_6_sites.html", height=325)


def get_gif_duration(filename):
    with Image.open(filename) as gif:
        total_duration_ms = 0

        try:
            while True:
                total_duration_ms += gif.info.get("duration", 100)
                gif.seek(gif.tell() + 1)
        except EOFError:
            pass

    return total_duration_ms / 1000


gif_path = "data/solution_car_6.gif"


# Cache the pickled solution dataframe so it loads once and is shared across
# reruns and sessions instead of being re-read on every rerun. cache_data hands
# each caller a copy, and the page copies before mutating anyway.
@st.cache_data
def load_car_6_solution_df():
    return pd.read_pickle("data/solution_car_6_best.pkl")


solution_df = load_car_6_solution_df()

existing_sites = load_devon_sites()
existing_sites = existing_sites[existing_sites["Existing"] == "Yes"][
    "Facility_Name"
].to_list()

run = st.button("Click here to run the optimiser")

if run:
    with st.spinner("The optimiser is starting up..."):
        time.sleep(3)

    st.write("The optimiser is evaluating all possible combinations of 6 sites")

    duration = get_gif_duration(gif_path)

    progress = st.progress(0)

    gif_placeholder = st.empty()
    gif_placeholder.image(gif_path)

    for i in range(100):
        time.sleep(duration / 100)
        progress.progress(i + 1)

    best_combo = solution_df[solution_df["solution_rank"] == 1]["site_names"].iloc[0]
    best_additional = [i for i in best_combo if i not in existing_sites]

    gif_placeholder.success(
        f"The optimiser finds the best additional two sites to be {' and '.join(best_additional)}."
    )

    solution_df_display = (
        solution_df.copy().drop(columns=["site_indices", "problem_df"]).round(2)
    )

    solution_df_display["site"] = solution_df_display["site_names"].apply(
        lambda x: "<br>".join([i for i in x if i not in existing_sites])
    )

    solution_df_display = solution_df_display.drop(columns="site_names")

    st.dataframe(
        solution_df_display,
        hide_index=True,
        column_order=[
            "solution_rank",
            "site",
            "site_names",
            "weighted_average",
            "unweighted_average",
            "90th_percentile",
            "max",
            "proportion_within_coverage_threshold",
        ],
    )
