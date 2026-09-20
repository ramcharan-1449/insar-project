from pathlib import Path

import pandas as pd
import numpy as np


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Current automated Stage 6.5 output
INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_grid_features.csv"
)

# Stage 10 QC output
OUTPUT_FILE = (
    PROJECT_ROOT
    / "config"
    / "insar_spatial_qc.csv"
)


# ============================================================
# SETTINGS
# ============================================================

EXPECTED_CELLS = 293

COHERENCE_THRESHOLD = 0.50

# Broad scientific sanity limits.
# These are review limits, NOT deformation thresholds.
MAX_ABSOLUTE_LOS_MM = 500.0
MAX_ABSOLUTE_PHASE = 1000.0


# ============================================================
# START
# ============================================================

print("=" * 70)
print("STAGE 10 - AUTOMATED INSAR SCIENTIFIC QC")
print("=" * 70)

print()
print(f"Input file : {INPUT_FILE}")
print()


# ============================================================
# INPUT CHECK
# ============================================================

if not INPUT_FILE.exists():

    print("ERROR: Input file does not exist.")
    raise SystemExit(1)


# ============================================================
# LOAD
# ============================================================

df = pd.read_csv(INPUT_FILE)

print(f"Rows loaded : {len(df)}")
print(f"Columns     : {len(df.columns)}")
print()


# ============================================================
# REQUIRED COLUMNS
# ============================================================

required_columns = [

    "cell_id",
    "product_id",
    "zip_file",

    "reference_date",
    "secondary_date",
    "temporal_baseline_days",

    "orbit_direction",
    "relative_orbit",
    "reference_frame",
    "secondary_frame",

    "unwrapped_phase_mean",
    "unwrapped_phase_median",
    "unwrapped_phase_std",
    "unwrapped_phase_min",
    "unwrapped_phase_max",
    "unwrapped_phase_valid_pixel_count",

    "amplitude_mean",
    "amplitude_median",
    "amplitude_std",
    "amplitude_min",
    "amplitude_max",
    "amplitude_valid_pixel_count",

    "coherence_mean",
    "coherence_median",
    "coherence_std",
    "coherence_min",
    "coherence_max",
    "coherence_valid_pixel_count",

    "dem_mean",
    "dem_median",
    "dem_std",
    "dem_min",
    "dem_max",
    "dem_valid_pixel_count",

    "vertical_displacement_mean",
    "vertical_displacement_median",
    "vertical_displacement_std",
    "vertical_displacement_min",
    "vertical_displacement_max",
    "vertical_displacement_valid_pixel_count",

    "los_displacement_mean",
    "los_displacement_median",
    "los_displacement_std",
    "los_displacement_min",
    "los_displacement_max",
    "los_displacement_valid_pixel_count",

    "incidence_angle_mean",
    "incidence_angle_median",
    "incidence_angle_std",
    "incidence_angle_min",
    "incidence_angle_max",
    "incidence_angle_valid_pixel_count",

    "valid_pixel_fraction",
]


missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]


if missing_columns:

    print("ERROR: Missing required columns:")

    for column in missing_columns:
        print(f"  {column}")

    raise SystemExit(1)


print("Required-column check: PASS")


# ============================================================
# AUTOMATIC PRODUCT DISCOVERY
# ============================================================

products_found = sorted(
    df["product_id"]
    .dropna()
    .astype(str)
    .unique()
)


if len(products_found) == 0:

    print()
    print("ERROR: No products found.")

    raise SystemExit(1)


print()
print("Products discovered automatically:")
print(products_found)

print()
print(
    f"Product count: {len(products_found)}"
)


# ============================================================
# EXPECTED ROW COUNT
# ============================================================

expected_rows = (
    len(products_found)
    * EXPECTED_CELLS
)


print()
print(f"Expected rows: {expected_rows}")
print(f"Actual rows  : {len(df)}")


if len(df) == expected_rows:

    print("Row-count check: PASS")

else:

    print("Row-count check: REVIEW")

    print(
        f"Difference: "
        f"{len(df) - expected_rows}"
    )


# ============================================================
# DUPLICATE CHECK
# ============================================================

duplicates = df.duplicated(
    subset=[
        "cell_id",
        "product_id"
    ]
).sum()


print()
print(
    f"Duplicate cell-product records: "
    f"{duplicates}"
)


if duplicates == 0:

    print("Duplicate check: PASS")

else:

    print("Duplicate check: FAIL")


# ============================================================
# NUMERIC COLUMNS
# ============================================================

numeric_columns = [

    "temporal_baseline_days",

    "relative_orbit",
    "reference_frame",
    "secondary_frame",

    "unwrapped_phase_mean",
    "unwrapped_phase_median",
    "unwrapped_phase_std",
    "unwrapped_phase_min",
    "unwrapped_phase_max",
    "unwrapped_phase_valid_pixel_count",

    "amplitude_mean",
    "amplitude_median",
    "amplitude_std",
    "amplitude_min",
    "amplitude_max",
    "amplitude_valid_pixel_count",

    "coherence_mean",
    "coherence_median",
    "coherence_std",
    "coherence_min",
    "coherence_max",
    "coherence_valid_pixel_count",

    "dem_mean",
    "dem_median",
    "dem_std",
    "dem_min",
    "dem_max",
    "dem_valid_pixel_count",

    "vertical_displacement_mean",
    "vertical_displacement_median",
    "vertical_displacement_std",
    "vertical_displacement_min",
    "vertical_displacement_max",
    "vertical_displacement_valid_pixel_count",

    "los_displacement_mean",
    "los_displacement_median",
    "los_displacement_std",
    "los_displacement_min",
    "los_displacement_max",
    "los_displacement_valid_pixel_count",

    "incidence_angle_mean",
    "incidence_angle_median",
    "incidence_angle_std",
    "incidence_angle_min",
    "incidence_angle_max",
    "incidence_angle_valid_pixel_count",

    "valid_pixel_fraction",
]


for column in numeric_columns:

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )


# ============================================================
# NUMERIC QUALITY
# ============================================================

print()
print("-" * 70)
print("NUMERIC VALUE QUALITY")
print("-" * 70)


for column in numeric_columns:

    finite_count = np.isfinite(
        df[column]
    ).sum()

    missing_count = (
        len(df)
        - finite_count
    )

    print(
        f"{column:40s} "
        f"finite={finite_count:6d} "
        f"missing={missing_count:6d}"
    )


# ============================================================
# COHERENCE RANGE
# ============================================================

coherence = df[
    "coherence_mean"
].dropna()


coherence_below_zero = (
    coherence < 0
).sum()


coherence_above_one = (
    coherence > 1
).sum()


print()
print("-" * 70)
print("COHERENCE QUALITY")
print("-" * 70)

print(
    f"Coherence < 0 : "
    f"{coherence_below_zero}"
)

print(
    f"Coherence > 1 : "
    f"{coherence_above_one}"
)


if (
    coherence_below_zero == 0
    and coherence_above_one == 0
):

    print("Coherence range check: PASS")

else:

    print("Coherence range check: REVIEW")


high_coherence = (
    coherence >= COHERENCE_THRESHOLD
).sum()


low_coherence = (
    coherence < COHERENCE_THRESHOLD
).sum()


print()
print(
    f"Mean coherence >= "
    f"{COHERENCE_THRESHOLD}: "
    f"{high_coherence}"
)

print(
    f"Mean coherence < "
    f"{COHERENCE_THRESHOLD}: "
    f"{low_coherence}"
)


# ============================================================
# VALID PIXEL FRACTION
# ============================================================

valid_fraction = df[
    "valid_pixel_fraction"
].dropna()


invalid_fraction = (
    (valid_fraction < 0)
    | (valid_fraction > 1)
).sum()


print()
print(
    f"Invalid valid-pixel fractions: "
    f"{invalid_fraction}"
)


if invalid_fraction == 0:

    print(
        "Valid-pixel fraction check: PASS"
    )

else:

    print(
        "Valid-pixel fraction check: REVIEW"
    )


# ============================================================
# TEMPORAL BASELINE
# ============================================================

temporal_days = df[
    "temporal_baseline_days"
].dropna()


invalid_temporal = (
    temporal_days <= 0
).sum()


print()
print(
    f"Temporal baseline <= 0 days: "
    f"{invalid_temporal}"
)


if invalid_temporal == 0:

    print(
        "Temporal baseline check: PASS"
    )

else:

    print(
        "Temporal baseline check: REVIEW"
    )


# ============================================================
# LOS SANITY
# ============================================================

los = df[
    "los_displacement_mean"
].dropna()


los_extreme = (
    los.abs()
    > MAX_ABSOLUTE_LOS_MM
).sum()


print()
print(
    f"LOS values with "
    f"|displacement| > "
    f"{MAX_ABSOLUTE_LOS_MM}: "
    f"{los_extreme}"
)


if los_extreme == 0:

    print(
        "LOS magnitude sanity check: PASS"
    )

else:

    print(
        "LOS magnitude sanity check: REVIEW"
    )


# ============================================================
# PHASE SANITY
# ============================================================

phase = df[
    "unwrapped_phase_mean"
].dropna()


phase_extreme = (
    phase.abs()
    > MAX_ABSOLUTE_PHASE
).sum()


print()
print(
    f"Phase values with "
    f"|phase| > "
    f"{MAX_ABSOLUTE_PHASE}: "
    f"{phase_extreme}"
)


if phase_extreme == 0:

    print(
        "Phase magnitude sanity check: PASS"
    )

else:

    print(
        "Phase magnitude sanity check: REVIEW"
    )


# ============================================================
# PRODUCT SUMMARY
# ============================================================

print()
print("=" * 70)
print("AUTOMATIC PRODUCT SUMMARY")
print("=" * 70)


product_records = []


for product_id in products_found:

    subset = df[
        df["product_id"].astype(str)
        == str(product_id)
    ].copy()


    cells = len(subset)


    mean_coherence = (
        subset["coherence_mean"]
        .mean()
    )


    median_coherence = (
        subset["coherence_mean"]
        .median()
    )


    mean_los = (
        subset["los_displacement_mean"]
        .mean()
    )


    median_los = (
        subset["los_displacement_mean"]
        .median()
    )


    mean_vertical = (
        subset["vertical_displacement_mean"]
        .mean()
    )


    mean_valid_fraction = (
        subset["valid_pixel_fraction"]
        .mean()
    )


    high_coh_cells = (
        subset["coherence_mean"]
        >= COHERENCE_THRESHOLD
    ).sum()


    low_coh_cells = (
        subset["coherence_mean"]
        < COHERENCE_THRESHOLD
    ).sum()


    if cells == EXPECTED_CELLS:

        product_status = "PASS"

    else:

        product_status = "REVIEW"


    product_records.append({

        "product_id": product_id,

        "grid_cells": cells,

        "expected_grid_cells":
            EXPECTED_CELLS,

        "high_coherence_cells":
            int(high_coh_cells),

        "low_coherence_cells":
            int(low_coh_cells),

        "mean_coherence":
            mean_coherence,

        "median_coherence":
            median_coherence,

        "mean_los_displacement":
            mean_los,

        "median_los_displacement":
            median_los,

        "mean_vertical_displacement":
            mean_vertical,

        "mean_valid_pixel_fraction":
            mean_valid_fraction,

        "status":
            product_status
    })


    print(
        f"{product_id}: "
        f"cells={cells}, "
        f"high_coh={high_coh_cells}, "
        f"low_coh={low_coh_cells}, "
        f"mean_coh={mean_coherence:.3f}, "
        f"mean_LOS={mean_los:.3f}, "
        f"mean_vertical={mean_vertical:.3f}, "
        f"status={product_status}"
    )


# ============================================================
# SAVE QC
# ============================================================

qc_df = pd.DataFrame(
    product_records
)


qc_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# OVERALL QC STATUS
# ============================================================

overall_pass = True


if len(df) != expected_rows:
    overall_pass = False


if duplicates != 0:
    overall_pass = False


if (
    coherence_below_zero != 0
    or coherence_above_one != 0
):
    overall_pass = False


if invalid_fraction != 0:
    overall_pass = False


if invalid_temporal != 0:
    overall_pass = False


# ============================================================
# FINAL
# ============================================================

print()
print("=" * 70)
print("STAGE 10 AUTOMATED QC SUMMARY")
print("=" * 70)

print(
    f"Input records       : {len(df)}"
)

print(
    f"Products            : {len(products_found)}"
)

print(
    f"Grid cells/product  : {EXPECTED_CELLS}"
)

print(
    f"Expected observations: {expected_rows}"
)

print(
    f"Actual observations : {len(df)}"
)

print(
    f"Duplicate records   : {duplicates}"
)

print()
print("QC output:")
print(OUTPUT_FILE)

print()


if overall_pass:

    print(
        "OVERALL SCIENTIFIC QC STATUS: PASS"
    )

else:

    print(
        "OVERALL SCIENTIFIC QC STATUS: REVIEW"
    )


print()
print(
    "Stage 10 automated scientific QC complete."
)