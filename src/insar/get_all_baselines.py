import asf_search as asf
import geopandas as gpd
import pandas as pd
from pathlib import Path


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

AOI_FILE = PROJECT_ROOT / "config" / "mine_aoi.geojson"
PRIORITY_FILE = PROJECT_ROOT / "config" / "sentinel1_priority_pairs.csv"
OUTPUT_FILE = PROJECT_ROOT / "config" / "sentinel1_all_dynamic_baselines.csv"


# ============================================================
# SEARCH PERIOD
# ============================================================

START_DATE = "2024-01-01"
END_DATE = "2025-12-31"

# Maximum temporal separation for candidate pairs
MAX_TEMPORAL_DAYS = 24


print("=" * 70)
print("       DYNAMIC BASELINE SEARCH FOR ALL PRIORITY SCENES")
print("=" * 70)


# ============================================================
# 1. LOAD AOI
# ============================================================

print("\nLoading AOI:")
print(AOI_FILE)

aoi = gpd.read_file(AOI_FILE)
aoi = aoi.to_crs("EPSG:4326")

geometry = aoi.geometry.union_all()
wkt = geometry.wkt

print("AOI loaded successfully.")
print("Geometry:", geometry.geom_type)


# ============================================================
# 2. SEARCH ASF
# ============================================================

print("\nSearching ASF...")
print("Dataset    : Sentinel-1")
print("Product    : SLC")
print("Start date :", START_DATE)
print("End date   :", END_DATE)

results = asf.search(
    platform=asf.PLATFORM.SENTINEL1,
    intersectsWith=wkt,
    start=START_DATE,
    end=END_DATE,
    processingLevel=asf.PRODUCT_TYPE.SLC,
)

print("\nASF search completed.")
print("Total scenes found:", len(results))


# ============================================================
# 3. LOAD PRIORITY PAIRS
# ============================================================

print("\nLoading priority pairs:")
print(PRIORITY_FILE)

priority_df = pd.read_csv(PRIORITY_FILE)

print("Priority pairs loaded:", len(priority_df))


# ============================================================
# 4. GET UNIQUE MASTER/REFERENCE SCENES
# ============================================================

# Our priority-pair CSV uses "master_scene"
# as the reference scene.

reference_column = "master_scene"

if reference_column not in priority_df.columns:

    print("\nERROR:")
    print("The priority CSV does not contain:")
    print(reference_column)

    print("\nAvailable columns:")
    print(priority_df.columns.tolist())

    raise SystemExit


reference_scenes = (
    priority_df[reference_column]
    .dropna()
    .unique()
)

print("\nUnique reference scenes:", len(reference_scenes))


# ============================================================
# 5. CREATE ASF SCENE LOOKUP
# ============================================================

scene_lookup = {}

for scene in results:

    scene_name = scene.properties.get(
        "sceneName",
        ""
    )

    if scene_name:
        scene_lookup[scene_name] = scene


print("ASF scene lookup created.")
print("Scenes available for lookup:", len(scene_lookup))


# ============================================================
# 6. PROCESS EACH REFERENCE SCENE
# ============================================================

all_rows = []


for index, reference_id in enumerate(
    reference_scenes,
    start=1
):

    print("\n" + "-" * 70)

    print(
        f"REFERENCE {index}/{len(reference_scenes)}"
    )

    print(reference_id)


    # ========================================================
    # FIND REFERENCE SCENE
    # ========================================================

    reference = scene_lookup.get(
        reference_id
    )


    if reference is None:

        print(
            "WARNING: Reference scene not found in ASF search."
        )

        all_rows.append({

            "reference_scene": reference_id,

            "secondary_scene": "",

            "reference_date": "",

            "secondary_date": "",

            "orbit_direction": "",

            "relative_orbit": "",

            "frame": "",

            "temporal_baseline_days": "",

            "asf_temporal_baseline": "",

            "perpendicular_baseline_m": "",

            "status": "REFERENCE_NOT_FOUND"
        })

        continue


    # ========================================================
    # REFERENCE METADATA
    # ========================================================

    properties = reference.properties

    reference_date = properties.get(
        "startTime",
        ""
    )

    orbit_direction = properties.get(
        "flightDirection",
        ""
    )

    relative_orbit = properties.get(
        "pathNumber",
        ""
    )

    frame = properties.get(
        "frameNumber",
        ""
    )

    polarization = properties.get(
        "polarization",
        ""
    )

    beam_mode = properties.get(
        "beamModeType",
        ""
    )

    platform = properties.get(
        "platform",
        ""
    )


    print("\nReference metadata:")

    print(
        "Date        :",
        reference_date
    )

    print(
        "Path        :",
        relative_orbit
    )

    print(
        "Frame       :",
        frame
    )

    print(
        "Direction   :",
        orbit_direction
    )

    print(
        "Polarization:",
        polarization
    )

    print(
        "Beam mode   :",
        beam_mode
    )


    # ========================================================
    # CONVERT REFERENCE DATE
    # ========================================================

    try:

        reference_datetime = pd.to_datetime(
            reference_date,
            utc=True
        )

    except Exception as error:

        print(
            "ERROR converting reference date:",
            error
        )

        continue


    # ========================================================
    # GET BASELINE STACK
    # ========================================================

    print("\nRequesting ASF baseline stack...")


    try:

        stack = reference.stack()

        print(
            "Stack scenes:",
            len(stack)
        )

    except Exception as error:

        print(
            "ERROR while requesting stack:"
        )

        print(error)

        all_rows.append({

            "reference_scene": reference_id,

            "secondary_scene": "",

            "reference_date": reference_date,

            "secondary_date": "",

            "orbit_direction": orbit_direction,

            "relative_orbit": relative_orbit,

            "frame": frame,

            "temporal_baseline_days": "",

            "asf_temporal_baseline": "",

            "perpendicular_baseline_m": "",

            "status": "BASELINE_STACK_ERROR"
        })

        continue


    # ========================================================
    # FILTER COMPATIBLE SCENES
    # ========================================================

    compatible = []


    for secondary in stack:

        secondary_properties = (
            secondary.properties
        )


        secondary_scene = (
            secondary_properties.get(
                "sceneName",
                ""
            )
        )


        secondary_direction = (
            secondary_properties.get(
                "flightDirection",
                ""
            )
        )


        secondary_path = (
            secondary_properties.get(
                "pathNumber",
                ""
            )
        )


        secondary_frame = (
            secondary_properties.get(
                "frameNumber",
                ""
            )
        )


        secondary_beam = (
            secondary_properties.get(
                "beamModeType",
                ""
            )
        )


        secondary_platform = (
            secondary_properties.get(
                "platform",
                ""
            )
        )


        secondary_polarization = (
            secondary_properties.get(
                "polarization",
                ""
            )
        )


        # ASF baseline value
        asf_temporal_baseline = (
            secondary_properties.get(
                "temporalBaseline"
            )
        )


        perpendicular_baseline = (
            secondary_properties.get(
                "perpendicularBaseline"
            )
        )


        secondary_date = (
            secondary_properties.get(
                "startTime",
                ""
            )
        )


        # ====================================================
        # SKIP INVALID DATA
        # ====================================================

        if (
            not secondary_scene
            or not secondary_date
        ):
            continue


        if perpendicular_baseline is None:
            continue


        # ====================================================
        # SAME PLATFORM
        # ====================================================

        if secondary_platform != platform:
            continue


        # ====================================================
        # SAME ORBIT DIRECTION
        # ====================================================

        if secondary_direction != orbit_direction:
            continue


        # ====================================================
        # SAME RELATIVE ORBIT
        # ====================================================

        if secondary_path != relative_orbit:
            continue


        # ====================================================
        # SAME FRAME
        # ====================================================

        if secondary_frame != frame:
            continue


        # ====================================================
        # SAME BEAM MODE
        # ====================================================

        if secondary_beam != beam_mode:
            continue


        # ====================================================
        # SAME POLARIZATION
        # ====================================================

        if secondary_polarization != polarization:
            continue


        # ====================================================
        # CALCULATE TRUE TEMPORAL BASELINE
        # ====================================================

        try:

            secondary_datetime = pd.to_datetime(
                secondary_date,
                utc=True
            )

            temporal_baseline_days = (
                secondary_datetime
                - reference_datetime
            ).total_seconds() / 86400.0

        except Exception:

            continue


        # ====================================================
        # TEMPORAL BASELINE FILTER
        # ====================================================

        if (
            abs(temporal_baseline_days)
            > MAX_TEMPORAL_DAYS
        ):
            continue


        # ====================================================
        # ADD COMPATIBLE CANDIDATE
        # ====================================================

        compatible.append({

            "reference_scene":
                reference_id,

            "secondary_scene":
                secondary_scene,

            "reference_date":
                reference_date,

            "secondary_date":
                secondary_date,

            "orbit_direction":
                orbit_direction,

            "relative_orbit":
                relative_orbit,

            "frame":
                frame,

            "temporal_baseline_days":
                round(
                    temporal_baseline_days,
                    2
                ),

            "asf_temporal_baseline":
                asf_temporal_baseline,

            "perpendicular_baseline_m":
                round(
                    float(perpendicular_baseline),
                    2
                ),

            "status":
                "BASELINE_CANDIDATE"
        })


    # ========================================================
    # SORT BY ABSOLUTE PERPENDICULAR BASELINE
    # ========================================================

    compatible.sort(
        key=lambda x:
        abs(
            x[
                "perpendicular_baseline_m"
            ]
        )
    )


    print(
        "\nCompatible candidates:",
        len(compatible)
    )


    # ========================================================
    # DISPLAY TOP CANDIDATES
    # ========================================================

    print("\nBest candidates:")


    for candidate in compatible[:5]:

        print(
            "\nSecondary:",
            candidate[
                "secondary_scene"
            ]
        )

        print(
            "Temporal:",
            candidate[
                "temporal_baseline_days"
            ],
            "days"
        )

        print(
            "Perpendicular:",
            candidate[
                "perpendicular_baseline_m"
            ],
            "m"
        )


    # ========================================================
    # ADD TO FINAL LIST
    # ========================================================

    all_rows.extend(
        compatible
    )


# ============================================================
# 7. CREATE DATAFRAME
# ============================================================

output_df = pd.DataFrame(
    all_rows
)


# ============================================================
# 8. SORT RESULTS
# ============================================================

if not output_df.empty:

    output_df[
        "baseline_sort"
    ] = pd.to_numeric(
        output_df[
            "perpendicular_baseline_m"
        ],
        errors="coerce"
    ).abs()


    output_df = output_df.sort_values(

        by=[
            "reference_scene",
            "baseline_sort"
        ],

        na_position="last"
    )


    output_df = output_df.drop(
        columns=[
            "baseline_sort"
        ]
    )


# ============================================================
# 9. SAVE CSV
# ============================================================

output_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# 10. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)

print(
    "          ALL BASELINE SEARCH COMPLETE"
)

print("=" * 70)


print(
    "\nReferences processed:",
    len(reference_scenes)
)


if not output_df.empty:

    candidate_count = len(
        output_df[
            output_df[
                "status"
            ]
            == "BASELINE_CANDIDATE"
        ]
    )

else:

    candidate_count = 0


print(
    "Baseline candidates found:",
    candidate_count
)


print("\nCSV created:")

print(
    OUTPUT_FILE
)


print("\nIMPORTANT:")

print(
    "Temporal baseline is calculated"
)

print(
    "directly from Sentinel-1 acquisition dates."
)

print(
    "ASF temporalBaseline is preserved separately"
)

print(
    "for reference and traceability."
)

print(
    "These are dynamic baseline candidates."
)

print(
    "They are NOT final InSAR pairs yet."
)


print("\nNext step:")

print(
    "We will rank and select the scientifically"
)

print(
    "useful pairs for HyP3 processing."
)


print("\n" + "=" * 70)