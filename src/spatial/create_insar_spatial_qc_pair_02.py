import geopandas as gpd
import pandas as pd
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

GRID_FILE = Path(
    "data/processed/grid/mine_grid_coverage.geojson"
)

FEATURE_FILE = Path(
    "data/processed/grid/"
    "spatial_features_test_pair_02.csv"
)

OUTPUT_FILE = Path(
    "data/processed/grid/"
    "insar_spatial_qc_test_pair_02.geojson"
)


# ============================================================
# LOAD DATA
# ============================================================

grid = gpd.read_file(GRID_FILE)

features = pd.read_csv(
    FEATURE_FILE
)


# ============================================================
# MERGE
# ============================================================

qc = grid.merge(
    features,
    on="cell_id",
    how="left",
    validate="one_to_one"
)


# ============================================================
# VALIDATION
# ============================================================

print("=" * 70)
print("             PAIR 02 INSAR SPATIAL QC")
print("=" * 70)

print("\nGrid cells:", len(grid))
print("Feature rows:", len(features))
print("Merged rows:", len(qc))

print("\nQuality summary:")

print(
    qc["quality_flag"].value_counts(
        dropna=False
    )
)


# ============================================================
# SAVE
# ============================================================

qc.to_file(
    OUTPUT_FILE,
    driver="GeoJSON"
)


print("\nOutput:")
print(OUTPUT_FILE)

print("\nCRS:")
print(qc.crs)

print("\n" + "=" * 70)
print("PAIR 02 SPATIAL QC CREATED")
print("=" * 70)
