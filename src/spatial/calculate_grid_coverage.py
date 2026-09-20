import geopandas as gpd
from pathlib import Path


print("=" * 70)
print("              GRID AOI COVERAGE ANALYSIS")
print("=" * 70)


# ---------------------------------------------------------
# 1. File paths
# ---------------------------------------------------------

grid_file = Path(
    "data/processed/grid/mine_grid.geojson"
)

aoi_file = Path(
    "config/mine_aoi_projected.geojson"
)

output_file = Path(
    "data/processed/grid/mine_grid_coverage.geojson"
)


# ---------------------------------------------------------
# 2. Load files
# ---------------------------------------------------------

print("\nLoading grid...")

grid = gpd.read_file(grid_file)

print("Grid loaded:", len(grid), "cells")


print("\nLoading AOI...")

aoi = gpd.read_file(aoi_file)

print("AOI loaded successfully ✅")


# ---------------------------------------------------------
# 3. Check CRS
# ---------------------------------------------------------

if grid.crs.to_epsg() != 32645:
    raise ValueError(
        f"Grid CRS must be EPSG:32645. Found: {grid.crs}"
    )

if aoi.crs.to_epsg() != 32645:
    raise ValueError(
        f"AOI CRS must be EPSG:32645. Found: {aoi.crs}"
    )

print("\nCRS check: SUCCESS ✅")


# ---------------------------------------------------------
# 4. Combine AOI geometry
# ---------------------------------------------------------

aoi_geometry = aoi.geometry.union_all()


# ---------------------------------------------------------
# 5. Calculate coverage
# ---------------------------------------------------------

print("\nCalculating AOI coverage for every cell...")

grid["grid_area_m2"] = grid.geometry.area

grid["intersection_area_m2"] = (
    grid.geometry
    .intersection(aoi_geometry)
    .area
)

grid["aoi_coverage_percent"] = (
    grid["intersection_area_m2"]
    / grid["grid_area_m2"]
) * 100


# ---------------------------------------------------------
# 6. Classify cells
# ---------------------------------------------------------

def classify_coverage(value):

    if value >= 100:
        return "FULL"

    elif value >= 50:
        return "MAJORITY"

    elif value > 0:
        return "BOUNDARY"

    else:
        return "OUTSIDE"


grid["coverage_class"] = (
    grid["aoi_coverage_percent"]
    .apply(classify_coverage)
)


# ---------------------------------------------------------
# 7. Save
# ---------------------------------------------------------

print("\nSaving coverage information...")

grid.to_file(
    output_file,
    driver="GeoJSON"
)


# ---------------------------------------------------------
# 8. Summary
# ---------------------------------------------------------

print("\nCoverage summary:")

print(
    "FULL cells:",
    (grid["coverage_class"] == "FULL").sum()
)

print(
    "MAJORITY cells:",
    (grid["coverage_class"] == "MAJORITY").sum()
)

print(
    "BOUNDARY cells:",
    (grid["coverage_class"] == "BOUNDARY").sum()
)

print(
    "OUTSIDE cells:",
    (grid["coverage_class"] == "OUTSIDE").sum()
)


print("\nCoverage range:")

print(
    "Minimum:",
    round(grid["aoi_coverage_percent"].min(), 2),
    "%"
)

print(
    "Maximum:",
    round(grid["aoi_coverage_percent"].max(), 2),
    "%"
)


# ---------------------------------------------------------
# 9. Output
# ---------------------------------------------------------

print("\nOutput file:")
print(output_file)

print("\n" + "=" * 70)
print("           GRID COVERAGE ANALYSIS COMPLETE")
print("=" * 70)
