import pandas as pd
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

INPUT_FILE = Path(
    "data/processed/grid/"
    "temporal_observations_test_pair_02.csv"
)

OUTPUT_FILE = Path(
    "data/processed/grid/"
    "temporal_features_test_pair_02.csv"
)


# ============================================================
# LOAD
# ============================================================

df = pd.read_csv(INPUT_FILE)


# ============================================================
# SCHEMA CONSISTENCY
# ============================================================
#
# Pair 02 spatial extraction uses:
#     valid_percentage
#
# The combined temporal dataset expects:
#     valid_pixel_percentage
#
# Rename it here so Pair 01 and Pair 02
# have the same temporal schema.
#
# ============================================================

if "valid_percentage" in df.columns:

    df.rename(
        columns={
            "valid_percentage":
            "valid_pixel_percentage"
        },
        inplace=True
    )


print("=" * 70)
print("             PAIR 02 TEMPORAL FEATURES")
print("=" * 70)

print("\nInput rows:", len(df))


# ============================================================
# DATE CONVERSION
# ============================================================

df["reference_date"] = pd.to_datetime(
    df["reference_date"]
)

df["secondary_date"] = pd.to_datetime(
    df["secondary_date"]
)


# ============================================================
# OBSERVATION MID DATE
# ============================================================

df["observation_mid_date"] = (
    df["reference_date"]
    +
    (
        df["secondary_date"]
        -
        df["reference_date"]
    ) / 2
)


# ============================================================
# PAIR DISPLACEMENT
# ============================================================
#
# Use median referenced LOS displacement
# as the cell-level pair displacement.
#
# Units: millimeters
#
# ============================================================

df["pair_displacement_mm"] = (
    df["median_los_mm"]
)


# ============================================================
# TEMPORAL QUALITY
# ============================================================

df["temporal_quality_flag"] = (
    df["quality_flag"]
)


# ============================================================
# OBSERVATION SEQUENCE
# ============================================================
#
# This file contains one interferometric pair,
# therefore sequence = 1.
#
# The combined dataset will assign the final
# chronological sequence per grid cell.
#
# ============================================================

df["observation_sequence"] = 1


# ============================================================
# IMPORTANT SCIENTIFIC RULE
# ============================================================
#
# This is a single interferometric pair.
#
# Therefore:
#
# - Pair displacement is allowed.
# - Velocity is NOT calculated.
# - Long-term trend is NOT calculated.
#
# ============================================================


# ============================================================
# FORMAT DATES
# ============================================================

df["reference_date"] = (
    df["reference_date"]
    .dt.strftime("%Y-%m-%d")
)

df["secondary_date"] = (
    df["secondary_date"]
    .dt.strftime("%Y-%m-%d")
)

df["observation_mid_date"] = (
    pd.to_datetime(
        df["observation_mid_date"]
    )
    .dt.strftime("%Y-%m-%d")
)


# ============================================================
# VALIDATE REQUIRED COLUMNS
# ============================================================

required_columns = [
    "cell_id",
    "pair_id",
    "reference_scene",
    "secondary_scene",
    "reference_date",
    "secondary_date",
    "temporal_baseline_days",
    "observation_type",
    "pair_displacement_mm",
    "temporal_quality_flag",
    "observation_sequence",
    "valid_pixel_percentage"
]

missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing_columns:

    raise ValueError(
        "Missing required columns: "
        f"{missing_columns}"
    )


# ============================================================
# SAVE
# ============================================================

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("\nTemporal features created.")

print(
    "Pair:",
    df["pair_id"].iloc[0]
)

print(
    "Reference date:",
    df["reference_date"].iloc[0]
)

print(
    "Secondary date:",
    df["secondary_date"].iloc[0]
)

print(
    "Temporal baseline:",
    df["temporal_baseline_days"].iloc[0],
    "days"
)

print(
    "Observation type:",
    df["observation_type"].iloc[0]
)


# ============================================================
# PAIR DISPLACEMENT STATISTICS
# ============================================================

print(
    "\nPair displacement statistics:"
)

valid = df[
    df["quality_flag"] == "VALID"
]

if len(valid) > 0:

    print(
        "Min:",
        valid["pair_displacement_mm"].min(),
        "mm"
    )

    print(
        "Max:",
        valid["pair_displacement_mm"].max(),
        "mm"
    )

    print(
        "Mean:",
        valid["pair_displacement_mm"].mean(),
        "mm"
    )

    print(
        "Median:",
        valid["pair_displacement_mm"].median(),
        "mm"
    )


# ============================================================
# QUALITY SUMMARY
# ============================================================

print("\nQuality summary:")

print(
    df["temporal_quality_flag"].value_counts()
)


# ============================================================
# VALID PIXEL COVERAGE
# ============================================================

print(
    "\nValid pixel percentage:"
)

print(
    "Min:",
    df["valid_pixel_percentage"].min()
)

print(
    "Max:",
    df["valid_pixel_percentage"].max()
)

print(
    "Mean:",
    df["valid_pixel_percentage"].mean()
)


# ============================================================
# OUTPUT
# ============================================================

print(
    "\nOutput:",
    OUTPUT_FILE
)

print("\n" + "=" * 70)
print("PAIR 02 TEMPORAL FEATURES COMPLETE")
print("=" * 70) 