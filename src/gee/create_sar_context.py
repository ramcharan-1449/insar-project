import ee
import csv
from pathlib import Path

print("=" * 70)
print("             SENTINEL-1 SAR CONTEXT")
print("=" * 70)

# ---------------------------------------------------------
# 1. Initialize GEE
# ---------------------------------------------------------

print("\nInitializing Google Earth Engine...")

try:
    ee.Initialize()
    print("GEE initialization: SUCCESS ✅")
except Exception as error:
    print("GEE initialization FAILED ❌")
    print(error)
    raise


# ---------------------------------------------------------
# 2. Define Shyamsundarpur AOI
# ---------------------------------------------------------

print("\nLoading Shyamsundarpur AOI...")

aoi = ee.Geometry.Polygon([
    [
        [87.2500, 23.6400],
        [87.2600, 23.6380],
        [87.2680, 23.6430],
        [87.2660, 23.6520],
        [87.2570, 23.6540],
        [87.2490, 23.6490],
        [87.2500, 23.6400]
    ]
])

print("AOI loaded: SUCCESS ✅")


# ---------------------------------------------------------
# 3. Load Sentinel-1 GRD
# ---------------------------------------------------------

print("\nLoading Sentinel-1 GRD...")

collection = (
    ee.ImageCollection("COPERNICUS/S1_GRD")
    .filterBounds(aoi)
    .filterDate("2024-01-01", "2025-12-31")
    .filter(
        ee.Filter.listContains(
            "transmitterReceiverPolarisation",
            "VV"
        )
    )
    .filter(
        ee.Filter.eq(
            "instrumentMode",
            "IW"
        )
    )
)

count = collection.size().getInfo()

print("Available VV scenes:", count)


# ---------------------------------------------------------
# 4. Calculate statistics
# ---------------------------------------------------------

print("\nCalculating SAR statistics...")


def calculate_stats(image):

    stats = image.select("VV").reduceRegion(
        reducer=ee.Reducer.mean().combine(
            reducer2=ee.Reducer.minMax(),
            sharedInputs=True
        ),
        geometry=aoi,
        scale=10,
        bestEffort=True,
        maxPixels=1e8
    )

    return ee.Feature(
        None,
        {
            "scene_id": image.get("system:index"),

            "date": ee.Date(
                image.get("system:time_start")
            ).format("YYYY-MM-dd"),

            "orbit_direction": image.get(
                "orbitProperties_pass"
            ),

            "relative_orbit": image.get(
                "relativeOrbitNumber_start"
            ),

            "mean_vv": stats.get("VV_mean"),

            "min_vv": stats.get("VV_min"),

            "max_vv": stats.get("VV_max")
        }
    )


stats_collection = collection.map(calculate_stats)


# ---------------------------------------------------------
# 5. Retrieve results
# ---------------------------------------------------------

print("Retrieving statistics...")

features = stats_collection.getInfo()["features"]

print("Statistics retrieved:", len(features))


# ---------------------------------------------------------
# 6. Create output folder
# ---------------------------------------------------------

output_dir = Path("data/processed/gee")

output_dir.mkdir(
    parents=True,
    exist_ok=True
)

output_file = output_dir / "sentinel1_sar_context.csv"


# ---------------------------------------------------------
# 7. Save CSV
# ---------------------------------------------------------

print("\nSaving CSV...")

with open(
    output_file,
    "w",
    newline="",
    encoding="utf-8"
) as csv_file:

    writer = csv.writer(csv_file)

    writer.writerow([
        "scene_id",
        "date",
        "orbit_direction",
        "relative_orbit",
        "mean_vv",
        "min_vv",
        "max_vv"
    ])

    for feature in features:

        properties = feature["properties"]

        writer.writerow([
            properties.get("scene_id"),
            properties.get("date"),
            properties.get("orbit_direction"),
            properties.get("relative_orbit"),
            properties.get("mean_vv"),
            properties.get("min_vv"),
            properties.get("max_vv")
        ])


# ---------------------------------------------------------
# 8. Display first 5 records
# ---------------------------------------------------------

print("\nFirst 5 records:")

for feature in features[:5]:

    print(feature["properties"])


# ---------------------------------------------------------
# 9. Final result
# ---------------------------------------------------------

print("\nOutput file:")
print(output_file)

print("\n" + "=" * 70)
print("          SAR CONTEXT PROCESSING COMPLETE")
print("=" * 70)