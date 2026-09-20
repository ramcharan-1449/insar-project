from pathlib import Path
import json
import math

import geopandas as gpd
from shapely.geometry import box


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

AOI_FILE = PROJECT_ROOT / "config" / "mine_aoi.geojson"

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
)

GRID_CONFIG_FILE = PROJECT_ROOT / "config" / "grid_config.json"


# ============================================================
# SETTINGS
# ============================================================

TARGET_CRS = "EPSG:32645"

with GRID_CONFIG_FILE.open(encoding="utf-8") as stream:
    grid_config = json.load(stream)

GRID_SIZE = float(grid_config["grid_size_m"])
TARGET_CRS = grid_config["crs"]
OUTPUT_FILE = OUTPUT_DIR / grid_config["grid_filename"]


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LOAD AOI
# ============================================================

print("=" * 70)
print(f"STAGE 8 - {GRID_SIZE:g} m MINE GRID CREATION")
print("=" * 70)

print()
print(f"AOI      : {AOI_FILE}")
print(f"CRS      : {TARGET_CRS}")
print(f"Grid size: {GRID_SIZE} m")
print()


aoi = gpd.read_file(AOI_FILE)


if aoi.empty:
    print("ERROR: AOI contains no geometry.")
    raise SystemExit(1)


# ============================================================
# PROJECT AOI
# ============================================================

aoi = aoi.to_crs(TARGET_CRS)

aoi_geometry = aoi.geometry.union_all()


if aoi_geometry.is_empty:
    print("ERROR: AOI geometry is empty.")
    raise SystemExit(1)


if not aoi_geometry.is_valid:
    print("ERROR: AOI geometry is invalid.")
    raise SystemExit(1)


# ============================================================
# AOI BOUNDS
# ============================================================

minx, miny, maxx, maxy = aoi_geometry.bounds

print("Projected AOI bounds:")
print(f"min X : {minx:.3f}")
print(f"min Y : {miny:.3f}")
print(f"max X : {maxx:.3f}")
print(f"max Y : {maxy:.3f}")
print()


# ============================================================
# SNAP GRID TO THE CANONICAL GRID SPACING
# ============================================================

grid_minx = math.floor(minx / GRID_SIZE) * GRID_SIZE
grid_miny = math.floor(miny / GRID_SIZE) * GRID_SIZE

grid_maxx = math.ceil(maxx / GRID_SIZE) * GRID_SIZE
grid_maxy = math.ceil(maxy / GRID_SIZE) * GRID_SIZE


# ============================================================
# CREATE GRID CELLS
# ============================================================

features = []

cell_id = 1

y = grid_miny

while y < grid_maxy:

    x = grid_minx

    while x < grid_maxx:

        cell = box(
            x,
            y,
            x + GRID_SIZE,
            y + GRID_SIZE
        )

        if cell.intersects(aoi_geometry):

            intersection = cell.intersection(
                aoi_geometry
            )

            intersection_area = intersection.area

            cell_area = cell.area

            coverage_percent = (
                intersection_area
                / cell_area
                * 100
            )

            if coverage_percent >= 99.999:

                coverage_class = "FULL"

            elif coverage_percent >= 50:

                coverage_class = "MAJORITY"

            else:

                coverage_class = "BOUNDARY"

            features.append({
                "cell_id": f"G{cell_id:04d}",
                "grid_size_m": GRID_SIZE,
                "coverage_percent": round(
                    coverage_percent,
                    4
                ),
                "coverage_class": coverage_class,
                "geometry": cell
            })

            cell_id += 1

        x += GRID_SIZE

    y += GRID_SIZE


# ============================================================
# CREATE GEODATAFRAME
# ============================================================

grid = gpd.GeoDataFrame(
    features,
    crs=TARGET_CRS
)


# ============================================================
# SAVE GRID
# ============================================================

grid.to_file(
    OUTPUT_FILE,
    driver="GeoJSON"
)


# ============================================================
# SUMMARY
# ============================================================

full = sum(
    grid["coverage_class"] == "FULL"
)

majority = sum(
    grid["coverage_class"] == "MAJORITY"
)

boundary = sum(
    grid["coverage_class"] == "BOUNDARY"
)

print("=" * 70)
print("GRID SUMMARY")
print("=" * 70)

print(f"Total grid cells : {len(grid)}")
print(f"FULL             : {full}")
print(f"MAJORITY         : {majority}")
print(f"BOUNDARY         : {boundary}")

print()
print(f"Grid CRS         : {grid.crs}")
print(f"Grid size        : {GRID_SIZE} m")

print()
print("Output:")
print(OUTPUT_FILE)

print()
print("Stage 8 grid creation complete.")
