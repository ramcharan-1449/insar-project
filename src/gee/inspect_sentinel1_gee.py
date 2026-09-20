import ee

print("=" * 70)
print("        SENTINEL-1 GEE DATASET INSPECTION")
print("=" * 70)

# ---------------------------------------------------------
# 1. Initialize Earth Engine
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
# 2. Load project AOI
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
# 3. Load Sentinel-1 GRD collection
# ---------------------------------------------------------

print("\nLoading Sentinel-1 GRD collection...")

collection = (
    ee.ImageCollection("COPERNICUS/S1_GRD")
    .filterBounds(aoi)
    .filterDate("2024-01-01", "2025-12-31")
)

count = collection.size().getInfo()

print("Sentinel-1 GRD scenes found:", count)


# ---------------------------------------------------------
# 4. Check polarization
# ---------------------------------------------------------

print("\nChecking VV-polarized scenes...")

vv_collection = collection.filter(
    ee.Filter.listContains(
        "transmitterReceiverPolarisation",
        "VV"
    )
)

vv_count = vv_collection.size().getInfo()

print("VV scenes found:", vv_count)


# ---------------------------------------------------------
# 5. Check ascending / descending coverage
# ---------------------------------------------------------

print("\nChecking orbit directions...")

ascending = vv_collection.filter(
    ee.Filter.eq("orbitProperties_pass", "ASCENDING")
)

descending = vv_collection.filter(
    ee.Filter.eq("orbitProperties_pass", "DESCENDING")
)

ascending_count = ascending.size().getInfo()
descending_count = descending.size().getInfo()

print("Ascending scenes :", ascending_count)
print("Descending scenes:", descending_count)


# ---------------------------------------------------------
# 6. Display first scene information
# ---------------------------------------------------------

print("\nInspecting first Sentinel-1 scene...")

if vv_count > 0:

    first = ee.Image(vv_collection.first())

    properties = first.toDictionary([
        "system:index",
        "system:time_start",
        "orbitProperties_pass",
        "relativeOrbitNumber_start",
        "instrumentMode",
        "resolution_meters"
    ]).getInfo()

    print("\nFirst scene information:")

    for key, value in properties.items():

        print(f"{key}: {value}")

else:

    print("No Sentinel-1 VV scenes found.")


# ---------------------------------------------------------
# 7. Final message
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("             GEE INSPECTION COMPLETE")
print("=" * 70)
