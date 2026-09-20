from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# STAGE 12 - TEMPORAL FEATURE ENGINEERING
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_temporal_spatial_features.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_temporal_features.csv"
)


print("=" * 70)
print("STAGE 12 - TEMPORAL FEATURE ENGINEERING")
print("=" * 70)


# ------------------------------------------------------------
# 1. Load data
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

print(f"\nInput records : {len(df)}")
print(f"Products      : {df['product_id'].nunique()}")
print(f"Grid cells    : {df['cell_id'].nunique()}")


# ------------------------------------------------------------
# 2. Required columns
# ------------------------------------------------------------

required_columns = [
    "cell_id",
    "product_id",
    "reference_date",
    "secondary_date",
    "temporal_baseline_days",
    "orbit_direction",
    "relative_orbit",
    "frame",
    "los_displacement_mean_mm",
    "los_displacement_median_mm",
    "los_displacement_std_mm",
    "coherence_mean",
    "coherence_median",
    "unwrapped_phase_mean",
    "unwrapped_phase_median",
    "valid_pixel_count",
    "total_pixel_count",
    "valid_pixel_percent",
    "qc_status",
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )


# ------------------------------------------------------------
# 3. Convert dates
# ------------------------------------------------------------

df["reference_date"] = pd.to_datetime(
    df["reference_date"],
    errors="coerce"
)

df["secondary_date"] = pd.to_datetime(
    df["secondary_date"],
    errors="coerce"
)


# ------------------------------------------------------------
# 4. Validate dates
# ------------------------------------------------------------

invalid_dates = (
    df["reference_date"].isna()
    | df["secondary_date"].isna()
)

print(f"Invalid date records : {invalid_dates.sum()}")

if invalid_dates.any():
    raise ValueError(
        "Invalid reference_date or secondary_date detected."
    )


# ------------------------------------------------------------
# 5. Calculate acquisition midpoint
# ------------------------------------------------------------

df["acquisition_midpoint"] = (
    df["reference_date"]
    + (
        df["secondary_date"]
        - df["reference_date"]
    ) / 2
)


# ------------------------------------------------------------
# 6. Validate temporal baseline
# ------------------------------------------------------------

calculated_baseline = (
    df["secondary_date"]
    - df["reference_date"]
).dt.days

metadata_baseline = pd.to_numeric(
    df["temporal_baseline_days"],
    errors="coerce"
)

baseline_difference = (
    calculated_baseline - metadata_baseline
).abs()

baseline_mismatches = (
    baseline_difference > 1
).sum()

print(f"Baseline mismatches : {baseline_mismatches}")

if baseline_mismatches:
    raise ValueError(
        "Temporal baseline metadata does not match acquisition dates."
    )


# ------------------------------------------------------------
# 7. Pair-normalized displacement
# ------------------------------------------------------------
#
# IMPORTANT:
# This is NOT long-term deformation velocity.
#
# It is simply displacement divided by pair duration.
# Unit = mm/day.
#
# It must NOT be interpreted as a continuous time-series
# velocity.
# ------------------------------------------------------------

df["los_displacement_per_day_mm"] = np.where(
    df["temporal_baseline_days"] > 0,
    df["los_displacement_mean_mm"]
    / df["temporal_baseline_days"],
    np.nan
)


# ------------------------------------------------------------
# 8. Displacement magnitude
# ------------------------------------------------------------

df["los_displacement_abs_mm"] = (
    df["los_displacement_mean_mm"].abs()
)


# ------------------------------------------------------------
# 9. Temporal date features
# ------------------------------------------------------------

df["reference_year"] = (
    df["reference_date"].dt.year
)

df["reference_month"] = (
    df["reference_date"].dt.month
)

df["secondary_year"] = (
    df["secondary_date"].dt.year
)

df["secondary_month"] = (
    df["secondary_date"].dt.month
)

df["midpoint_year"] = (
    df["acquisition_midpoint"].dt.year
)

df["midpoint_month"] = (
    df["acquisition_midpoint"].dt.month
)


# ------------------------------------------------------------
# 10. Temporal pair label
# ------------------------------------------------------------

df["temporal_pair"] = (
    df["reference_date"].dt.strftime("%Y-%m-%d")
    + "_to_"
    + df["secondary_date"].dt.strftime("%Y-%m-%d")
)


# ------------------------------------------------------------
# 11. Temporal quality classification
# ------------------------------------------------------------

def classify_temporal_quality(row):

    if row["qc_status"] == "NO_DATA":
        return "NO_DATA"

    if row["qc_status"] == "LOW_COHERENCE":
        return "LOW_COHERENCE"

    if row["coherence_mean"] >= 0.7:
        return "HIGH_COHERENCE"

    if row["coherence_mean"] >= 0.5:
        return "ACCEPTABLE_COHERENCE"

    return "LOW_COHERENCE"


df["temporal_quality"] = df.apply(
    classify_temporal_quality,
    axis=1
)


# ------------------------------------------------------------
# 12. Sort chronologically
# ------------------------------------------------------------

df = df.sort_values(
    by=[
        "cell_id",
        "acquisition_midpoint",
        "product_id"
    ]
).reset_index(drop=True)


# ------------------------------------------------------------
# 13. Format dates
# ------------------------------------------------------------

df["reference_date"] = (
    df["reference_date"].dt.strftime("%Y-%m-%d")
)

df["secondary_date"] = (
    df["secondary_date"].dt.strftime("%Y-%m-%d")
)

df["acquisition_midpoint"] = (
    df["acquisition_midpoint"].dt.strftime("%Y-%m-%d")
)


# ------------------------------------------------------------
# 14. Save output
# ------------------------------------------------------------

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ------------------------------------------------------------
# 15. Summary
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("STAGE 12 SUMMARY")
print("=" * 70)

print(f"Output records     : {len(df)}")
print(f"Products           : {df['product_id'].nunique()}")
print(f"Grid cells         : {df['cell_id'].nunique()}")

print("\nTemporal products:")

print(
    df[
        [
            "product_id",
            "reference_date",
            "secondary_date",
            "temporal_baseline_days",
            "orbit_direction",
            "relative_orbit",
            "frame"
        ]
    ]
    .drop_duplicates()
    .sort_values("reference_date")
    .to_string(index=False)
)

print("\nTemporal quality:")

print(
    df["temporal_quality"]
    .value_counts()
    .to_string()
)

print("\nOutput:")
print(OUTPUT_FILE)

print("\nStage 12 temporal feature engineering complete.")