from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SPATIAL_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_grid_features.csv"
)

QC_FILE = (
    PROJECT_ROOT
    / "config"
    / "insar_temporal_qc.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_temporal_observations.csv"
)


# ============================================================
# SETTINGS
# ============================================================

# No product IDs are hard-coded.
# Products and observations are discovered from the input files.

MIN_VALID_TEMPORAL_DAYS = 1


# ============================================================
# START
# ============================================================

print("=" * 70)
print("STAGE 14 - AUTOMATED TEMPORAL OBSERVATION DATASET")
print("=" * 70)


# ============================================================
# CHECK INPUT FILES
# ============================================================

if not SPATIAL_FILE.exists():
    print(f"ERROR: Spatial input does not exist:")
    print(SPATIAL_FILE)
    raise SystemExit(1)


if not QC_FILE.exists():
    print(f"ERROR: Temporal QC input does not exist:")
    print(QC_FILE)
    raise SystemExit(1)


# ============================================================
# LOAD SPATIAL DATA
# ============================================================

print("\nLoading spatial features...")

spatial = pd.read_csv(
    SPATIAL_FILE
)

print(
    f"Spatial records : {len(spatial)}"
)

print(
    f"Spatial columns : {len(spatial.columns)}"
)


# ============================================================
# LOAD TEMPORAL QC
# ============================================================

print("\nLoading temporal QC...")

qc = pd.read_csv(
    QC_FILE
)

print(
    f"QC records      : {len(qc)}"
)

print(
    f"QC columns      : {len(qc.columns)}"
)


# ============================================================
# AUTOMATIC PRODUCT DISCOVERY
# ============================================================

spatial_products = sorted(
    spatial["product_id"]
    .dropna()
    .astype(str)
    .unique()
)

qc_products = sorted(
    qc["product_id"]
    .dropna()
    .astype(str)
    .unique()
)


print("\nAutomatic product discovery:")

print(
    f"Spatial products : {len(spatial_products)}"
)

print(
    f"QC products      : {len(qc_products)}"
)


# ============================================================
# REQUIRED SPATIAL COLUMNS
# ============================================================

required_spatial = [
    "cell_id",
    "product_id",

    "reference_date",
    "secondary_date",

    "temporal_baseline_days",

    "orbit_direction",
    "relative_orbit",
    "reference_frame",
    "secondary_frame",

    "los_displacement_mean",
    "los_displacement_median",
    "los_displacement_std",

    "coherence_mean",
    "coherence_median",

    "valid_pixel_fraction",
]


# ============================================================
# REQUIRED QC COLUMNS
# ============================================================

required_qc = [
    "cell_id",
    "product_id",

    "temporal_qc_pass",
    "qc_status",
    "temporal_quality",
    "temporal_qc_reason",
]


# ============================================================
# COLUMN VALIDATION
# ============================================================

missing_spatial = [
    column
    for column in required_spatial
    if column not in spatial.columns
]


missing_qc = [
    column
    for column in required_qc
    if column not in qc.columns
]


if missing_spatial:

    print("\nERROR: Missing spatial columns:")

    for column in missing_spatial:
        print(f"  {column}")

    raise SystemExit(1)


if missing_qc:

    print("\nERROR: Missing temporal QC columns:")

    for column in missing_qc:
        print(f"  {column}")

    raise SystemExit(1)


print("\nRequired-column check: PASS")


# ============================================================
# QC DUPLICATE CHECK
# ============================================================

qc_duplicates = qc.duplicated(
    subset=[
        "cell_id",
        "product_id"
    ]
).sum()


if qc_duplicates != 0:

    print()
    print(
        f"ERROR: Temporal QC contains "
        f"{qc_duplicates} duplicate cell-product records."
    )

    raise SystemExit(1)


print(
    "Temporal QC duplicate check: PASS"
)


# ============================================================
# SELECT QC INFORMATION
# ============================================================

qc_info = qc[
    [
        "cell_id",
        "product_id",
        "temporal_qc_pass",
        "qc_status",
        "temporal_quality",
        "temporal_qc_reason",
    ]
].copy()


# ============================================================
# NORMALIZE JOIN KEYS
# ============================================================

spatial["cell_id"] = (
    spatial["cell_id"]
    .astype(str)
)

spatial["product_id"] = (
    spatial["product_id"]
    .astype(str)
)


qc_info["cell_id"] = (
    qc_info["cell_id"]
    .astype(str)
)

qc_info["product_id"] = (
    qc_info["product_id"]
    .astype(str)
)


# ============================================================
# MERGE QC
# ============================================================

print("\nMerging temporal QC information...")

data = spatial.merge(
    qc_info,
    on=[
        "cell_id",
        "product_id"
    ],
    how="left",
    validate="one_to_one",
)


# ============================================================
# MERGE SAFETY CHECK
# ============================================================

if len(data) != len(spatial):

    print(
        "ERROR: Record count changed "
        "during QC merge."
    )

    raise SystemExit(1)


print(
    "QC merge check: PASS"
)


# ============================================================
# CHECK QC COMPLETENESS
# ============================================================

missing_qc_rows = (
    data["temporal_qc_pass"]
    .isna()
    .sum()
)


if missing_qc_rows > 0:

    print(
        f"ERROR: {missing_qc_rows} observations "
        f"have no temporal QC result."
    )

    raise SystemExit(1)


print(
    "QC completeness check: PASS"
)


# ============================================================
# NORMALIZE QC BOOLEAN
# ============================================================

def parse_boolean(value):

    if isinstance(value, bool):
        return value

    if pd.isna(value):
        return np.nan

    text = str(value).strip().lower()

    if text in {
        "true",
        "1",
        "yes",
        "pass",
        "passed"
    }:
        return True

    if text in {
        "false",
        "0",
        "no",
        "fail",
        "failed"
    }:
        return False

    return np.nan


data["temporal_qc_pass"] = (
    data["temporal_qc_pass"]
    .apply(parse_boolean)
)


if data["temporal_qc_pass"].isna().any():

    print(
        "ERROR: Invalid temporal_qc_pass values detected."
    )

    raise SystemExit(1)


# ============================================================
# QC FILTERING
# ============================================================

valid = data[
    data["temporal_qc_pass"]
].copy()


excluded_count = (
    len(data)
    - len(valid)
)


print("\nQC filtering:")

print(
    f"Total observations : {len(data)}"
)

print(
    f"Valid observations : {len(valid)}"
)

print(
    f"Excluded           : {excluded_count}"
)


# ============================================================
# DATE PROCESSING
# ============================================================

valid["reference_date"] = pd.to_datetime(
    valid["reference_date"],
    errors="coerce"
)

valid["secondary_date"] = pd.to_datetime(
    valid["secondary_date"],
    errors="coerce"
)


if valid["reference_date"].isna().any():

    raise ValueError(
        "Invalid reference dates detected."
    )


if valid["secondary_date"].isna().any():

    raise ValueError(
        "Invalid secondary dates detected."
    )


# ============================================================
# DATE ORDER CHECK
# ============================================================

invalid_date_order = (
    valid["secondary_date"]
    <= valid["reference_date"]
)


if invalid_date_order.any():

    count = invalid_date_order.sum()

    raise ValueError(
        f"{count} observations have "
        f"invalid date ordering."
    )


# ============================================================
# TEMPORAL INFORMATION
# ============================================================

valid["mid_date"] = (
    valid["reference_date"]
    + (
        valid["secondary_date"]
        - valid["reference_date"]
    ) / 2
)


valid["temporal_baseline_days"] = (
    valid["secondary_date"]
    - valid["reference_date"]
).dt.days


valid["temporal_baseline_years"] = (
    valid["temporal_baseline_days"]
    / 365.25
)


# ============================================================
# TEMPORAL BASELINE CHECK
# ============================================================

invalid_baseline = (
    valid["temporal_baseline_days"]
    < MIN_VALID_TEMPORAL_DAYS
)


if invalid_baseline.any():

    count = invalid_baseline.sum()

    raise ValueError(
        f"{count} observations have "
        f"invalid temporal baselines."
    )


# ============================================================
# DISPLACEMENT CONVERSION
# ============================================================

valid["los_displacement_mean_mm"] = (
    valid["los_displacement_mean"]
    * 1000.0
)


valid["los_displacement_median_mm"] = (
    valid["los_displacement_median"]
    * 1000.0
)


valid["los_displacement_std_mm"] = (
    valid["los_displacement_std"]
    * 1000.0
)


# ============================================================
# PAIRWISE DISPLACEMENT RATE
# ============================================================
#
# This is a pairwise rate.
# It is NOT a long-term deformation velocity
# derived from a common-reference time series.
# ============================================================

valid["los_pairwise_rate_mm_per_year"] = np.where(
    valid["temporal_baseline_years"] > 0,

    (
        valid["los_displacement_mean_mm"]
        / valid["temporal_baseline_years"]
    ),

    np.nan,
)


# ============================================================
# COHERENCE QUALITY
# ============================================================

def coherence_quality(value):

    if pd.isna(value):
        return "UNAVAILABLE"

    if value >= 0.70:
        return "HIGH"

    if value >= 0.50:
        return "ACCEPTABLE"

    return "LOW"


valid["coherence_quality"] = (
    valid["coherence_mean"]
    .apply(coherence_quality)
)


# ============================================================
# SORT
# ============================================================

valid = valid.sort_values(
    [
        "cell_id",
        "reference_date",
        "secondary_date",
        "product_id",
    ]
).reset_index(drop=True)


# ============================================================
# OUTPUT COLUMNS
# ============================================================

output_columns = [
    "cell_id",
    "product_id",

    "zip_file",

    "reference_date",
    "secondary_date",
    "mid_date",

    "temporal_baseline_days",
    "temporal_baseline_years",

    "orbit_direction",
    "relative_orbit",
    "reference_frame",
    "secondary_frame",

    "los_displacement_mean_mm",
    "los_displacement_median_mm",
    "los_displacement_std_mm",

    "los_pairwise_rate_mm_per_year",

    "coherence_mean",
    "coherence_median",
    "coherence_quality",

    "valid_pixel_fraction",

    "temporal_quality",
    "qc_status",
    "temporal_qc_pass",
    "temporal_qc_reason",
]


# Keep columns that actually exist.
output_columns = [
    column
    for column in output_columns
    if column in valid.columns
]


result = valid[
    output_columns
].copy()


# ============================================================
# FINAL DUPLICATE CHECK
# ============================================================

result_duplicates = result.duplicated(
    subset=[
        "cell_id",
        "product_id"
    ]
).sum()


if result_duplicates != 0:

    raise ValueError(
        "Duplicate cell-product observations "
        "remain in final temporal dataset."
    )


# ============================================================
# SAVE
# ============================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)


result.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 70)
print("STAGE 14 AUTOMATED SUMMARY")
print("=" * 70)

print(
    f"Input observations       : {len(spatial)}"
)

print(
    f"QC-valid observations    : {len(result)}"
)

print(
    f"Excluded observations    : {excluded_count}"
)

print(
    f"Products represented    : "
    f"{result['product_id'].nunique()}"
)

print(
    f"Grid cells represented  : "
    f"{result['cell_id'].nunique()}"
)

print(
    f"Date pairs represented  : "
    f"{result[['reference_date', 'secondary_date']]}"
    ".drop_duplicates().shape[0]}"
)


# ============================================================
# AUTOMATIC EXCLUSION SUMMARY
# ============================================================

print()
print("Products excluded by temporal QC:")

excluded = data[
    ~data["temporal_qc_pass"]
].groupby(
    "product_id"
).size()


if excluded.empty:

    print("  None")

else:

    print(
        excluded.to_string()
    )


# ============================================================
# COHERENCE SUMMARY
# ============================================================

print()
print("Coherence quality:")

if len(result) > 0:

    print(
        result["coherence_quality"]
        .value_counts()
        .to_string()
    )

else:

    print("No QC-valid observations.")


# ============================================================
# OUTPUT
# ============================================================

print()
print("Output:")
print(OUTPUT_FILE)


# ============================================================
# FINAL STATUS
# ============================================================

if len(result) == 0:

    print()
    print(
        "ERROR: No QC-valid observations "
        "remain after temporal filtering."
    )

    raise SystemExit(1)


print()
print(
    "STAGE 14 AUTOMATED STATUS: PASS"
)

print()
print(
    "Stage 14 automated temporal observation "
    "dataset completed."
)

