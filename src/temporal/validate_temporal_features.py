from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# STAGE 13 - TEMPORAL CONSISTENCY & SCIENTIFIC QC
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_grid_features.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "config"
    / "insar_temporal_qc.csv"
)


print("=" * 70)
print("STAGE 13 - TEMPORAL CONSISTENCY & SCIENTIFIC QC")
print("=" * 70)


# ============================================================
# 1. LOAD DATA
# ============================================================

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Input file not found:\n{INPUT_FILE}"
    )

df = pd.read_csv(INPUT_FILE)

print(f"\nInput records : {len(df)}")
print(f"Input columns : {len(df.columns)}")


# ============================================================
# 2. REQUIRED COLUMNS
# ============================================================

required_columns = [
    "cell_id",
    "product_id",
    "reference_date",
    "secondary_date",
    "temporal_baseline_days",
    "orbit_direction",
    "relative_orbit",
    "los_displacement_mean",
    "los_displacement_median",
    "los_displacement_std",
    "coherence_mean",
    "coherence_median",
    "valid_pixel_fraction",
]

missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )


# ============================================================
# 3. CONVERT DATES
# ============================================================

df["reference_date"] = pd.to_datetime(
    df["reference_date"],
    errors="coerce"
)

df["secondary_date"] = pd.to_datetime(
    df["secondary_date"],
    errors="coerce"
)


# ============================================================
# 4. DATE VALIDATION
# ============================================================

df["date_valid"] = (
    df["reference_date"].notna()
    & df["secondary_date"].notna()
)

df["date_order_valid"] = (
    df["secondary_date"]
    > df["reference_date"]
)


# ============================================================
# 5. TEMPORAL BASELINE VALIDATION
# ============================================================

calculated_baseline = (
    df["secondary_date"]
    - df["reference_date"]
).dt.days

metadata_baseline = pd.to_numeric(
    df["temporal_baseline_days"],
    errors="coerce"
)

df["baseline_valid"] = (
    calculated_baseline == metadata_baseline
)

df["baseline_range_valid"] = (
    (metadata_baseline > 0)
    & (metadata_baseline <= 24)
)


# ============================================================
# 6. ORBIT VALIDATION
# ============================================================

df["orbit_valid"] = (
    df["orbit_direction"]
    .astype(str)
    .str.upper()
    .isin([
        "ASCENDING",
        "DESCENDING"
    ])
)

df["relative_orbit_valid"] = (
    pd.to_numeric(
        df["relative_orbit"],
        errors="coerce"
    ).notna()
)


# ============================================================
# 7. DUPLICATE PRODUCT / GRID CELL
# ============================================================

df["duplicate_product_cell"] = (
    df.duplicated(
        subset=[
            "product_id",
            "cell_id"
        ],
        keep=False
    )
)


# ============================================================
# 8. NUMERIC VALIDITY
# ============================================================

numeric_columns = [
    "los_displacement_mean",
    "los_displacement_median",
    "los_displacement_std",
    "coherence_mean",
    "coherence_median",
    "valid_pixel_fraction",
]

for column in numeric_columns:

    values = pd.to_numeric(
        df[column],
        errors="coerce"
    )

    df[f"{column}_finite"] = np.isfinite(
        values
    )


# ============================================================
# 9. COHERENCE RANGE
# ============================================================

df["coherence_range_valid"] = (
    (df["coherence_mean"] >= 0)
    & (df["coherence_mean"] <= 1)
    & (df["coherence_median"] >= 0)
    & (df["coherence_median"] <= 1)
)


# ============================================================
# 10. VALID PIXEL FRACTION
# ============================================================

df["valid_pixel_fraction_valid"] = (
    (df["valid_pixel_fraction"] >= 0)
    & (df["valid_pixel_fraction"] <= 1)
)


# ============================================================
# 11. DISPLACEMENT SANITY CHECK
# ============================================================

# Review flag only.
#
# Values above 500 mm are not automatically
# considered physically impossible.

df["displacement_sanity_valid"] = (
    df["los_displacement_mean"]
    .abs()
    <= 0.5
)


# ============================================================
# 12. TEMPORAL QUALITY CLASSIFICATION
# ============================================================

def classify_temporal_quality(row):

    coherence = row["coherence_mean"]

    if not np.isfinite(coherence):
        return "UNAVAILABLE"

    if coherence >= 0.7:
        return "HIGH_COHERENCE"

    if coherence >= 0.5:
        return "ACCEPTABLE_COHERENCE"

    return "LOW_COHERENCE"


df["temporal_quality"] = (
    df.apply(
        classify_temporal_quality,
        axis=1
    )
)


# ============================================================
# 13. OBSERVATION QC STATUS
# ============================================================

def determine_qc_status(row):

    if not row["date_valid"]:
        return "INVALID"

    if not row["date_order_valid"]:
        return "INVALID"

    if not row["baseline_valid"]:
        return "INVALID"

    if not row["baseline_range_valid"]:
        return "INVALID"

    if not row["orbit_valid"]:
        return "INVALID"

    if not row["relative_orbit_valid"]:
        return "INVALID"

    if row["duplicate_product_cell"]:
        return "INVALID"

    if not row["coherence_range_valid"]:
        return "INVALID"

    if not row["valid_pixel_fraction_valid"]:
        return "INVALID"

    if not row["los_displacement_mean_finite"]:
        return "INVALID"

    if not row["los_displacement_median_finite"]:
        return "INVALID"

    if not row["los_displacement_std_finite"]:
        return "INVALID"

    if not row["coherence_mean_finite"]:
        return "INVALID"

    if not row["coherence_median_finite"]:
        return "INVALID"

    if not row["valid_pixel_fraction_finite"]:
        return "INVALID"

    if not row["displacement_sanity_valid"]:
        return "REVIEW"

    return "VALID"


df["qc_status"] = (
    df.apply(
        determine_qc_status,
        axis=1
    )
)


# ============================================================
# 14. OVERALL TEMPORAL QC
# ============================================================

df["temporal_qc_pass"] = (
    df["qc_status"] == "VALID"
)


# ============================================================
# 15. QC REASON
# ============================================================

def qc_reason(row):

    failures = []

    if not row["date_valid"]:
        failures.append("INVALID_DATE")

    if not row["date_order_valid"]:
        failures.append("INVALID_DATE_ORDER")

    if not row["baseline_valid"]:
        failures.append("BASELINE_MISMATCH")

    if not row["baseline_range_valid"]:
        failures.append("BASELINE_OUT_OF_RANGE")

    if not row["orbit_valid"]:
        failures.append("INVALID_ORBIT")

    if not row["relative_orbit_valid"]:
        failures.append("INVALID_RELATIVE_ORBIT")

    if row["duplicate_product_cell"]:
        failures.append("DUPLICATE_PRODUCT_CELL")

    if not row["coherence_range_valid"]:
        failures.append("INVALID_COHERENCE")

    if not row["valid_pixel_fraction_valid"]:
        failures.append(
            "INVALID_VALID_PIXEL_FRACTION"
        )

    if not row["los_displacement_mean_finite"]:
        failures.append(
            "INVALID_LOS_MEAN"
        )

    if not row["los_displacement_median_finite"]:
        failures.append(
            "INVALID_LOS_MEDIAN"
        )

    if not row["los_displacement_std_finite"]:
        failures.append(
            "INVALID_LOS_STD"
        )

    if not row["coherence_mean_finite"]:
        failures.append(
            "INVALID_COHERENCE_MEAN"
        )

    if not row["coherence_median_finite"]:
        failures.append(
            "INVALID_COHERENCE_MEDIAN"
        )

    if not row["valid_pixel_fraction_finite"]:
        failures.append(
            "INVALID_VALID_PIXEL_FRACTION_VALUE"
        )

    if not row["displacement_sanity_valid"]:
        failures.append(
            "DISPLACEMENT_REVIEW"
        )

    if not failures:
        return "PASS"

    return ";".join(failures)


df["temporal_qc_reason"] = (
    df.apply(
        qc_reason,
        axis=1
    )
)


# ============================================================
# 16. PRODUCT-LEVEL SUMMARY
# ============================================================

product_summary = (
    df.groupby("product_id")
    .agg(
        reference_date=(
            "reference_date",
            "first"
        ),

        secondary_date=(
            "secondary_date",
            "first"
        ),

        temporal_baseline_days=(
            "temporal_baseline_days",
            "first"
        ),

        orbit_direction=(
            "orbit_direction",
            "first"
        ),

        relative_orbit=(
            "relative_orbit",
            "first"
        ),

        grid_cells=(
            "cell_id",
            "nunique"
        ),

        qc_pass=(
            "temporal_qc_pass",
            "sum"
        ),

        qc_review=(
            "qc_status",
            lambda x: (x == "REVIEW").sum()
        ),

        qc_fail=(
            "qc_status",
            lambda x: (x == "INVALID").sum()
        ),
    )
    .reset_index()
)


# ============================================================
# 17. SAVE DETAILED QC
# ============================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# 18. SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("STAGE 13 QC SUMMARY")
print("=" * 70)

print(
    f"Input records        : {len(df)}"
)

print(
    f"Products             : "
    f"{df['product_id'].nunique()}"
)

print(
    f"Grid cells           : "
    f"{df['cell_id'].nunique()}"
)

print(
    f"Duplicate records    : "
    f"{df['duplicate_product_cell'].sum()}"
)

print(
    f"Date failures        : "
    f"{(~df['date_valid']).sum()}"
)

print(
    f"Date-order failures  : "
    f"{(~df['date_order_valid']).sum()}"
)

print(
    f"Baseline failures    : "
    f"{(~df['baseline_valid']).sum()}"
)

print(
    f"Baseline range fail  : "
    f"{(~df['baseline_range_valid']).sum()}"
)

print(
    f"Orbit failures       : "
    f"{(~df['orbit_valid']).sum()}"
)

print(
    f"Relative orbit fail  : "
    f"{(~df['relative_orbit_valid']).sum()}"
)

print(
    f"Coherence failures   : "
    f"{(~df['coherence_range_valid']).sum()}"
)

print(
    f"Pixel fraction fail  : "
    f"{(~df['valid_pixel_fraction_valid']).sum()}"
)

print(
    f"Displacement review  : "
    f"{(~df['displacement_sanity_valid']).sum()}"
)


print("\nQC STATUS:")

print(
    df["qc_status"]
    .value_counts()
    .to_string()
)


print("\nTEMPORAL QUALITY:")

print(
    df["temporal_quality"]
    .value_counts()
    .to_string()
)


print("\nProduct-level summary:")

print(
    product_summary.to_string(
        index=False
    )
)


print("\nOutput:")
print(OUTPUT_FILE)

print(
    "\nStage 13 temporal consistency "
    "and scientific QC complete."
)
