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
MAXIMUM_BRIEFINGS = 5

SITE_SELECTION_SUBMITTABLE = [
    "demand",
    "deprivation",
    "car_travel",
    "public_transport",
    "utilisation",
    "projected_demand",
]


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


def investigation_button(investigation: Investigation) -> None:
    """
    Render a single investigation button.

    - Hidden if prerequisites are unmet.
    - Greyed out (non-clickable) if already visited.
    - Active and clickable otherwise.
    """
    if not _prerequisites_met(investigation):
        return  # Hidden entirely

    visited = _already_visited(investigation)
    button_key = f"inv_btn_{investigation.id}"

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
            <div style="
                display: flex;
                align-items: center;
                padding: 12px 16px;
                border-radius: 8px;
                border: 1.5px solid #e0e0e0;
                background: #f7f7f7;
                color: #aaa;
                font-size: 0.92rem;
                cursor: not-allowed;
                margin-bottom: 6px;
                user-select: none;
            ">
                {icon_html}
                <span>✓ {investigation.analyst_prompt}</span>
            </div>
        """)
    else:
        streamlit_icon = f":material/{investigation.icon}:"

        if st.button(
            investigation.analyst_prompt,
            key=button_key,
            icon=streamlit_icon,
            use_container_width=True,
        ):
            record_page_visited(investigation)
            st.switch_page(investigation.page)


# components/investigation_button.py (addition)


def render_navigation(current: Investigation) -> None:
    """
    Render the full navigation section for a given investigation page.
    Call once at the bottom of each page after content.
    """
    st.subheader("Recommended next steps")
    for inv_id in current.recommended_next:
        if inv_id in ALL_INVESTIGATIONS:
            investigation_button(ALL_INVESTIGATIONS[inv_id])

    other_investigations = [
        inv
        for inv_id, inv in ALL_INVESTIGATIONS.items()
        if inv_id not in set(current.recommended_next) | {current.id}
    ]

    if any(
        _prerequisites_met(inv) and not _already_visited(inv)
        for inv in other_investigations
    ):
        st.divider()
        st.subheader("Other available investigations")
        for inv in other_investigations:
            investigation_button(inv)

    st.subheader("Other Actions")
    # Allow jumping to decisions page
    if st.button(
        "Review your decisions so far and make your choice.",
        key="btn_make_your_choice",
        icon=":material/balance:",
        use_container_width=True,
    ):
        st.switch_page("app/Decide.py")

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
        "analyses_remaining": 5,
        "message": (
            "Your analyst appears enthusiastic and optimistic. "
            "They have several coloured pens, a fresh notebook, and "
            "a coffee cup that is still warm."
        ),
    },
    {
        "analyses_remaining": 4,
        "message": "Your analyst appears a little less bright-eyed and bushy-tailed than when you"
        "first met them. Their coffee cup does not leave their sight.",
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
        "You swear you saw them exit via a ground-floor bathroom window when you approached "
        "the building recently, but you cannot prove this.",
    },
    {
        "analyses_remaining": 1,
        "message": "Your analyst informs you that they are considering a career in "
        "sheep farming. They have begun browsing rural property listings "
        "in Scotland during meetings. It may be prudent to reach a decision soon.",
    },
]


def page_styling():
    with open("app/style.css", "r") as f:
        css_content = f.read()

    return st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)


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


def render_notes_textbox(key):
    st.subheader("Write down any additional thoughts you have.")
    st.caption("These will be saved to your notes.")
    st.text_area(
        label="Your Thoughts",
        label_visibility="hidden",
        key=f"additional_thoughts_{key}",
    )

    st.write("")
    st.write("")
