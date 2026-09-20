import pandas as pd
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "config" / "sentinel1_candidate_pairs.csv"
OUTPUT_FILE = PROJECT_ROOT / "config" / "sentinel1_priority_pairs.csv"


# Number of pairs we want for initial HyP3 processing
PAIRS_PER_TRACK = 3


print("=" * 70)
print("       SENTINEL-1 PRIORITY PAIR SELECTION")
print("=" * 70)


# ---------------------------------------------------------
# Load candidate pairs
# ---------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

print("\nCandidate pairs loaded:", len(df))


# ---------------------------------------------------------
# Convert dates
# ---------------------------------------------------------

df["master_date"] = pd.to_datetime(
    df["master_date"],
    utc=True
)

df["slave_date"] = pd.to_datetime(
    df["slave_date"],
    utc=True
)


# ---------------------------------------------------------
# Sort by temporal baseline
# ---------------------------------------------------------

df = df.sort_values(
    [
        "orbit_direction",
        "relative_orbit",
        "temporal_baseline_days",
        "master_date"
    ]
)


# ---------------------------------------------------------
# Select shortest pairs from each track
# ---------------------------------------------------------

priority_pairs = []

for (orbit_direction, relative_orbit), group in df.groupby(
    ["orbit_direction", "relative_orbit"]
):

    group = group.sort_values(
        [
            "temporal_baseline_days",
            "master_date"
        ]
    )

    selected = group.head(PAIRS_PER_TRACK).copy()

    selected["status"] = "PRIORITY_CANDIDATE"

    selected["notes"] = (
        "Short temporal baseline; spatial baseline must be checked before HyP3."
    )

    priority_pairs.append(selected)


# ---------------------------------------------------------
# Combine selected pairs
# ---------------------------------------------------------

priority_df = pd.concat(
    priority_pairs,
    ignore_index=True
)


# ---------------------------------------------------------
# Final sorting
# ---------------------------------------------------------

priority_df = priority_df.sort_values(
    [
        "temporal_baseline_days",
        "orbit_direction",
        "relative_orbit",
        "master_date"
    ]
)


# ---------------------------------------------------------
# Save
# ---------------------------------------------------------

priority_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ---------------------------------------------------------
# Display results
# ---------------------------------------------------------

print("\nPriority pairs selected:", len(priority_df))

print("\nPairs selected from each track:")

print(
    priority_df.groupby(
        [
            "orbit_direction",
            "relative_orbit"
        ]
    ).size()
)


print("\nPriority pairs:")

print(
    priority_df[
        [
            "master_scene",
            "slave_scene",
            "orbit_direction",
            "relative_orbit",
            "temporal_baseline_days",
            "status"
        ]
    ].to_string(index=False)
)


print("\nOutput file:")
print(OUTPUT_FILE)


print("\nIMPORTANT:")
print("These are PRIORITY CANDIDATES only.")
print("Spatial baseline has NOT been checked yet.")
print("Do NOT submit them to HyP3 yet.")


print("\n" + "=" * 70)
print("              PRIORITY SELECTION COMPLETE")
print("=" * 70)