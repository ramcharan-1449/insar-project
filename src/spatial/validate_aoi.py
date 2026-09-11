import json
from pathlib import Path

import geopandas as gpd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

AOI_FILE = PROJECT_ROOT / "config" / "mine_aoi.geojson"

CONFIG_FILE = PROJECT_ROOT / "config" / "aoi_config.json"


def validate_aoi():

    print("=" * 60)
    print("        SHYAMSUNDARPUR AOI VALIDATION")
    print("=" * 60)

    # Check AOI file
    if not AOI_FILE.exists():

        print("\nERROR:")
        print("mine_aoi.geojson was not found.")

        print(AOI_FILE)

        return

    # Read AOI
    aoi = gpd.read_file(AOI_FILE)

    print("\nAOI loaded successfully.")

    print("\nNumber of features:")
    print(len(aoi))

    print("\nCRS:")
    print(aoi.crs)

    print("\nGeometry types:")
    print(aoi.geometry.geom_type.value_counts())

    print("\nGeometry validity:")
    print(aoi.geometry.is_valid.tolist())

    # Bounding box
    minx, miny, maxx, maxy = aoi.total_bounds

    print("\nBounding Box")
    print("-" * 40)

    print("Minimum Longitude:", minx)
    print("Minimum Latitude :", miny)
    print("Maximum Longitude:", maxx)
    print("Maximum Latitude :", maxy)

    # Read configuration
    with open(CONFIG_FILE, "r") as file:
        config = json.load(file)

    # Update calculated bounding box
    config["calculated_aoi_bounds"] = {
        "min_longitude": float(minx),
        "min_latitude": float(miny),
        "max_longitude": float(maxx),
        "max_latitude": float(maxy)
    }

    # Important:
    # Do NOT mark as FROZEN because this is assumed data.
    config["aoi_status"] = "ASSUMED_FOR_DEVELOPMENT"

    config["replacement_required"] = True

    # Save configuration
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file, indent=4)

    print("\nAOI configuration updated.")

    print("\nIMPORTANT:")
    print("AOI is ASSUMED.")
    print("AOI is NOT FROZEN.")
    print("Replace it with the verified mine boundary later.")

    print("\n" + "=" * 60)
    print("             AOI VALIDATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    validate_aoi()