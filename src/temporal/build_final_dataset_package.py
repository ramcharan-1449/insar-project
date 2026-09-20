
from pathlib import Path
import json
import shutil
from datetime import datetime, timezone

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ============================================================
# INPUTS
# ============================================================

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

QC_FILE = (
    PROJECT_ROOT
    / "config"
    / "insar_temporal_qc.csv"
)

AOI_FILE = (
    PROJECT_ROOT
    / "config"
    / "aoi_config.json"
)


# ============================================================
# OUTPUT
# ============================================================

FINAL_DIR = (
    PROJECT_ROOT
    / "data"
    / "final_dataset"
)

FINAL_DIR.mkdir(
    parents=True,
    exist_ok=True
)

FINAL_OBS = FINAL_DIR / "insar_observations.csv"
FINAL_TEMPORAL = FINAL_DIR / "insar_temporal_features.csv"
FINAL_SPATIAL = FINAL_DIR / "insar_spatial_features.csv"
FINAL_GRID = FINAL_DIR / "grid.geojson"
FINAL_METADATA = FINAL_DIR / "dataset_metadata.json"
FINAL_README = FINAL_DIR / "README.md"


print("=" * 70)
print("STAGE 17 - FINAL DATASET PACKAGING")
print("=" * 70)


# ============================================================
# LOAD DATA
# ============================================================

print("\nLoading validated datasets...")

observations = pd.read_csv(OBS_FILE)
temporal = pd.read_csv(TEMPORAL_FILE)
spatial = pd.read_csv(SPATIAL_FILE)
qc = pd.read_csv(QC_FILE)


print(f"Observations       : {len(observations)}")
print(f"Temporal features  : {len(temporal)}")
print(f"Spatial features   : {len(spatial)}")
print(f"QC records         : {len(qc)}")


# ============================================================
# DISCOVER CURRENT DATASET STRUCTURE
# ============================================================

grid_cells = sorted(
    observations["cell_id"]
    .dropna()
    .unique()
    .tolist()
)

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

qc_products = sorted(
    qc["product_id"]
    .dropna()
    .unique()
    .tolist()
)


grid_cell_count = len(grid_cells)
valid_product_count = len(valid_products)
all_product_count = len(all_products)
qc_product_count = len(qc_products)

expected_observation_count = (
    grid_cell_count * valid_product_count
)

expected_spatial_count = (
    grid_cell_count * all_product_count
)

expected_qc_count = (
    grid_cell_count * qc_product_count
)


# Products present in processing but absent from valid observations
excluded_products = sorted(
    set(all_products) - set(valid_products)
)


print("\nCurrent dataset structure:")
print(f"Grid cells             : {grid_cell_count}")
print(f"Total products         : {all_product_count}")
print(f"QC products            : {qc_product_count}")
print(f"Valid products         : {valid_product_count}")
print(f"Excluded products      : {len(excluded_products)}")

print(
    f"Expected observations  : {expected_observation_count}"
)

print(
    f"Expected spatial rows  : {expected_spatial_count}"
)

print(
    f"Expected QC rows       : {expected_qc_count}"
)


# ============================================================
# BASIC PACKAGING SAFETY CHECKS
# ============================================================

print("\nRunning packaging safety checks...")


# ------------------------------------------------------------
# Grid consistency
# ------------------------------------------------------------

assert grid_cell_count > 0, (
    "No grid cells found in observations."
)

assert temporal["cell_id"].nunique() == grid_cell_count, (
    "Temporal feature grid-cell count does not match observations."
)

assert spatial["cell_id"].nunique() == grid_cell_count, (
    "Spatial feature grid-cell count does not match observations."
)

assert qc["cell_id"].nunique() == grid_cell_count, (
    "QC grid-cell count does not match observations."
)


# ------------------------------------------------------------
# Product consistency
# ------------------------------------------------------------

assert (
    set(valid_products).issubset(
        set(all_products)
    )
), (
    "Some valid observation products are missing "
    "from the spatial dataset."
)


assert (
    set(valid_products).issubset(
        set(qc_products)
    )
), (
    "Some valid observation products are missing "
    "from the QC dataset."
)


# ------------------------------------------------------------
# Observation count
# ------------------------------------------------------------

assert len(observations) == expected_observation_count, (
    f"Expected {expected_observation_count} observations, "
    f"found {len(observations)}"
)


# ------------------------------------------------------------
# Spatial count
# ------------------------------------------------------------

assert len(spatial) == expected_spatial_count, (
    f"Expected {expected_spatial_count} spatial records, "
    f"found {len(spatial)}"
)


# ------------------------------------------------------------
# QC count
# ------------------------------------------------------------

assert len(qc) == expected_qc_count, (
    f"Expected {expected_qc_count} QC records, "
    f"found {len(qc)}"
)


# ------------------------------------------------------------
# Duplicate checks
# ------------------------------------------------------------

assert (
    observations.duplicated(
        ["cell_id", "product_id"]
    ).sum()
    == 0
), (
    "Duplicate cell/product records found "
    "in observations."
)


assert (
    spatial.duplicated(
        ["cell_id", "product_id"]
    ).sum()
    == 0
), (
    "Duplicate cell/product records found "
    "in spatial features."
)


assert (
    qc.duplicated(
        ["cell_id", "product_id"]
    ).sum()
    == 0
), (
    "Duplicate cell/product records found "
    "in QC records."
)


# ------------------------------------------------------------
# One observation per valid product per cell
# ------------------------------------------------------------

observations_per_cell = (
    observations
    .groupby("cell_id")
    .size()
)

assert (
    len(observations_per_cell) == grid_cell_count
), (
    "Not every grid cell is represented "
    "in observations."
)

assert (
    observations_per_cell.min()
    == valid_product_count
), (
    "Some grid cells have fewer observations "
    "than the current valid product count."
)

assert (
    observations_per_cell.max()
    == valid_product_count
), (
    "Some grid cells have more observations "
    "than the current valid product count."
)


# ------------------------------------------------------------
# Temporal summary consistency
# ------------------------------------------------------------

assert (
    temporal["valid_observation_count"]
    .min()
    == valid_product_count
), (
    "Temporal summary minimum observation count "
    "does not match valid product count."
)

assert (
    temporal["valid_observation_count"]
    .max()
    == valid_product_count
), (
    "Temporal summary maximum observation count "
    "does not match valid product count."
)


# ------------------------------------------------------------
# QC-valid product consistency
# ------------------------------------------------------------

if "temporal_qc_pass" in qc.columns:

    qc_valid_products = set(
        qc.loc[
            qc["temporal_qc_pass"] == True,
            "product_id"
        ]
        .dropna()
        .unique()
    )

    assert (
        set(valid_products) == qc_valid_products
    ), (
        "Valid observation products do not exactly "
        "match QC-pass products."
    )


print("All packaging safety checks passed.")


# ============================================================
# COPY FINAL DATASETS
# ============================================================

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


# ============================================================
# COPY GRID
# ============================================================

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


# ============================================================
# READ AOI INFORMATION
# ============================================================

aoi_info = {}


if AOI_FILE.exists():

    try:

        with open(
            AOI_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            aoi_info = json.load(f)

    except Exception as exc:

        print(
            f"WARNING: Could not read AOI configuration: {exc}"
        )


# ============================================================
# QC / EXCLUSION INFORMATION
# ============================================================

excluded_product_details = []


for product_id in excluded_products:

    product_qc = qc[
        qc["product_id"] == product_id
    ]

    details = {
        "product_id": product_id,
        "qc_records": len(product_qc)
    }

    if "temporal_qc_pass" in product_qc.columns:

        details["qc_pass_records"] = int(
            (
                product_qc["temporal_qc_pass"]
                == True
            ).sum()
        )

        details["qc_fail_records"] = int(
            (
                product_qc["temporal_qc_pass"]
                == False
            ).sum()
        )

    if "qc_status" in product_qc.columns:

        details["qc_statuses"] = sorted(
            product_qc["qc_status"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

    excluded_product_details.append(
        details
    )


# ============================================================
# DATASET METADATA
# ============================================================

metadata = {

    "dataset_name":
        "Automated InSAR Mine Monitoring Dataset",

    "site":
        "Shyamsundarpur Colliery",

    "region":
        "Raniganj Coalfield, Paschim Bardhaman, West Bengal, India",

    "created_utc":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "grid": {

        "cell_count":
            grid_cell_count,

        "grid_size_m":
            100,

        "crs":
            "EPSG:32645"

    },

    "products": {

        "total_products_processed":
            all_product_count,

        "qc_products":
            qc_product_count,

        "valid_products":
            valid_product_count,

        "excluded_products":
            excluded_products,

        "excluded_product_count":
            len(excluded_products),

        "excluded_product_details":
            excluded_product_details

    },

    "observations": {

        "valid_observation_count":
            len(observations),

        "grid_cells":
            grid_cell_count,

        "observations_per_cell":
            valid_product_count,

        "expected_observation_count":
            expected_observation_count

    },

    "source_datasets": {

        "spatial_features":
            str(SPATIAL_FILE),

        "temporal_qc":
            str(QC_FILE),

        "temporal_observations":
            str(OBS_FILE),

        "temporal_features":
            str(TEMPORAL_FILE),

        "grid":
            str(GRID_FILE)

    },

    "quality_control": {

        "stage_16_integrity_status":
            "PASS",

        "duplicate_cell_product_records":
            int(
                observations.duplicated(
                    ["cell_id", "product_id"]
                ).sum()
            ),

        "excluded_products":
            excluded_products

    },

    "notes": [

        "Temporal observations contain QC-valid InSAR observations only.",

        "Excluded products are determined dynamically from the difference between processed products and valid observation products.",

        "Pairwise LOS displacement rate is not a long-term velocity estimate.",

        "Low coherence observations are retained only when they pass the defined QC rules.",

        "The current AOI should be replaced with an authoritative mine polygon before final scientific publication."

    ],

    "aoi_configuration":
        aoi_info
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


print(
    f"Created: {FINAL_METADATA}"
)


# ============================================================
# README
# ============================================================

excluded_readme = (
    "\n".join(
        f"- {product}"
        for product in excluded_products
    )
    if excluded_products
    else "- None"
)


readme = f"""# Automated InSAR Mine Monitoring Dataset

## Study Area

Shyamsundarpur Colliery  
Raniganj Coalfield  
Paschim Bardhaman, West Bengal, India

## Dataset Status

Stage 16 final integrity QC: **PASS**

## Grid

- Grid cells: {grid_cell_count}
- Grid size: 100 m
- CRS: EPSG:32645

## InSAR Products

- Total processed products: {all_product_count}
- QC products: {qc_product_count}
- Valid products: {valid_product_count}
- Excluded products: {len(excluded_products)}

Excluded products:

{excluded_readme}

## Valid Observations

- Grid cells: {grid_cell_count}
- Valid products: {valid_product_count}
- Total observations: {len(observations)}
- Observations per cell: {valid_product_count}

Therefore:

{grid_cell_count} cells × {valid_product_count} valid products = {expected_observation_count} observations

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
- Dynamic observation count
- Dynamic product validation
- QC consistency
- Date consistency
- Orbit metadata completeness
- Temporal-summary consistency

Excluded products are determined automatically from the current QC-valid product set.

## Important Scientific Notes

Missing InSAR displacement values were not replaced with zero.

Pairwise displacement rates should not be interpreted as long-term ground velocity unless derived from an appropriate multi-date temporal model.

## Automation

This package represents the current validated output of the automated InSAR processing pipeline.

Future Sentinel-1 acquisitions can be processed incrementally by the pipeline without changing the scientific packaging logic.

Product counts, observation counts and excluded products are calculated dynamically from the current datasets.

## Scientific Finalization

The current development AOI is provisional. An authoritative mine boundary should replace the development AOI before final scientific publication.
"""


FINAL_README.write_text(
    readme,
    encoding="utf-8"
)


print(
    f"Created: {FINAL_README}"
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("STAGE 17 SUMMARY")
print("=" * 70)

print(
    f"Final directory       : {FINAL_DIR}"
)

print(
    f"Valid observations    : {len(observations)}"
)

print(
    f"Grid cells            : {grid_cell_count}"
)

print(
    f"Valid products        : {valid_product_count}"
)

print(
    f"Total products        : {all_product_count}"
)

print(
    f"Excluded products     : {excluded_products}"
)

print(
    f"Observations per cell : {valid_product_count}"
)


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

        print(
            f"  OK  {file.name}"
        )

    else:

        print(
            f"  MISSING  {file.name}"
        )


print("\nSTAGE 17 COMPLETED.")
