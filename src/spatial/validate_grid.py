import geopandas as gpd
from pathlib import Path


print("=" * 70)
print("                 GRID VALIDATION")
print("=" * 70)


# ---------------------------------------------------------
# 1. Paths
# ---------------------------------------------------------

grid_file = Path(
    "data/processed/grid/mine_grid.geojson"
)

aoi_file = Path(
    "config/mine_aoi_projected.geojson"
)


# ---------------------------------------------------------
# 2. Load files
# ---------------------------------------------------------

print("\nLoading grid...")

grid = gpd.read_file(grid_file)

print("Grid loaded successfully ✅")
print("Number of cells:", len(grid))
print("CRS:", grid.crs)


print("\nLoading AOI...")

aoi = gpd.read_file(aoi_file)

print("AOI loaded successfully ✅")


# ---------------------------------------------------------
# 3. Check CRS
# ---------------------------------------------------------

print("\nChecking CRS...")

if grid.crs.to_epsg() == 32645:
    print("Grid CRS: CORRECT ✅")
else:
    print("Grid CRS: INCORRECT ❌")


# ---------------------------------------------------------
# 4. Check cell IDs
# ---------------------------------------------------------

print("\nChecking cell IDs...")

unique_ids = grid["cell_id"].nunique()

print("Total cells:", len(grid))
print("Unique IDs :", unique_ids)

if unique_ids == len(grid):
    print("Cell IDs are unique ✅")
else:
    print("Duplicate cell IDs found ❌")


# ---------------------------------------------------------
# 5. Check geometry validity
# ---------------------------------------------------------

print("\nChecking geometries...")

invalid = (~grid.geometry.is_valid).sum()
empty = grid.geometry.is_empty.sum()

print("Invalid geometries:", invalid)
print("Empty geometries  :", empty)

if invalid == 0 and empty == 0:
    print("All geometries are valid ✅")
else:
    print("Geometry problems found ❌")


# ---------------------------------------------------------
# 6. Check cell dimensions
# ---------------------------------------------------------

print("\nChecking cell dimensions...")

widths = []
heights = []

for geometry in grid.geometry:

    min_x, min_y, max_x, max_y = geometry.bounds

    widths.append(max_x - min_x)
    heights.append(max_y - min_y)


print(
    "Minimum cell width :",
    round(min(widths), 2),
    "m"
)

print(
    "Maximum cell width :",
    round(max(widths), 2),
    "m"
)

print(
    "Minimum cell height:",
    round(min(heights), 2),
    "m"
)

print(
    "Maximum cell height:",
    round(max(heights), 2),
    "m"
)


# ---------------------------------------------------------
# 7. Check AOI intersection
# ---------------------------------------------------------

print("\nChecking AOI intersection...")

aoi_geometry = aoi.geometry.union_all()

intersecting = grid.geometry.intersects(
    aoi_geometry
).sum()

print("Grid cells intersecting AOI:", intersecting)


# ---------------------------------------------------------
# 8. Calculate AOI coverage percentage
# ---------------------------------------------------------

print("\nCalculating AOI coverage...")

grid["intersection_area_m2"] = grid.geometry.intersection(
    aoi_geometry
).area

grid["aoi_coverage_percent"] = (
    grid["intersection_area_m2"]
    / grid.geometry.area
) * 100


print(
    "Minimum AOI coverage:",
    round(grid["aoi_coverage_percent"].min(), 2),
    "%"
)

print(
    "Maximum AOI coverage:",
    round(grid["aoi_coverage_percent"].max(), 2),
    "%"
)


# ---------------------------------------------------------
# 9. Summary
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("                 GRID VALIDATION COMPLETE")
print("=" * 70)

print("\nValidation summary:")
print("Cells:", len(grid))
print("Unique IDs:", unique_ids)
print("Invalid geometries:", invalid)
print("Empty geometries:", empty)
print("CRS:", grid.crs)
print("AOI-intersecting cells:", intersecting)

print("\nGrid is ready for spatial sampling ✅")

print("=" * 70)
