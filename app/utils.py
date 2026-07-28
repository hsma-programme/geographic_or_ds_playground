import pandas as pd
import streamlit as st
import geopandas
import html
from app.utils_investigations import ALL_INVESTIGATIONS, Investigation
import base64
from PIL import Image
from io import BytesIO
from pathlib import Path
import os
from lokigi.site import SiteProblem

TERMINAL_DEFAULT_SPEED = 10
TERMINAL_COLOUR = "yellow"
MAXIMUM_BRIEFINGS = 6

# Shared basemap for every folium/leaflet map in the app, so switching styles
# only requires changing this one value. CartoDB Voyager keeps roads/labels
# visible (unlike Positron) while staying more muted than default OpenStreetMap.
BASEMAP_TILES = "cartodbvoyager"

# Which direction "best" sorts in for each optimiser solution_df metric - lower
# is better for every travel-time-style column, higher is better for coverage.
# Used on the Optimise pages so a rank looked up externally (e.g. "where does
# my chosen site fall for this metric?") lines up with lokigi's own internal
# ranking convention in SiteSolutionSet.plot_best_combination (documented as
# "highest for coverage proportions, lowest for travel costs").
RANK_METRIC_ASCENDING = {
    "weighted_average": True,
    "unweighted_average": True,
    "90th_percentile": True,
    "max": True,
    "proportion_within_coverage_threshold": False,
    "inter_tertile_ratio": True,
}

# Human-readable phrasing for each optimiser metric column, for embedding in
# sentences (lower-case) or as st.radio options (via .capitalize()). Keeps
# raw pandas column names like "proportion_within_coverage_threshold" off the
# screen - they're meaningful to whoever wrote the analysis, not the exec
# reading the page.
RANK_METRIC_LABELS = {
    "weighted_average": "weighted average travel time",
    "unweighted_average": "unweighted average travel time",
    "90th_percentile": "90th percentile travel time",
    "max": "maximum travel time",
    "proportion_within_coverage_threshold": "coverage within the travel time threshold",
    "inter_tertile_ratio": "equity (inter-tertile ratio)",
}

SITE_SELECTION_SUBMITTABLE = [
    "demand",
    "deprivation",
    "car_travel",
    "public_transport",
    "2sfca_car",
    "2sfca_pt",
    "utilisation",
    "projected_demand",
    "demand_deprivation_hotspots",
    "demand_travel_hotspots",
    "deprivation_travel_hotspots",
    "final",
]

# Human-readable phrasing for each SITE_SELECTION_SUBMITTABLE key, for
# embedding in sentences (lower-case) describing which page a site choice
# came from - e.g. "You chose X for travel by car" rather than the raw
# "car_travel" key.
SITE_SELECTION_LABELS = {
    "demand": "demand",
    "deprivation": "deprivation",
    "car_travel": "travel by car",
    "public_transport": "travel by public transport",
    "2sfca_car": "accessibility by car (2SFCA)",
    "2sfca_pt": "accessibility by public transport (2SFCA)",
    "utilisation": "CDC utilisation",
    "projected_demand": "projected demand",
    "demand_deprivation_hotspots": "demand & deprivation hotspots",
    "demand_travel_hotspots": "demand & travel hotspots",
    "deprivation_travel_hotspots": "deprivation & travel hotspots",
    "final": "your final decision",
}


# Load datasets
@st.cache_data
def load_travel_matrix_car():
    return pd.read_csv("data/devon_miu_travel_matrix.csv")


@st.cache_data
def load_travel_matrix_public():
    return pd.read_csv("data/devon_miu_travel_matrix_public_transport.csv")


@st.cache_data
def load_population_weighted_centroids(snapped=True):
    if snapped:
        return geopandas.read_file("data/travel_matrix_generation/snapped_pwc.gpkg")
    else:
        return geopandas.read_file(
            "data/travel_matrix_generation/LSOA_PopCentroids_EW_2021_V4_-4541397882496207062.gpkg"
        )


@st.cache_data
def load_devon_sites():
    existing_cdcs = pd.read_csv("data/devon_cdcs.csv")
    return geopandas.GeoDataFrame(
        existing_cdcs,  # Our pandas dataframe
        geometry=geopandas.points_from_xy(
            existing_cdcs[
                "Longitude"
            ],  # Our 'x' column (horizontal position of points)
            existing_cdcs["Latitude"],  # Our 'y' column (vertical position of points)
        ),
        crs="EPSG:4326",
    )


@st.cache_data
def load_cdc_utilisation():
    # Made-up weekly capacity vs. weekly caseload for the four *existing* CDCs.
    # These are illustrative teaching figures, not real activity data. Proposed
    # (not-yet-built) sites are deliberately absent - they have no utilisation.
    return pd.read_csv("data/devon_cdc_utilisation.csv")


@st.cache_data
def load_devon_sites_with_utilisation():
    """Existing CDCs as a GeoDataFrame with weekly_capacity / weekly_caseload
    columns merged in (proposed sites get NaN - they aren't built yet)."""
    sites = load_devon_sites()
    return sites.merge(load_cdc_utilisation(), on="Facility_Name", how="left")


@st.cache_data
def load_devon_geography():
    return geopandas.read_file("data/LSOA_Devon_2021_EW_BSC_V4.gpkg")


@st.cache_data
def load_deprivation():
    return pd.read_csv("data/devon_imd_2025_2021_LSOAs.csv")


@st.cache_data
def load_demand():
    return pd.read_csv("data/demand_MF_50_84.csv")


@st.cache_data
def create_demand_gdf():
    devon_gdf = load_devon_geography()
    demand_df = load_demand()
    full_gdf = devon_gdf.merge(demand_df, left_on="LSOA21NM", right_on="LSOA 2021 Name")
    return full_gdf


@st.cache_data
def load_demand_projected():
    return pd.read_csv("data/demand_MF_50_84_projected_2036.csv")


@st.cache_data
def create_projected_demand_gdf():
    devon_gdf = load_devon_geography()
    current_df = load_demand()
    projected_df = load_demand_projected()

    growth_df = current_df[["LSOA 2021 Name", "MF50-84", "Total"]].merge(
        projected_df[["LSOA 2021 Name", "MF50-84", "Total"]],
        on="LSOA 2021 Name",
        suffixes=(" (Now)", " (2036)"),
    )
    growth_df["MF50-84 Growth"] = (
        growth_df["MF50-84 (2036)"] - growth_df["MF50-84 (Now)"]
    )
    growth_df["MF50-84 Growth (%)"] = (
        (growth_df["MF50-84 (2036)"] / growth_df["MF50-84 (Now)"] - 1) * 100
    ).round(1)

    full_gdf = devon_gdf.merge(
        projected_df, left_on="LSOA21NM", right_on="LSOA 2021 Name"
    ).merge(
        growth_df[["LSOA 2021 Name", "MF50-84 Growth", "MF50-84 Growth (%)"]],
        on="LSOA 2021 Name",
    )
    return full_gdf


@st.cache_data
def create_deprivation_gdf():
    devon_gdf = load_devon_geography()
    deprivation_df = load_deprivation()
    full_gdf = devon_gdf.merge(
        deprivation_df, left_on="LSOA21NM", right_on="LSOA name (2021)"
    )
    return full_gdf


@st.cache_data
def load_demand_deprivation_hotspots():
    # Precomputed offline by data/generate_hotspots.py so the page doesn't run
    # Local Moran's I (spatial weights + permutation inference over 729 LSOAs)
    # live on every session. Re-run that script if the demand/deprivation inputs
    # change. Returns a GeoDataFrame with cluster_type / attribute_typology /
    # combined_score / p_value columns keyed to the Devon LSOA geometry.
    return pd.read_pickle("data/demand_deprivation_hotspots.pkl")


@st.cache_data
def load_demand_travel_hotspots():
    # Precomputed offline by data/generate_demand_travel_hotspots.py (a
    # solution-level analysis: it solves the existing-CDCs / car-travel problem
    # first, then runs Local Moran's I on demand vs travel time). Re-run that
    # script if the demand/car-travel inputs change. Returns a GeoDataFrame with
    # cluster_type / attribute_typology / combined_score / p_value / min_cost
    # columns keyed to the Devon LSOA geometry.
    return pd.read_pickle("data/demand_travel_hotspots.pkl")


@st.cache_data
def load_deprivation_travel_hotspots():
    # Precomputed offline by data/generate_deprivation_travel_hotspots.py (a
    # solution-level analysis: it solves the existing-CDCs / car-travel problem
    # first, then runs Local Moran's I on deprivation vs travel time). Re-run that
    # script if the deprivation/car-travel inputs change. Returns a GeoDataFrame
    # with cluster_type / attribute_typology / combined_score / p_value / min_cost
    # columns keyed to the Devon LSOA geometry.
    return pd.read_pickle("data/deprivation_travel_hotspots.pkl")


def write_terminal_html(
    text: str,
    output_path: str = "app/assets/terminal.html",
    colour: str = TERMINAL_COLOUR,
    glow_amount: float = 0.7,
    reveal_speed_ms: int = TERMINAL_DEFAULT_SPEED,
    cursor: str = "block",
    stay_blinking: bool = True,
):
    with open("app/assets/terminal.css") as f:
        css = f.read()
    with open("app/assets/terminal.js") as f:
        js = f.read()

    safe_text = html.escape(text, quote=True)
    strong_pct = int(glow_amount * 100)
    soft_pct = int(glow_amount * 40)

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<style>
    {css}
    :root {{
        --terminal-colour: {colour};
        --terminal-glow-strong: color-mix(in srgb, {colour} {strong_pct}%, transparent);
        --terminal-glow-soft: color-mix(in srgb, {colour} {soft_pct}%, transparent);
    }}
</style>
</head>
<body>
  <div id="typewrite" class="typeing" data-text="{safe_text}"></div>
  <script>
    var REVEAL_SPEED_MS = {reveal_speed_ms};
    var CURSOR = {repr(cursor)};
    var STAY_BLINKING = {"true" if stay_blinking else "false"};
    {js}
  </script>
</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(html_content)

    return len(text), reveal_speed_ms


def write_crt_html(
    image_path: str,
    output_path: str = "app/assets/crt_render.html",
    curvature: float = 0.15,
    scanlines: float = 0.3,
    vignette: float = 0.2,
):
    """
    Writes a self-contained HTML file applying CRTFilter.js to a target image,
    matching the architecture of your working terminal generator.
    """
    # 1. Read the local JavaScript file source
    # (Using utf-8 to ensure smooth reading across different OS environments)
    with open("app/assets/CRTFilter.js", "r", encoding="utf-8") as f:
        js_library = f.read()

    # 2. Convert the image asset to a base64 string
    image = Image.open(image_path)
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    image_b64 = base64.b64encode(buffered.getvalue()).decode()

    # 3. Generate the self-contained HTML
    # Note: We use type="module" so the browser handles the library's ES exports flawlessly.
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0;
            padding: 0;
            background-color: transparent;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
        }}
        canvas {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
        }}
    </style>
</head>
<body>

    <canvas id="crtCanvas"></canvas>

    <script type="module">
        // Inject the library directly into the module scope
        {js_library}

        // The library exports 'CRTFilterWebGL' natively.
        // Because we are inside a type="module" script, it is perfectly accessible here.
        const canvas = document.getElementById('crtCanvas');
        const ctx = canvas.getContext('2d');

        const img = new Image();
        img.src = "data:image/png;base64,{image_b64}";

        img.onload = function() {{
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);

            try {{
                // Initialize using the actual configuration keys required by the library
                const crt = new CRTFilterWebGL(canvas, {{
                    curvature: {curvature},
                    scanlineIntensity: {scanlines},
                    vignette: {vignette}
                }});

                // Fire up the animation frame render cycle
                crt.start();
            }} catch (e) {{
                console.error("CRTFilter runtime exception:", e);
            }}
        }};
    </script>
</body>
</html>"""

    # 4. Write out the static HTML file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_path


def record_page_visited(investigation: Investigation) -> None:
    """Record a visit to an investigation page by ID."""
    visited_ids = [v["id"] for v in st.session_state.pages_visited]
    if investigation.id not in visited_ids:
        step = len(st.session_state.pages_visited) + 1
        st.session_state.pages_visited.append(
            {
                "step": step,
                "id": investigation.id,
                "title": investigation.title,
                "analyst_days": investigation.analyst_days,
            }
        )


def _prerequisites_met(investigation: Investigation) -> bool:
    visited_ids = {v["id"] for v in st.session_state.pages_visited}
    return all(p in visited_ids for p in investigation.prerequisites)


def _already_visited(investigation: Investigation) -> bool:
    visited_ids = {v["id"] for v in st.session_state.pages_visited}
    return investigation.id in visited_ids


def _missing_prerequisites(investigation: Investigation) -> list[str]:
    """IDs of this investigation's prerequisites not yet visited."""
    visited_ids = {v["id"] for v in st.session_state.pages_visited}
    return [p for p in investigation.prerequisites if p not in visited_ids]


def investigation_button(investigation: Investigation) -> None:
    """
    Render a single investigation button.

    - Locked (visible but disabled, naming what's still needed) if
      prerequisites are unmet - shows the curriculum exists rather than
      hiding it entirely.
    - Greyed out (non-clickable) if already visited.
    - Active and clickable otherwise.
    """
    button_key = f"inv_btn_{investigation.id}"

    if not _prerequisites_met(investigation):
        missing_titles = ", ".join(
            ALL_INVESTIGATIONS[p].title
            for p in _missing_prerequisites(investigation)
            if p in ALL_INVESTIGATIONS
        )
        st.html(f"""
            <div class="investigation-tile investigation-tile-locked">
                <span style="margin-right: 8px; flex-shrink: 0;">&#128274;</span>
                <span><strong>Locked</strong> - {investigation.analyst_prompt}<br>
                    <span class="investigation-tile-requires">Requires: {missing_titles}</span>
                </span>
            </div>
        """)
        return

    visited = _already_visited(investigation)

    # # Use Iconify API to grab the Lucide icon as a clean, static SVG image
    # # Lucide icons on Iconify use the prefix "lucide" (e.g., lucide/search)
    # icon_url = f"https://api.iconify.design/lucide/{investigation.icon}.svg"

    # icon_html = f"""
    #     <img src="{icon_url}"
    #          style="width:18px; height:18px; vertical-align:middle; margin-right:8px;
    #                 {"filter: opacity(0.4) grayscale(100%);" if visited else ""}" />
    # """

    if visited:
        icon_url = f"https://api.iconify.design/lucide/{investigation.icon}.svg"
        icon_html = f'<img src="{icon_url}" style="width:18px; height:18px; vertical-align:middle; margin-right:8px; filter: opacity(0.4) grayscale(100%);" />'
        # Render as static greyed-out tile — no button interaction
        st.html(f"""
            <div class="investigation-tile investigation-tile-visited">
                {icon_html}
                <span>✓ {investigation.analyst_prompt}</span>
            </div>
        """)
    else:
        streamlit_icon = f":material/{investigation.icon}:"

        # Once the analyst's briefing budget is spent, every remaining choice is
        # greyed out (disabled) - the only way forward is to make a decision.
        if st.button(
            investigation.analyst_prompt,
            key=button_key,
            icon=streamlit_icon,
            width="stretch",
            disabled=capacity_exhausted(),
        ):
            record_page_visited(investigation)
            st.switch_page(investigation.page)


# components/investigation_button.py (addition)


def render_navigation(current: Investigation) -> None:
    """
    Render the full navigation section for a given investigation page.
    Call once at the bottom of each page after content.
    """
    render_capacity_status()

    st.subheader("Recommended next steps")
    st.caption("More options may unlock as you progress through the problem.")
    recommended = [
        ALL_INVESTIGATIONS[inv_id]
        for inv_id in current.recommended_next
        if inv_id in ALL_INVESTIGATIONS
    ]
    # Locked entries sink to the bottom of the list (stable sort keeps
    # everything else in its existing order) - what you can act on right
    # now stays primary, what's still locked reads as secondary/aspirational.
    for inv in sorted(recommended, key=lambda inv: not _prerequisites_met(inv)):
        investigation_button(inv)

    other_investigations = [
        inv
        for inv_id, inv in ALL_INVESTIGATIONS.items()
        if inv_id not in set(current.recommended_next) | {current.id}
    ]

    if any(not _already_visited(inv) for inv in other_investigations):
        st.divider()
        st.subheader("Other available investigations")
        for inv in sorted(
            other_investigations, key=lambda inv: not _prerequisites_met(inv)
        ):
            investigation_button(inv)

    st.subheader("Other Actions")
    # Allow jumping to decisions page
    if st.button(
        "Review your decisions so far and make your choice.",
        key="btn_make_your_choice",
        icon=":material/balance:",
        width="stretch",
    ):
        st.switch_page("app/Decide.py")

    # Escape hatch: wipe progress (session + browser storage) and start again.
    from app.persistence import render_reset_button

    render_reset_button(label="Start over", key="reset_nav")

    # Padding
    st.write("")
    st.write("")


def crt_filter_component(
    image_path: str, curvature: float, scanlines: float, vignette: float
):
    # 1. Prepare and read the Image
    image = Image.open(image_path)
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    image_b64 = base64.b64encode(buffered.getvalue()).decode()

    # 2. Read and patch the JS library
    try:
        js_lib_code = Path("app/assets/CRTFilter.js").read_text()

        # REMOVE the ES Module export syntax so the browser can run it as a normal script
        # This binds it to the global window scope safely inside our IIFE
        js_lib_code = js_lib_code.replace("export { CRTFilterWebGL };", "")
        js_lib_code = js_lib_code.replace("export default CRTFilterWebGL;", "")
    except FileNotFoundError:
        st.error("Could not find CRTFilter.js in app/assets/")
        return

    # Use a unique ID based on the path
    canvas_id = f"crt_{hash(image_path) & 0xFFFFFFFF}"

    html_code = f"""
    <div style="display: flex; justify-content: center; margin: 10px 0;">
        <canvas id="{canvas_id}" style="max-width: 100%; height: auto; border-radius: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.4);"></canvas>
    </div>

    <script>
        (function() {{
            // 1. Evaluate the modified library string safely
            if (typeof CRTFilterWebGL === 'undefined') {{
                {js_lib_code}
            }}

            const canvas = document.getElementById('{canvas_id}');
            if (!canvas) return;

            const ctx = canvas.getContext('2d');
            const img = new Image();
            img.src = "data:image/png;base64,{image_b64}";

            img.onload = function() {{
                // Apply source sizing
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.drawImage(img, 0, 0);

                try {{
                    // 2. Instantiate with the correct class name and parameters
                    const crt = new CRTFilterWebGL(canvas, {{
                        curvature: {curvature},
                        scanlineIntensity: {scanlines},
                        vignette: {vignette}
                    }});

                    # 3. Trigger the animation loop render lifecycle
                    crt.start();
                }} catch (e) {{
                    console.error("CRTFilter Execution Failure:", e);
                }}
            }};
        }})();
    </script>
    """

    st.html(html_code, unsafe_allow_javascript=True)


ANALYST_CAPACITY_MESSAGES = [
    {
        "analyses_remaining": 6,
        "message": (
            "Your analyst appears enthusiastic and optimistic. "
            "They have several coloured pens, a fresh notebook, and "
            "a coffee cup that is still warm."
        ),
    },
    {
        "analyses_remaining": 5,
        "message": "Your analyst appears a little less bright-eyed and bushy-tailed than when you "
        "first met them. Their coffee cup does not leave their sight.",
    },
    {
        "analyses_remaining": 4,
        "message": "Your analyst now appears to have upgraded to a hat with two coffee cups atttached and a straw. "
        "You make a note to review the coffee budget for the data department.",
    },
    {
        "analyses_remaining": 3,
        "message": "Your analyst appears to be disillusioned. They have been getting very angry about "
        "documentation (the lack of it) and data dictionaries (the absence of them) and something "
        "called a syntax error (an abundance of). You smile and nod politely.",
    },
    {
        "analyses_remaining": 2,
        "message": "Your analyst is mysteriously missing every time you try to talk to them. "
        "You swear you saw them exit via a ground-floor window when you approached "
        "the building recently, but you cannot prove this.",
    },
    {
        "analyses_remaining": 1,
        "message": "Your analyst informs you that they are considering a career in "
        "sheep farming. They have begun browsing rural property listings "
        "in Scotland during meetings. It may be prudent to reach a decision soon.",
    },
]


def analyses_used() -> int:
    """How many of the analyst's briefings have been spent so far.

    Each unique evidence page the user visits costs one briefing (see
    ``record_page_visited`` - revisits are free).
    """
    return len(st.session_state.pages_visited)


def analyses_remaining() -> int:
    """How many briefings the analyst can still provide."""
    return MAXIMUM_BRIEFINGS - analyses_used()


def total_analyst_days() -> float:
    """Cumulative analyst_days across every unique page visited so far.

    Purely informational - see render_capacity_status(). The briefing count
    is the only thing that actually gates progress; this never constrains
    anything, it just makes the (very uneven) real cost behind each flat
    "1 briefing" visible.
    """
    return sum(v["analyst_days"] for v in st.session_state.pages_visited)


def capacity_exhausted() -> bool:
    """True once every briefing has been spent."""
    return analyses_remaining() <= 0


def _capacity_message(remaining: int) -> str | None:
    """The analyst flavour text for a given number of remaining briefings."""
    for entry in ANALYST_CAPACITY_MESSAGES:
        if entry["analyses_remaining"] == remaining:
            return entry["message"]
    return None


def render_capacity_status() -> None:
    """Tell the user how many briefings they can still request.

    Uses the flavour text in ``ANALYST_CAPACITY_MESSAGES`` and escalates the
    styling (info -> warning -> error) as the budget runs down.
    """
    remaining = analyses_remaining()

    if remaining <= 0:
        st.error(
            f"Your analyst is out of capacity - all {MAXIMUM_BRIEFINGS} briefings "
            "have been used. You can no longer request new information, so it is "
            "time to make your decision.",
            icon=":material/hourglass_disabled:",
        )
    else:
        plural = "briefing" if remaining == 1 else "briefings"
        header = f"You can request **{remaining}** more {plural}."
        message = _capacity_message(remaining)
        body = f"{header}\n\n{message}" if message else header

        if remaining <= 2:
            st.warning(body, icon=":material/hourglass_bottom:")
        else:
            st.info(body, icon=":material/hourglass_top:")

    if st.session_state.pages_visited:
        days = total_analyst_days()
        n = len(st.session_state.pages_visited)
        briefing_word = "briefing" if n == 1 else "briefings"
        st.caption(
            f"Behind the scenes: your analyst has logged **{days:g} days** of work "
            f"across those {n} {briefing_word} so far - a reminder that the "
            "briefing count and the real cost aren't the same thing."
        )


def page_styling():
    with open("app/style.css", "r") as f:
        css_content = f.read()

    return st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)


# A one-shot "scroll back to the top" used after a decision is submitted, so the
# user lands at the top of the (now terminal-free) page instead of wherever the
# submit button happened to be. request_scroll_to_top() is called at submission;
# handle_scroll_to_top() runs once on the following rerun and consumes the flag.
SCROLL_TOP_FLAG = "_scroll_to_top"


def request_scroll_to_top():
    """Ask for the next run to scroll the page to the top."""
    st.session_state[SCROLL_TOP_FLAG] = True


def handle_scroll_to_top():
    """Emit the scroll-to-top JS if one was requested, then clear the flag."""
    if not st.session_state.get(SCROLL_TOP_FLAG):
        return
    st.session_state[SCROLL_TOP_FLAG] = False

    # A changing nonce makes Streamlit treat this as a fresh component each time,
    # so the scroll re-fires on repeat submissions rather than being cached.
    nonce = st.session_state.get("_scroll_nonce", 0) + 1
    st.session_state["_scroll_nonce"] = nonce

    # st.iframe (Streamlit >=1.60) auto-detects the HTML string and replaces the
    # deprecated st.components.v1.html.
    st.iframe(
        f"""<!DOCTYPE html>
<html><body><script>
    // {nonce}
    const doc = window.parent.document;
    const selectors = [
        'section.main',
        '[data-testid="stMain"]',
        '[data-testid="stAppViewContainer"]',
        '[data-testid="stMainBlockContainer"]',
    ];
    for (const sel of selectors) {{
        const el = doc.querySelector(sel);
        if (el) el.scrollTo({{top: 0, left: 0, behavior: "instant"}});
    }}
    window.parent.scrollTo({{top: 0, left: 0, behavior: "instant"}});
</script></body></html>""",
        height=1,
    )


def select_site_from_current_evidence():

    devon_sites = load_devon_sites()
    options = devon_sites[devon_sites["Existing"] == "No"]

    selected = st.pills(
        label="Based on the evidence on this page only, what one site would you choose?",
        options=options,
    )

    return selected


@st.cache_data
def load_car_travel_matrix():
    return pd.read_csv("data/travel_matrix_car.csv").fillna(9999.0)


@st.cache_data
def load_pt_travel_matrix():
    return pd.read_csv("data/travel_matrix_public_transport.csv")


@st.cache_resource
def setup_lokigi_site_problem_BASE():
    lokigi_site_problem = SiteProblem()

    lokigi_site_problem.add_demand(
        load_demand(), demand_col="MF50-84", location_id_col="LSOA 2021 Name"
    )

    lokigi_site_problem.add_region_geometry_layer(
        load_devon_geography(), common_col="LSOA21NM"
    )

    # lokigi_site_problem.add_equity_data(
    #     load_deprivation(),
    #     equity_col="Index of Multiple Deprivation (IMD) Decile (where 1 is most deprived 10% of LSOA",
    #     common_col="LSOA name (2021)",
    #     label="IMD",
    # )

    return lokigi_site_problem


@st.cache_resource
def setup_lokigi_site_problem_car_existing():
    lokigi_site_problem = setup_lokigi_site_problem_BASE().copy()

    devon_sites = load_devon_sites()

    devon_sites = devon_sites[devon_sites["Existing"] == "Yes"]

    lokigi_site_problem.add_sites(
        devon_sites,
        candidate_id_col="Facility_Name",
    )

    lokigi_site_problem.add_travel_matrix(
        load_car_travel_matrix(), unit="minutes", source_col="from_id"
    )

    return lokigi_site_problem


@st.cache_resource
def setup_lokigi_site_problem_utilisation():
    # Utilisation is a baseline diagnostic of the *existing* sites: how much of
    # each site's capacity today's caseload uses. It needs neither travel matrix
    # nor solve() - just the sites registered with capacity/current-load columns.
    lokigi_site_problem = setup_lokigi_site_problem_BASE().copy()

    existing_sites = load_devon_sites_with_utilisation()
    existing_sites = existing_sites[existing_sites["Existing"] == "Yes"]

    lokigi_site_problem.add_sites(
        existing_sites,
        candidate_id_col="Facility_Name",
        capacity_col="weekly_capacity",
        current_load_col="weekly_caseload",
    )

    return lokigi_site_problem


@st.cache_resource
def setup_lokigi_site_problem_car():
    lokigi_site_problem = setup_lokigi_site_problem_BASE().copy()

    lokigi_site_problem.add_sites(
        load_devon_sites(),
        candidate_id_col="Facility_Name",
        required_sites_col="Existing",
    )

    lokigi_site_problem.add_travel_matrix(
        load_car_travel_matrix(), unit="minutes", source_col="from_id"
    )

    return lokigi_site_problem


@st.cache_resource
def setup_lokigi_site_problem_pt():
    lokigi_site_problem = setup_lokigi_site_problem_BASE().copy()

    lokigi_site_problem.add_sites(
        load_devon_sites(),
        candidate_id_col="Facility_Name",
        required_sites_col="Existing",
    )

    lokigi_site_problem.add_travel_matrix(
        load_pt_travel_matrix(), unit="minutes", source_col="from_id"
    )

    return lokigi_site_problem


def _setup_lokigi_site_problem_2sfca(travel_matrix):
    # 2SFCA needs the three ingredients the earlier pages showed separately:
    # each existing site's capacity (supply), the population (demand, from BASE),
    # and how far apart they are (a travel matrix). Only the four *existing* CDCs
    # have capacity, so those are the sites we register. Proposed sites aren't
    # built and contribute no supply; they're overlaid on the map for selection
    # only, outside this lokigi problem.
    lokigi_site_problem = setup_lokigi_site_problem_BASE().copy()

    existing_sites = load_devon_sites_with_utilisation()
    existing_sites = existing_sites[existing_sites["Existing"] == "Yes"]

    lokigi_site_problem.add_sites(
        existing_sites,
        candidate_id_col="Facility_Name",
        capacity_col="weekly_capacity",
        current_load_col="weekly_caseload",
    )

    lokigi_site_problem.add_travel_matrix(
        travel_matrix, unit="minutes", source_col="from_id"
    )

    return lokigi_site_problem


@st.cache_resource
def setup_lokigi_site_problem_2sfca_car():
    return _setup_lokigi_site_problem_2sfca(load_car_travel_matrix())


@st.cache_resource
def setup_lokigi_site_problem_2sfca_pt():
    return _setup_lokigi_site_problem_2sfca(load_pt_travel_matrix())


# A single, shared notepad follows the user across every evidence page. The
# durable copy lives under a plain (non-widget) session-state key - Streamlit
# clears widget-scoped state whenever a widget isn't rendered on the previous
# run, which happens every time the user changes page, so the text area itself
# cannot be relied on to persist. Instead the widget writes into the durable key
# via its on_change callback, and is re-seeded from it on every run.
NOTES_STATE_KEY = "user_notes"
_NOTES_WIDGET_KEY = "_user_notes_widget"


def _persist_notes():
    st.session_state[NOTES_STATE_KEY] = st.session_state[_NOTES_WIDGET_KEY]


def render_notes_textbox(key=None):
    """Render the running notepad that follows the user from page to page.

    All evidence pages share one notepad (``st.session_state["user_notes"]``),
    so notes written on earlier pages are already present here.

    ``key`` is accepted for backwards compatibility with existing call sites but
    is no longer used to scope the notes - all pages share one notepad.
    """
    st.session_state.setdefault(NOTES_STATE_KEY, "")

    st.subheader("Write down any additional thoughts you have.")
    st.caption(
        "These notes follow you from page to page, so you can build up your "
        "thinking as you go."
    )

    # Re-seed the widget from the durable copy every run (see note above), then
    # let its on_change callback write any edits straight back into it.
    st.session_state[_NOTES_WIDGET_KEY] = st.session_state[NOTES_STATE_KEY]
    st.text_area(
        label="Your Thoughts",
        label_visibility="hidden",
        key=_NOTES_WIDGET_KEY,
        on_change=_persist_notes,
    )

    st.write("")
    st.write("")
