import asf_search
import json
import csv
from pathlib import Path
from datetime import datetime, timezone
from shapely.geometry import shape


# ============================================================
# CONFIGURATION
# ============================================================

BASE = Path(__file__).resolve().parents[2]

AOI_FILE = BASE / "config" / "mine_aoi.geojson"
CONFIG_FILE = BASE / "config" / "sentinel1_config.json"

OUTPUT_FILE = BASE / "config" / "sentinel1_scene_inventory_auto.csv"
START_DATE = "2024-01-01"

# Automatically search up to the current UTC date
END_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# ============================================================
# LOAD AOI
# ============================================================

with open(AOI_FILE, "r", encoding="utf-8") as f:
    aoi = json.load(f)

# Get geometry from GeoJSON
geometry = shape(aoi["features"][0]["geometry"])

# ASF asf_search expects WKT for intersectsWith
aoi_wkt = geometry.wkt

print("AOI loaded successfully.")
print(f"AOI geometry type: {geometry.geom_type}")


# ============================================================
# LOAD SENTINEL CONFIG
# ============================================================

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

orbit_directions = config.get(
    "orbit_directions",
    ["ASCENDING", "DESCENDING"]
)


# ============================================================
# SEARCH FUNCTION
# ============================================================

def search_scenes(orbit_direction):

    print()
    print("=" * 60)
    print("Searching Sentinel-1 SLC scenes")
    print(f"Orbit: {orbit_direction}")
    print(f"Dates: {START_DATE} → {END_DATE}")
    print("=" * 60)

    results = asf_search.search(
        platform=asf_search.PLATFORM.SENTINEL1,
        processingLevel=asf_search.PRODUCT_TYPE.SLC,
        start=START_DATE,
        end=END_DATE,
        intersectsWith=aoi_wkt,
        beamMode=asf_search.BEAMMODE.IW,
        flightDirection=orbit_direction
    )

    print(f"Scenes found: {len(results)}")

    return results


# ============================================================
# MAIN
# ============================================================

def main():

    all_scenes = []

    for orbit in orbit_directions:

        try:

            scenes = search_scenes(orbit)

            for scene in scenes:

                props = scene.properties

                all_scenes.append({
                    "scene_id": props.get("sceneName"),
                    "acquisition_date": props.get("startTime"),
                    "orbit_direction": props.get("flightDirection"),
                    "relative_orbit": props.get("pathNumber"),
                    "frame": props.get("frameNumber"),
                    "polarization": props.get("polarization"),
                    "product_type": props.get("processingLevel"),
                    "beam_mode": props.get("beamModeType"),
                    "url": props.get("url")
                })

        except Exception as e:

            print()
            print(f"ERROR while searching {orbit}:")
            print(e)
            print()

    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    unique = {}

    for scene in all_scenes:

        scene_id = scene["scene_id"]

        if scene_id:
            unique[scene_id] = scene

    all_scenes = list(unique.values())


    # ========================================================
    # SORT BY DATE
    # ========================================================

    all_scenes.sort(
        key=lambda x: x["acquisition_date"] or ""
    )


    # ========================================================
    # SAVE CSV
    # ========================================================

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    columns = [
        "scene_id",
        "acquisition_date",
        "orbit_direction",
        "relative_orbit",
        "frame",
        "polarization",
        "product_type",
        "beam_mode",
        "url"
    ]

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=columns
        )

        writer.writeheader()
        writer.writerows(all_scenes)


    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 60)
    print("AUTOMATIC SENTINEL-1 SEARCH COMPLETE")
    print("=" * 60)

    print(f"Total unique scenes: {len(all_scenes)}")
    print(f"Output: {OUTPUT_FILE}")

    print()

    for orbit in orbit_directions:

        count = sum(
            1
            for scene in all_scenes
            if scene["orbit_direction"] == orbit
        )

        print(f"{orbit}: {count}")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()