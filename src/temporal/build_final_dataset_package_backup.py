from pathlib import Path
import json
import shutil
from datetime import datetime, timezone

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ------------------------------------------------------------------
# INPUTS
# ------------------------------------------------------------------

OBS_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_temporal_observations.csv"
)

TEMPORAL_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_temporal_features_qc.csv"
)

SPATIAL_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_grid_features.csv"
)

GRID_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "mine_grid_100m.geojson"
)

QC_FILE = PROJECT_ROOT / "config" / "insar_temporal_qc.csv"

AOI_FILE = PROJECT_ROOT / "config" / "aoi_config.json"

# ------------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------------

FINAL_DIR = PROJECT_ROOT / "data" / "final_dataset"

FINAL_DIR.mkdir(parents=True, exist_ok=True)

FINAL_OBS = FINAL_DIR / "insar_observations.csv"
FINAL_TEMPORAL = FINAL_DIR / "insar_temporal_features.csv"
FINAL_SPATIAL = FINAL_DIR / "insar_spatial_features.csv"
FINAL_GRID = FINAL_DIR / "grid.geojson"
FINAL_METADATA = FINAL_DIR / "dataset_metadata.json"
FINAL_README = FINAL_DIR / "README.md"


print("=" * 70)
print("STAGE 17 - FINAL DATASET PACKAGING")
print("=" * 70)


# ------------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------------

print("\nLoading validated datasets...")

observations = pd.read_csv(OBS_FILE)
temporal = pd.read_csv(TEMPORAL_FILE)
spatial = pd.read_csv(SPATIAL_FILE)
qc = pd.read_csv(QC_FILE)

print(f"Observations       : {len(observations)}")
print(f"Temporal features  : {len(temporal)}")
print(f"Spatial features   : {len(spatial)}")
print(f"QC records         : {len(qc)}")


# ------------------------------------------------------------------
# BASIC SAFETY CHECKS
# ------------------------------------------------------------------

print("\nRunning packaging safety checks...")

assert len(observations) == 8790, (
    f"Expected 8790 observations, found {len(observations)}"
)

assert len(temporal) == 293, (
    f"Expected 293 temporal cells, found {len(temporal)}"
)

assert len(spatial) == 9083, (
    f"Expected 9083 spatial records, found {len(spatial)}"
)

assert len(qc) == 9083, (
    f"Expected 9083 QC records, found {len(qc)}"
)

assert observations["cell_id"].nunique() == 293
assert observations["product_id"].nunique() == 30

assert observations.duplicated(
    ["cell_id", "product_id"]
).sum() == 0

assert temporal["cell_id"].nunique() == 293

print("All packaging safety checks passed.")


# ------------------------------------------------------------------
# COPY FINAL DATASETS
# ------------------------------------------------------------------

print("\nCreating final datasets...")

observations.to_csv(
    FINAL_OBS,
    index=False
)

temporal.to_csv(
    FINAL_TEMPORAL,
    index=False
)

spatial.to_csv(
    FINAL_SPATIAL,
    index=False
)

print(f"Created: {FINAL_OBS}")
print(f"Created: {FINAL_TEMPORAL}")
print(f"Created: {FINAL_SPATIAL}")


# ------------------------------------------------------------------
# COPY GRID
# ------------------------------------------------------------------

if GRID_FILE.exists():

    shutil.copy2(
        GRID_FILE,
        FINAL_GRID
    )

    print(f"Created: {FINAL_GRID}")

else:

    print(
        "WARNING: Grid GeoJSON was not found:"
    )
    print(GRID_FILE)


# ------------------------------------------------------------------
# READ AOI INFORMATION
# ------------------------------------------------------------------

aoi_info = {}

if AOI_FILE.exists():

    try:

        with open(AOI_FILE, "r", encoding="utf-8") as f:
            aoi_info = json.load(f)

    except Exception as exc:

        print(
            f"WARNING: Could not read AOI configuration: {exc}"
        )


# ------------------------------------------------------------------
# DATASET METADATA
# ------------------------------------------------------------------

valid_products = sorted(
    observations["product_id"]
    .dropna()
    .unique()
    .tolist()
)

all_products = sorted(
    spatial["product_id"]
    .dropna()
    .unique()
    .tolist()
)

excluded_products = sorted(
    set(all_products) - set(valid_products)
)

metadata = {
    "dataset_name": "Automated InSAR Mine Monitoring Dataset",
    "site": "Shyamsundarpur Colliery",
    "region": "Raniganj Coalfield, Paschim Bardhaman, West Bengal, India",

    "created_utc": datetime.now(
        timezone.utc
    ).isoformat(),

    "grid": {
        "cell_count": 293,
        "grid_size_m": 100,
        "crs": "EPSG:32645"
    },

    "products": {
        "total_products_processed": len(all_products),
        "valid_products": len(valid_products),
        "excluded_products": excluded_products
    },

    "observations": {
        "valid_observation_count": len(observations),
        "grid_cells": observations["cell_id"].nunique(),
        "observations_per_cell": 30
    },

    "source_datasets": {
        "spatial_features": str(SPATIAL_FILE),
        "temporal_qc": str(QC_FILE),
        "temporal_observations": str(OBS_FILE),
        "temporal_features": str(TEMPORAL_FILE),
        "grid": str(GRID_FILE)
    },

    "quality_control": {
        "stage_16_integrity_status": "PASS",
        "p006_excluded": "P006" in excluded_products,
        "duplicate_cell_product_records": int(
            observations.duplicated(
                ["cell_id", "product_id"]
            ).sum()
        )
    },

    "notes": [
        "Temporal observations contain QC-valid InSAR observations only.",
        "P006 is retained in the QC history but excluded from valid temporal observations.",
        "Pairwise LOS displacement rate is not a long-term velocity estimate.",
        "Low coherence observations are retained only when they pass the defined QC rules.",
        "The current AOI should be replaced with an authoritative mine polygon before final scientific publication."
    ],

    "aoi_configuration": aoi_info
}


with open(
    FINAL_METADATA,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        metadata,
        f,
        indent=4,
        default=str
    )

print(f"Created: {FINAL_METADATA}")


# ------------------------------------------------------------------
# README
# ------------------------------------------------------------------

readme = f"""# Automated InSAR Mine Monitoring Dataset

## Study Area

Shyamsundarpur Colliery  
Raniganj Coalfield  
Paschim Bardhaman, West Bengal, India

## Dataset Status

Stage 16 final integrity QC: **PASS**

## Grid

- Grid cells: 293
- Grid size: 100 m
- CRS: EPSG:32645

## InSAR Products

- Total processed products: {len(all_products)}
- Valid products: {len(valid_products)}
- Excluded products: {len(excluded_products)}

Excluded products:

{chr(10).join(f"- {p}" for p in excluded_products) if excluded_products else "- None"}

## Valid Observations

- Grid cells: {observations["cell_id"].nunique()}
- Valid products: {observations["product_id"].nunique()}
- Total observations: {len(observations)}
- Observations per cell: 30

Therefore:

293 cells × 30 valid products = 8,790 observations

## Files

### insar_observations.csv

Observation-level InSAR dataset containing the valid temporal observations for each grid cell and product.

### insar_temporal_features.csv

Cell-level temporal summary containing the engineered temporal features.

### insar_spatial_features.csv

Spatial/product-level InSAR feature dataset.

### grid.geojson

100 m spatial grid used for the analysis.

### dataset_metadata.json

Machine-readable description of the dataset, processing status and QC information.

## Quality Control

The dataset passed the final Stage 16 integrity checks.

Checks included:

- Grid-cell consistency
- Product consistency
- Duplicate detection
- Observation count
- P006 exclusion
- QC consistency
- Date consistency
- Orbit metadata completeness
- Temporal-summary consistency

## Important Scientific Note

P006 was excluded from the valid temporal observations because its LOS displacement fields were unavailable/invalid.

Missing InSAR displacement values were not replaced with zero.

Pairwise displacement rates should not be interpreted as long-term ground velocity unless derived from an appropriate multi-date temporal model.

## Automation

This package represents the current validated output of the automated InSAR processing pipeline.

Future acquisitions can be processed incrementally by the pipeline without rebuilding the scientific workflow from scratch.

## Scientific Finalization

The current development AOI is provisional. An authoritative mine boundary should replace the development AOI before final scientific publication.
"""


FINAL_README.write_text(
    readme,
    encoding="utf-8"
)

print(f"Created: {FINAL_README}")


# ------------------------------------------------------------------
# FINAL SUMMARY
# ------------------------------------------------------------------

print("\n" + "=" * 70)
print("STAGE 17 SUMMARY")
print("=" * 70)

print(f"Final directory       : {FINAL_DIR}")
print(f"Valid observations    : {len(observations)}")
print(f"Grid cells            : {observations['cell_id'].nunique()}")
print(f"Valid products        : {observations['product_id'].nunique()}")
print(f"Excluded products     : {excluded_products}")

print("\nFinal package files:")

for file in [
    FINAL_OBS,
    FINAL_TEMPORAL,
    FINAL_SPATIAL,
    FINAL_GRID,
    FINAL_METADATA,
    FINAL_README
]:

    if file.exists():
        print(f"  OK  {file.name}")
    else:
        print(f"  MISSING  {file.name}")

print("\nSTAGE 17 COMPLETED.")