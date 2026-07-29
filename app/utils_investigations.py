from dataclasses import dataclass


@dataclass
class Investigation:
    id: str
    title: str
    page: str

    category: list[str]

    prerequisites: list[str]
    parent: str | None

    analyst_prompt: str

    recommended_next: list[str]
    is_entry_point: bool

    analyst_days: float
    icon: str = "arrow_forward"


DEMAND = Investigation(
    id="demand",
    title="Where is our demand?",
    page="app/Demand.py",
    category=["need"],
    prerequisites=[],
    parent=None,
    recommended_next=[
        "deprivation",
        "travel_car",
    ],
    analyst_prompt=("Show me the population aged 50-85 who may require CDC services."),
    is_entry_point=True,
    analyst_days=0.5,
    icon="groups_2",
)

DEPRIVATION = Investigation(
    id="deprivation",
    title="Where is there high need?",
    page="app/Deprivation.py",
    category=["equity"],
    prerequisites=[],
    parent=None,
    recommended_next=[
        "demand",
        "travel_car",
    ],
    analyst_prompt=("Show me areas experiencing the highest deprivation."),
    is_entry_point=True,
    analyst_days=0.5,
    icon="payment_arrow_down",
)

TRAVEL_CAR = Investigation(
    id="travel_car",
    title="Travel by car",
    page="app/Travel_Car.py",
    category=["accessibility"],
    prerequisites=[],
    parent=None,
    recommended_next=["travel_pt", "demand"],
    analyst_prompt=("Show me travel times to existing CDCs by car."),
    is_entry_point=True,
    analyst_days=3,
    icon="directions_car",
)

TRAVEL_PT = Investigation(
    id="travel_pt",
    title="Travel by public transport",
    page="app/Travel_Public_Transport.py",
    category=["accessibility"],
    prerequisites=[],
    parent="travel_car",
    recommended_next=["travel_car", "demand"],
    analyst_prompt=("Look at travel times if patients are using public transport."),
    is_entry_point=False,
    analyst_days=5,
    icon="train",
)

HOTSPOTS_DEMAND_DEPRIVATION = Investigation(
    id="hotspots_combined",
    title="Demand and deprivation hotspots",
    page="app/Demand_Deprivation_Hotspots.py",
    category=["need", "equity"],
    prerequisites=[
        "demand",
        "deprivation",
    ],
    recommended_next=[
        "travel_car",
        "travel_pt",
        "hotspots_demand_travel",
        "hotspots_deprivation_travel",
    ],
    parent=None,
    analyst_prompt=("Combine demand and deprivation to identify priority areas."),
    is_entry_point=False,
    analyst_days=1,
    icon="emergency_heat",
)

HOTSPOTS_DEMAND_TRAVEL = Investigation(
    id="hotspots_demand_travel",
    title="Demand and travel hotspots",
    page="app/Demand_Travel_Hotspots.py",
    category=["need", "accessibility"],
    # We'll probably just make this only look at car travel
    # as adding pt prerequisite is a bit harsh
    prerequisites=[
        "demand",
        "travel_car",
    ],
    recommended_next=["hotspots_deprivation_travel"],
    parent=None,
    analyst_prompt=(
        "Combine demand and travel time to explore hotspots of poor access for high demand areas."
    ),
    is_entry_point=False,
    analyst_days=1,
    icon="car_crash",
)

HOTSPOTS_DEPRIVATION_TRAVEL = Investigation(
    id="hotspots_deprivation_travel",
    title="Deprivation and Travel Hotspots",
    page="app/Deprivation_Travel_Hotspots.py",
    category=["equity", "accessibility"],
    # We'll probably just make this only look at car travel
    # as adding pt prerequisite is a bit harsh
    prerequisites=["deprivation", "travel_car"],
    recommended_next=["hotspots_demand_travel"],
    parent=None,
    analyst_prompt=(
        "Combine deprivation and travel time to explore hotspots of poor access for deprived communities."
    ),
    is_entry_point=False,
    analyst_days=1,
    icon="disc_full",
)

# NOTE: Catchment_Isochrones_car.py / Catchment_Isochrones_pt.py pages have been
# deleted (redundant with Travel_Car.py / Travel_Public_Transport.py, which already
# show travel-time data). The Investigation entries for them are removed too.

# 2-step floating catchment area (2SFCA) is a genuinely distinct metric: it fuses
# capacity, demand/competition and travel time into a single "how much service can
# the people here actually reach" score. It builds directly on two earlier pages, so
# both are prerequisites: the utilisation page (which introduces the capacity figures)
# and the matching travel-time page (car here, public transport for the PT version).
TWO_SFCA_CAR = Investigation(
    id="2sfca_car",
    title="Who can actually reach a CDC? (car)",
    page="app/Catchment_2sfca_car.py",
    category=["accessibility", "capacity"],
    prerequisites=["utilisation", "travel_car"],
    parent="utilisation",
    recommended_next=["travel_pt", "2sfca_pt"],
    analyst_prompt=(
        "Combine capacity, demand and car travel to show who can actually make use of a CDC."
    ),
    is_entry_point=False,
    analyst_days=2,
    icon="ambulance",
)

TWO_SFCA_PT = Investigation(
    id="2sfca_pt",
    title="Who can actually reach a CDC? (public transport)",
    page="app/Catchment_2sfca_pt.py",
    category=["accessibility", "capacity"],
    prerequisites=["utilisation", "travel_pt"],
    parent="utilisation",
    recommended_next=["travel_car", "2sfca_car"],
    analyst_prompt=(
        "Combine capacity, demand and travel on public transport to show who can actually make use of a CDC."
    ),
    is_entry_point=False,
    analyst_days=2.5,
    icon="departure_board",
)

UTILISATION = Investigation(
    id="utilisation",
    title="How well-used are existing CDCs?",
    page="app/Utilisation.py",
    category=["capacity"],
    prerequisites=[],
    parent=None,
    is_entry_point=False,
    recommended_next=["2sfca_car", "demand", "projected_demand", "travel_car"],
    analyst_prompt="Show me how well-used the existing four CDCs are.",
    analyst_days=2,
    icon="reduce_capacity",
)

PROJECTED_DEMAND = Investigation(
    id="projected_demand",
    title="Where will demand be in the future?",
    page="app/Projected_Demand.py",
    category=["need"],
    prerequisites=[
        "demand",
    ],
    parent="demand",
    is_entry_point=False,
    recommended_next=[
        "hotspots_combined",
        "deprivation",
        "utilisation",
        "travel_car",
    ],
    analyst_prompt="Show me how the 50-85 population is projected to change across Devon in the next 10 years.",
    analyst_days=2,
    icon="show_chart",
)

# At the bottom of investigations.py

ALL_INVESTIGATIONS: dict[str, Investigation] = {
    inv.id: inv
    for inv in [
        DEMAND,
        DEPRIVATION,
        TRAVEL_CAR,
        TRAVEL_PT,
        HOTSPOTS_DEMAND_DEPRIVATION,
        HOTSPOTS_DEMAND_TRAVEL,
        HOTSPOTS_DEPRIVATION_TRAVEL,
        TWO_SFCA_CAR,
        TWO_SFCA_PT,
        UTILISATION,
        PROJECTED_DEMAND,
    ]
}
