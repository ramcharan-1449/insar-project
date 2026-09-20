import pandas as pd
from pathlib import Path

BASE = Path("data/processed/grid")

INPUT = BASE / "spatial_features_test_pair_03.csv"
OUTPUT = BASE / "temporal_features_test_pair_03.csv"

PAIR_ID = "test_pair_03"

REFERENCE_DATE = "2024-05-10"
SECONDARY_DATE = "2024-06-03"

TEMPORAL_BASELINE_DAYS = 24

REFERENCE_SCENE = (
    "S1A_IW_SLC__1SDV_20240510T121316_"
    "20240510T121343_053809_068A02_58C3"
)

SECONDARY_SCENE = (
    "S1A_IW_SLC__1SDV_20240603T121315_"
    "20240603T121342_054159_069615_B498"
)


print("Creating Pair 03 temporal features...")
print()

# --------------------------------------------------
# Read spatial features
# --------------------------------------------------

df = pd.read_csv(INPUT)

print("Input:", INPUT)
print("Rows:", len(df))

# --------------------------------------------------
# Standardize column name if necessary
# --------------------------------------------------

if "valid_percentage" in df.columns:
    df = df.rename(
        columns={
            "valid_percentage":
            "valid_pixel_percentage"
        }
    )

# --------------------------------------------------
# Add pair metadata
# --------------------------------------------------

df["pair_id"] = PAIR_ID
df["reference_scene"] = REFERENCE_SCENE
df["secondary_scene"] = SECONDARY_SCENE

df["reference_date"] = REFERENCE_DATE
df["secondary_date"] = SECONDARY_DATE

df["temporal_baseline_days"] = TEMPORAL_BASELINE_DAYS

df["observation_type"] = "PAIR_DISPLACEMENT"

df["observation_mid_date"] = (
    pd.to_datetime(REFERENCE_DATE)
    + (
        pd.to_datetime(SECONDARY_DATE)
        - pd.to_datetime(REFERENCE_DATE)
    ) / 2
).strftime("%Y-%m-%d")

# Pairwise displacement is LOS displacement,
# not velocity.
df["los_displacement_mm"] = df[
    "mean_los_disp_mm"
]

df["pair_displacement_mm"] = df[
    "mean_los_disp_mm"
]

# --------------------------------------------------
# Temporal quality
# --------------------------------------------------

def temporal_quality(row):

    if row["quality_flag"] == "VALID":
        return "VALID"

    if row["quality_flag"] == "LOW_COVERAGE":
        return "LOW_COVERAGE"

    if row["quality_flag"] == "LOW_CORRELATION":
        return "LOW_CORRELATION"

    return "NO_DATA"


df["temporal_quality_flag"] = df.apply(
    temporal_quality,
    axis=1
)

# --------------------------------------------------
# Observation sequence
# --------------------------------------------------

df["observation_sequence"] = 3

# --------------------------------------------------
# Arrange columns
# --------------------------------------------------

output_columns = [
    "pair_id",
    "reference_date",
    "secondary_date",
    "temporal_baseline_days",
    "reference_scene",
    "secondary_scene",
    "cell_id",
    "mean_los_disp_m",
    "median_los_disp_m",
    "mean_los_disp_mm",
    "median_los_disp_mm",
    "mean_correlation",
    "valid_pixel_count",
    "total_pixel_count",
    "valid_pixel_percentage",
    "quality_flag",
    "observation_type",
    "observation_mid_date",
    "los_displacement_mm",
    "pair_displacement_mm",
    "temporal_quality_flag",
    "observation_sequence",
]

missing = [
    col for col in output_columns
    if col not in df.columns
]

if missing:

    print()
    print("ERROR: Missing columns:")

    for col in missing:
        print(" -", col)

    raise SystemExit(1)

df = df[output_columns]

# --------------------------------------------------
# Save
# --------------------------------------------------

df.to_csv(
    OUTPUT,
    index=False
)

print()
print("Output:", OUTPUT)
print("Rows:", len(df))
print("Columns:", len(df.columns))

print()
print("Quality:")
print(
    df["quality_flag"]
    .value_counts()
    .to_string()
)

print()
print("Pair 03 temporal features created.")