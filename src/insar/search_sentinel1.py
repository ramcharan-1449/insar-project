import asf_search as asf
import geopandas as gpd
import csv
from pathlib import Path


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

AOI_FILE = PROJECT_ROOT / "config" / "mine_aoi.geojson"
CSV_FILE = PROJECT_ROOT / "config" / "sentinel1_scene_inventory.csv"


# ============================================================
# SEARCH SETTINGS
# ============================================================

START_DATE = "2024-01-01"
END_DATE = "2025-12-31"


# ============================================================
# LOAD AOI
# ============================================================

print("=" * 70)
print("       SENTINEL-1 AUTOMATIC ASF SEARCH")
print("=" * 70)

print("\nLoading AOI:")
print(AOI_FILE)

aoi = gpd.read_file(AOI_FILE)

print("\nAOI CRS:")
print(aoi.crs)

# Convert AOI to WGS84
aoi = aoi.to_crs("EPSG:4326")

# Combine all AOI geometries
geometry = aoi.geometry.union_all()

# Convert geometry to WKT
wkt = geometry.wkt

print("\nAOI loaded successfully.")
print("Geometry type:", geometry.geom_type)


# ============================================================
# ASF SEARCH
# ============================================================

print("\nSearching ASF...")
print("Dataset       : Sentinel-1")
print("Product       : SLC")
print("Start date    :", START_DATE)
print("End date      :", END_DATE)

results = asf.search(
    platform=asf.PLATFORM.SENTINEL1,
    intersectsWith=wkt,
    start=START_DATE,
    end=END_DATE,
    processingLevel=asf.PRODUCT_TYPE.SLC,
)

print("\nSearch completed.")

print("Number of scenes found:", len(results))


# ============================================================
# WRITE RESULTS TO CSV
# ============================================================

rows = []

for scene in results:

    properties = scene.properties

    scene_id = properties.get("sceneName", "")
    acquisition_date = properties.get("startTime", "")
    orbit_direction = properties.get("flightDirection", "")
    relative_orbit = properties.get("pathNumber", "")
    polarization = properties.get("polarization", "")
    product_type = properties.get("processingLevel", "")

    rows.append({
        "scene_id": scene_id,
        "acquisition_date": acquisition_date,
        "orbit_direction": orbit_direction,
        "relative_orbit": relative_orbit,
        "polarization": polarization,
        "product_type": product_type,
        "aoi_coverage": "YES",
        "selected": "NO",
        "status": "AVAILABLE",
        "notes": ""
    })


# ============================================================
# SAVE CSV
# ============================================================

fieldnames = [
    "scene_id",
    "acquisition_date",
    "orbit_direction",
    "relative_orbit",
    "polarization",
    "product_type",
    "aoi_coverage",
    "selected",
    "status",
    "notes"
]

with open(CSV_FILE, "w", newline="", encoding="utf-8") as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(rows)


# ============================================================
# SUMMARY
# ============================================================

print("\nCSV created successfully:")
print(CSV_FILE)

print("\nScenes written:", len(rows))

print("\nIMPORTANT:")
print("These scenes have NOT been selected for InSAR processing yet.")
print("They are only the ASF search results.")

print("\nNext step:")
print("We will analyze orbit direction, relative orbit, dates,")
print("and select compatible scenes for InSAR.")

print("\n" + "=" * 70)
print("                    SEARCH COMPLETE")
print("=" * 70)