import geopandas as gpd
from shapely.geometry import box
from pathlib import Path
import json


print("=" * 70)
print("              INSAR SPATIAL GRID GENERATION")
print("=" * 70)


# ---------------------------------------------------------
# 1. Input and output paths
# ---------------------------------------------------------

aoi_file = Path("config/mine_aoi_projected.geojson")

output_dir = Path("data/processed/grid")
output_dir.mkdir(parents=True, exist_ok=True)

with Path("config/grid_config.json").open(encoding="utf-8") as stream:
    grid_config = json.load(stream)

output_file = output_dir / grid_config["grid_filename"]


# ---------------------------------------------------------
# 2. Grid size
# ---------------------------------------------------------

GRID_SIZE = grid_config["grid_size_m"]  # metres; canonical project contract

print("\nGrid cell size:", GRID_SIZE, "m ×", GRID_SIZE, "m")


# ---------------------------------------------------------
# 3. Load projected AOI
# ---------------------------------------------------------

print("\nLoading projected AOI...")

aoi = gpd.read_file(aoi_file)

print("AOI loaded successfully ✅")
print("CRS:", aoi.crs)


# ---------------------------------------------------------
# 4. Validate CRS
# ---------------------------------------------------------

if aoi.crs is None:
    raise ValueError("AOI does not have a CRS.")

if aoi.crs.to_epsg() != 32645:
    raise ValueError(
        f"Expected EPSG:32645, but found {aoi.crs}"
    )

print("CRS validation: SUCCESS ✅")


# ---------------------------------------------------------
# 5. Combine AOI geometry
# ---------------------------------------------------------

aoi_geometry = aoi.geometry.union_all()

min_x, min_y, max_x, max_y = aoi_geometry.bounds

print("\nAOI bounds:")
print("Minimum X:", min_x)
print("Minimum Y:", min_y)
print("Maximum X:", max_x)
print("Maximum Y:", max_y)


# ---------------------------------------------------------
# 6. Generate grid
# ---------------------------------------------------------

print("\nGenerating grid cells...")

grid_cells = []

cell_id = 1

x = min_x

while x < max_x:

    y = min_y

    while y < max_y:

        cell = box(
            x,
            y,
            x + GRID_SIZE,
            y + GRID_SIZE
        )

        # Keep cells that intersect the AOI
        if cell.intersects(aoi_geometry):

            grid_cells.append({
                "cell_id": f"CELL_{cell_id:04d}",
                "geometry": cell
            })

            cell_id += 1

        y += GRID_SIZE

    x += GRID_SIZE


# ---------------------------------------------------------
# 7. Convert to GeoDataFrame
# ---------------------------------------------------------

grid = gpd.GeoDataFrame(
    grid_cells,
    geometry="geometry",
    crs=aoi.crs
)


# ---------------------------------------------------------
# 8. Add grid attributes
# ---------------------------------------------------------

grid["grid_size_m"] = GRID_SIZE

grid["area_m2"] = grid.geometry.area

grid["area_km2"] = grid["area_m2"] / 1_000_000


# ---------------------------------------------------------
# 9. Calculate whether cell is fully/partially inside AOI
# ---------------------------------------------------------

grid["inside_aoi"] = grid.geometry.within(aoi_geometry)

grid["intersects_aoi"] = grid.geometry.intersects(aoi_geometry)


# ---------------------------------------------------------
# 10. Save grid
# ---------------------------------------------------------

grid.to_file(
    output_file,
    driver="GeoJSON"
)


# ---------------------------------------------------------
# 11. Print summary
# ---------------------------------------------------------

print("\nGrid generation complete ✅")

print("\nNumber of grid cells:", len(grid))

print(
    "Total grid area:",
    round(grid["area_km2"].sum(), 4),
    "km²"
)

print(
    "Cells fully inside AOI:",
    int(grid["inside_aoi"].sum())
)

print(
    "Cells intersecting AOI:",
    int(grid["intersects_aoi"].sum())
)

print("\nOutput:")
print(output_file)

print("\n" + "=" * 70)
print("              GRID GENERATION COMPLETE")
print("=" * 70)
