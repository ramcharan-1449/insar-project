from pathlib import Path
import json

import geopandas as gpd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

with (PROJECT_ROOT / "config" / "grid_config.json").open(encoding="utf-8") as stream:
    GRID_CONFIG = json.load(stream)

GRID_FILE = PROJECT_ROOT / "data" / "processed" / "grid" / GRID_CONFIG["grid_filename"]


# ============================================================
# SETTINGS
# ============================================================

EXPECTED_CRS = GRID_CONFIG["crs"]
EXPECTED_GRID_SIZE = float(GRID_CONFIG["grid_size_m"])
EXPECTED_CELL_COUNT = int(GRID_CONFIG["expected_cell_count"])


# ============================================================
# LOAD GRID
# ============================================================

print("=" * 70)
print("STAGE 8.5 - MINE GRID VALIDATION")
print("=" * 70)

print()
print(f"Grid file: {GRID_FILE}")
print()


grid = gpd.read_file(GRID_FILE)


if grid.empty:
    print("ERROR: Grid contains no cells.")
    raise SystemExit(1)


# ============================================================
# CRS CHECK
# ============================================================

print(f"CRS: {grid.crs}")

if grid.crs.to_string() != EXPECTED_CRS:

    print(
        f"ERROR: Expected {EXPECTED_CRS}"
    )

    raise SystemExit(1)

print("CRS check: PASS")


# ============================================================
# CELL COUNT
# ============================================================

print()
print(f"Cell count: {len(grid)}")

if len(grid) != EXPECTED_CELL_COUNT:

    print(
        f"ERROR: Expected {EXPECTED_CELL_COUNT} canonical grid cells, "
        f"found {len(grid)}. Verify the authoritative AOI and grid origin; "
        "do not publish this as the production handoff."
    )
    raise SystemExit(1)

print("Cell count check: PASS")


# ============================================================
# GEOMETRY VALIDATION
# ============================================================

invalid_count = (
    ~grid.geometry.is_valid
).sum()

empty_count = (
    grid.geometry.is_empty
).sum()


print()
print(f"Invalid geometries: {invalid_count}")
print(f"Empty geometries  : {empty_count}")


if invalid_count > 0 or empty_count > 0:

    print("Geometry check: FAIL")
    raise SystemExit(1)

print("Geometry check: PASS")


# ============================================================
# GEOMETRY TYPE
# ============================================================

geometry_types = (
    grid.geometry.geom_type.unique()
)

print()
print(
    f"Geometry types: "
    f"{list(geometry_types)}"
)


if not all(
    geometry_type == "Polygon"
    for geometry_type in geometry_types
):

    print("Geometry type check: FAIL")
    raise SystemExit(1)

print("Geometry type check: PASS")


# ============================================================
# CELL AREA CHECK
# ============================================================

areas = grid.geometry.area

expected_area = (
    EXPECTED_GRID_SIZE
    * EXPECTED_GRID_SIZE
)


min_area = areas.min()
max_area = areas.max()


print()
print(
    f"Expected full cell area: "
    f"{expected_area:.2f} m²"
)

print(
    f"Minimum cell area: "
    f"{min_area:.2f} m²"
)

print(
    f"Maximum cell area: "
    f"{max_area:.2f} m²"
)


# ============================================================
# COVERAGE CLASS SUMMARY
# ============================================================

if "coverage_class" in grid.columns:

    print()
    print("Coverage classes:")

    counts = (
        grid["coverage_class"]
        .value_counts()
        .sort_index()
    )

    for name, count in counts.items():

        print(
            f"  {name}: {count}"
        )


# ============================================================
# DUPLICATE CELL IDs
# ============================================================

if "cell_id" not in grid.columns:

    print()
    print("ERROR: cell_id column missing.")
    raise SystemExit(1)


duplicate_ids = (
    grid["cell_id"]
    .duplicated()
    .sum()
)


print()
print(
    f"Duplicate cell IDs: "
    f"{duplicate_ids}"
)


if duplicate_ids > 0:

    print("Cell ID check: FAIL")
    raise SystemExit(1)

print("Cell ID check: PASS")


# ============================================================
# CELL SIZE CHECK
# ============================================================

full_cells = areas[
    areas >= expected_area * 0.999
]

print()
print(
    f"Full {EXPECTED_GRID_SIZE:g}x{EXPECTED_GRID_SIZE:g} m cells: "
    f"{len(full_cells)}"
)

print(
    f"Boundary/non-full cells: "
    f"{len(grid) - len(full_cells)}"
)


# ============================================================
# FINAL RESULT
# ============================================================

print()
print("=" * 70)
print("GRID VALIDATION SUMMARY")
print("=" * 70)

print(f"Total cells       : {len(grid)}")
print(f"CRS               : {grid.crs}")
print(f"Invalid geometries: {invalid_count}")
print(f"Empty geometries  : {empty_count}")
print(f"Duplicate IDs     : {duplicate_ids}")

print()
print("GRID STATUS: PASS")
print()
print("Stage 8.5 grid validation complete.")
