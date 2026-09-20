from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_temporal_observations.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_temporal_features_qc.csv"
)


# ============================================================
# LOAD
# ============================================================

print("=" * 70)
print("STAGE 15 - QC-AWARE TEMPORAL FEATURE ENGINEERING")
print("=" * 70)

df = pd.read_csv(INPUT_FILE)

print(f"\nInput observations : {len(df)}")
print(f"Input columns      : {len(df.columns)}")


# ============================================================
# REQUIRED COLUMNS
# ============================================================

required = [
    "cell_id",
    "product_id",
    "reference_date",
    "secondary_date",
    "temporal_baseline_days",
    "los_displacement_mean_mm",
    "los_displacement_median_mm",
    "los_displacement_std_mm",
    "los_pairwise_rate_mm_per_year",
    "coherence_mean",
    "coherence_quality",
    "valid_pixel_fraction",
]

missing = [c for c in required if c not in df.columns]

if missing:
    raise ValueError(
        f"Missing required columns: {missing}"
    )


# ============================================================
# DATE PROCESSING
# ============================================================

df["reference_date"] = pd.to_datetime(
    df["reference_date"],
    errors="coerce"
)

df["secondary_date"] = pd.to_datetime(
    df["secondary_date"],
    errors="coerce"
)

df["mid_date"] = pd.to_datetime(
    df["mid_date"],
    errors="coerce"
)


# ============================================================
# SORT
# ============================================================

df = df.sort_values(
    [
        "cell_id",
        "mid_date",
        "product_id",
    ]
).reset_index(drop=True)


# ============================================================
# CELL-LEVEL TEMPORAL SUMMARY
# ============================================================

print("\nBuilding cell-level temporal features...")

grouped = df.groupby(
    "cell_id",
    sort=True
)


features = grouped.agg(
    valid_observation_count=(
        "product_id",
        "count"
    ),

    observation_start_date=(
        "reference_date",
        "min"
    ),

    observation_end_date=(
        "secondary_date",
        "max"
    ),

    mean_los_displacement_mm=(
        "los_displacement_mean_mm",
        "mean"
    ),

    median_los_displacement_mm=(
        "los_displacement_median_mm",
        "median"
    ),

    std_los_displacement_mm=(
        "los_displacement_mean_mm",
        "std"
    ),

    min_los_displacement_mm=(
        "los_displacement_mean_mm",
        "min"
    ),

    max_los_displacement_mm=(
        "los_displacement_mean_mm",
        "max"
    ),

    mean_pairwise_rate_mm_per_year=(
        "los_pairwise_rate_mm_per_year",
        "mean"
    ),

    median_pairwise_rate_mm_per_year=(
        "los_pairwise_rate_mm_per_year",
        "median"
    ),

    std_pairwise_rate_mm_per_year=(
        "los_pairwise_rate_mm_per_year",
        "std"
    ),

    mean_coherence=(
        "coherence_mean",
        "mean"
    ),

    median_coherence=(
        "coherence_mean",
        "median"
    ),

    mean_valid_pixel_fraction=(
        "valid_pixel_fraction",
        "mean"
    ),
).reset_index()


# ============================================================
# TEMPORAL SPAN
# ============================================================

features["observation_span_days"] = (
    features["observation_end_date"]
    - features["observation_start_date"]
).dt.days

features["observation_span_years"] = (
    features["observation_span_days"]
    / 365.25
)


# ============================================================
# COHERENCE COUNTS
# ============================================================

quality_counts = (
    df.pivot_table(
        index="cell_id",
        columns="coherence_quality",
        values="product_id",
        aggfunc="count",
        fill_value=0,
    )
    .reset_index()
)

quality_counts = quality_counts.rename(
    columns={
        "HIGH": "high_coherence_count",
        "ACCEPTABLE": "acceptable_coherence_count",
        "LOW": "low_coherence_count",
        "UNAVAILABLE": "unavailable_coherence_count",
    }
)

for column in [
    "high_coherence_count",
    "acceptable_coherence_count",
    "low_coherence_count",
    "unavailable_coherence_count",
]:
    if column not in quality_counts.columns:
        quality_counts[column] = 0


features = features.merge(
    quality_counts,
    on="cell_id",
    how="left",
    validate="one_to_one",
)


# ============================================================
# PRODUCT COVERAGE
# ============================================================

total_products = df["product_id"].nunique()

features["total_valid_products_available"] = total_products

features["valid_observation_ratio"] = (
    features["valid_observation_count"]
    / total_products
)


# ============================================================
# COHERENCE RATIOS
# ============================================================

features["high_coherence_ratio"] = (
    features["high_coherence_count"]
    / features["valid_observation_count"]
)

features["acceptable_coherence_ratio"] = (
    features["acceptable_coherence_count"]
    / features["valid_observation_count"]
)

features["low_coherence_ratio"] = (
    features["low_coherence_count"]
    / features["valid_observation_count"]
)


# ============================================================
# VALID NUMERIC COUNTS
# ============================================================

features["finite_rate_count"] = (
    grouped["los_pairwise_rate_mm_per_year"]
    .apply(lambda x: np.isfinite(x).sum())
    .values
)


# ============================================================
# FINAL COLUMN ORDER
# ============================================================

output_columns = [
    "cell_id",

    "valid_observation_count",
    "total_valid_products_available",
    "valid_observation_ratio",

    "observation_start_date",
    "observation_end_date",
    "observation_span_days",
    "observation_span_years",

    "mean_los_displacement_mm",
    "median_los_displacement_mm",
    "std_los_displacement_mm",
    "min_los_displacement_mm",
    "max_los_displacement_mm",

    "mean_pairwise_rate_mm_per_year",
    "median_pairwise_rate_mm_per_year",
    "std_pairwise_rate_mm_per_year",

    "mean_coherence",
    "median_coherence",
    "mean_valid_pixel_fraction",

    "high_coherence_count",
    "acceptable_coherence_count",
    "low_coherence_count",
    "unavailable_coherence_count",

    "high_coherence_ratio",
    "acceptable_coherence_ratio",
    "low_coherence_ratio",

    "finite_rate_count",
]


features = features[output_columns]


# ============================================================
# NUMERIC CLEANUP
# ============================================================

numeric_columns = [
    c for c in features.columns
    if c not in [
        "cell_id",
        "observation_start_date",
        "observation_end_date",
    ]
]

features[numeric_columns] = features[numeric_columns].replace(
    [np.inf, -np.inf],
    np.nan
)


# ============================================================
# SAVE
# ============================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

features.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("STAGE 15 SUMMARY")
print("=" * 70)

print(f"Input observations       : {len(df)}")
print(f"Output grid cells        : {len(features)}")
print(f"Products used            : {total_products}")
print(
    f"Mean observations/cell  : "
    f"{features['valid_observation_count'].mean():.2f}"
)

print(
    f"Minimum observations     : "
    f"{features['valid_observation_count'].min()}"
)

print(
    f"Maximum observations     : "
    f"{features['valid_observation_count'].max()}"
)

print(
    f"Mean coherence           : "
    f"{features['mean_coherence'].mean():.4f}"
)

print(
    f"Mean valid pixel fraction: "
    f"{features['mean_valid_pixel_fraction'].mean():.4f}"
)

print("\nOutput:")
print(OUTPUT_FILE)

print("\nStage 15 completed.")