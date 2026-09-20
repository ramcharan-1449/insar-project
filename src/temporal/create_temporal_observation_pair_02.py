import pandas as pd
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

INPUT_FILE = Path(
    "data/processed/grid/"
    "spatial_features_test_pair_02.csv"
)

OUTPUT_FILE = Path(
    "data/processed/grid/"
    "temporal_observations_test_pair_02.csv"
)


# ============================================================
# PAIR INFORMATION
# ============================================================

PAIR_ID = "test_pair_02"

REFERENCE_SCENE = (
    "S1A_IW_SLC__1SDV_20240603T121315_20240603T121342_"
    "054159_069615_B498"
)

SECONDARY_SCENE = (
    "S1A_IW_SLC__1SDV_20240615T121315_20240615T121342_"
    "054334_069C22_5A68"
)

REFERENCE_DATE = pd.Timestamp("2024-06-03")

SECONDARY_DATE = pd.Timestamp("2024-06-15")

TEMPORAL_BASELINE_DAYS = 12

OBSERVATION_TYPE = "PAIR_DISPLACEMENT"


# ============================================================
# LOAD
# ============================================================

df = pd.read_csv(INPUT_FILE)

print("=" * 70)
print("          PAIR 02 TEMPORAL OBSERVATION")
print("=" * 70)

print("\nInput rows:", len(df))


# ============================================================
# ADD TEMPORAL INFORMATION
# ============================================================

df["pair_id"] = PAIR_ID

df["reference_scene"] = REFERENCE_SCENE

df["secondary_scene"] = SECONDARY_SCENE

df["reference_date"] = (
    REFERENCE_DATE.strftime("%Y-%m-%d")
)

df["secondary_date"] = (
    SECONDARY_DATE.strftime("%Y-%m-%d")
)

df["temporal_baseline_days"] = (
    TEMPORAL_BASELINE_DAYS
)

df["observation_type"] = OBSERVATION_TYPE


# ============================================================
# VALIDATION
# ============================================================

if df["cell_id"].duplicated().any():

    raise RuntimeError(
        "Duplicate cell_id found."
    )

if REFERENCE_DATE >= SECONDARY_DATE:

    raise RuntimeError(
        "Reference date must be earlier than "
        "secondary date."
    )

if TEMPORAL_BASELINE_DAYS <= 0:

    raise RuntimeError(
        "Temporal baseline must be positive."
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

print("\nTemporal observation created.")

print(
    "Pair ID:",
    PAIR_ID
)

print(
    "Reference:",
    REFERENCE_DATE.strftime("%Y-%m-%d")
)

print(
    "Secondary:",
    SECONDARY_DATE.strftime("%Y-%m-%d")
)

print(
    "Temporal baseline:",
    TEMPORAL_BASELINE_DAYS,
    "days"
)

print(
    "Observation type:",
    OBSERVATION_TYPE
)

print(
    "\nOutput:",
    OUTPUT_FILE
)

print("\nQuality summary:")

print(
    df["quality_flag"].value_counts()
)

print("\n" + "=" * 70)
print("PAIR 02 TEMPORAL OBSERVATION COMPLETE")
print("=" * 70)
