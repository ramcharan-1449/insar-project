import asf_search as asf
import geopandas as gpd
import csv
from pathlib import Path
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parents[2]

AOI_FILE = PROJECT_ROOT / "config" / "mine_aoi.geojson"

OUTPUT_FILE = (
    PROJECT_ROOT
    / "config"
    / "sentinel1_dynamic_baselines.csv"
)

REFERENCE_ID = (
    "S1A_IW_SLC__1SDV_20240510T121316_20240510T121343_053809_068A02_58C3"
)

START_DATE = "2024-01-01"
END_DATE = "2025-12-31"

MAX_TEMPORAL_DAYS = 24


print("=" * 70)
print("       DYNAMIC SENTINEL-1 BASELINE SEARCH")
print("=" * 70)


# ---------------------------------------------------------
# 1. LOAD AOI
# ---------------------------------------------------------

print("\nLoading AOI:")

aoi = gpd.read_file(AOI_FILE).to_crs("EPSG:4326")

geometry = aoi.geometry.union_all()

print("AOI loaded.")
print("Geometry:", geometry.geom_type)


# ---------------------------------------------------------
# 2. SEARCH ASF
# ---------------------------------------------------------

print("\nSearching ASF...")

results = asf.search(
    platform=asf.PLATFORM.SENTINEL1,
    intersectsWith=geometry.wkt,
    start=START_DATE,
    end=END_DATE,
    processingLevel=asf.PRODUCT_TYPE.SLC,
)

print("Total scenes found:", len(results))


# ---------------------------------------------------------
# 3. FIND REFERENCE SCENE
# ---------------------------------------------------------

reference = None

for scene in results:

    scene_id = scene.properties.get("sceneName", "")

    if scene_id == REFERENCE_ID:
        reference = scene
        break


if reference is None:

    print("\nERROR:")
    print("Reference scene was not found.")

    raise SystemExit(1)


print("\nReference scene found:")
print(reference.properties["sceneName"])

print("\nReference metadata:")
print("Date       :", reference.properties["startTime"])
print("Path       :", reference.properties["pathNumber"])
print("Frame      :", reference.properties["frameNumber"])
print("Direction  :", reference.properties["flightDirection"])
print("Polarize   :", reference.properties["polarization"])


# ---------------------------------------------------------
# 4. GET BASELINE STACK
# ---------------------------------------------------------

print("\nRequesting ASF baseline stack...")

stack = reference.stack()

print("Stack scenes:", len(stack))


# ---------------------------------------------------------
# 5. FILTER CANDIDATES
# ---------------------------------------------------------

reference_date = datetime.fromisoformat(
    reference.properties["startTime"].replace("Z", "+00:00")
)

candidates = []


for scene in stack:

    p = scene.properties

    scene_id = p.get("sceneName", "")

    if scene_id == REFERENCE_ID:
        continue

    # Same satellite
    if p.get("platform") != reference.properties.get("platform"):
        continue

    # Same direction
    if p.get("flightDirection") != reference.properties.get(
        "flightDirection"
    ):
        continue

    # Same path
    if p.get("pathNumber") != reference.properties.get(
        "pathNumber"
    ):
        continue

    # Same frame
    if p.get("frameNumber") != reference.properties.get(
        "frameNumber"
    ):
        continue

    # Same beam mode
    if p.get("beamModeType") != reference.properties.get(
        "beamModeType"
    ):
        continue

    # Same polarization
    if p.get("polarization") != reference.properties.get(
        "polarization"
    ):
        continue

    # Temporal baseline
    temporal = p.get("temporalBaseline")

    if temporal is None:
        continue

    temporal_days = abs(float(temporal))

    if temporal_days > MAX_TEMPORAL_DAYS:
        continue

    # Spatial/perpendicular baseline
    perpendicular = p.get("perpendicularBaseline")

    if perpendicular is None:
        continue

    candidates.append(
        {
            "reference_scene": REFERENCE_ID,
            "secondary_scene": scene_id,
            "reference_date": reference.properties.get(
                "startTime"
            ),
            "secondary_date": p.get("startTime"),
            "orbit_direction": p.get(
                "flightDirection"
            ),
            "relative_orbit": p.get(
                "pathNumber"
            ),
            "frame": p.get(
                "frameNumber"
            ),
            "polarization": p.get(
                "polarization"
            ),
            "temporal_baseline_days": temporal,
            "perpendicular_baseline_m": perpendicular,
        }
    )


# ---------------------------------------------------------
# 6. SORT BY SPATIAL BASELINE
# ---------------------------------------------------------

candidates.sort(
    key=lambda x: abs(
        float(x["perpendicular_baseline_m"])
    )
)


# ---------------------------------------------------------
# 7. SAVE CSV
# ---------------------------------------------------------

fieldnames = [
    "reference_scene",
    "secondary_scene",
    "reference_date",
    "secondary_date",
    "orbit_direction",
    "relative_orbit",
    "frame",
    "polarization",
    "temporal_baseline_days",
    "perpendicular_baseline_m",
]


with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8",
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames,
    )

    writer.writeheader()
    writer.writerows(candidates)


# ---------------------------------------------------------
# 8. DISPLAY RESULTS
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("BASELINE SEARCH COMPLETE")
print("=" * 70)

print("\nCompatible candidates:", len(candidates))

print("\nBest candidates:")

for candidate in candidates[:15]:

    print(
        "\nSecondary:",
        candidate["secondary_scene"],
    )

    print(
        "Temporal:",
        candidate["temporal_baseline_days"],
        "days",
    )

    print(
        "Perpendicular:",
        candidate["perpendicular_baseline_m"],
        "m",
    )


print("\nCSV created:")
print(OUTPUT_FILE)

print("\n" + "=" * 70)
