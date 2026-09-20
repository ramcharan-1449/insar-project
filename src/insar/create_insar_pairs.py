import pandas as pd
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "config" / "sentinel1_scene_inventory.csv"
OUTPUT_FILE = PROJECT_ROOT / "config" / "sentinel1_candidate_pairs.csv"


# Maximum temporal separation for candidate pairs
MAX_DAYS = 24


print("=" * 70)
print("       SENTINEL-1 INSAR CANDIDATE PAIR GENERATOR")
print("=" * 70)


# ---------------------------------------------------------
# Load inventory
# ---------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

df["acquisition_date"] = pd.to_datetime(
    df["acquisition_date"],
    utc=True
)

print("\nTotal scenes:", len(df))


# ---------------------------------------------------------
# Keep only SLC scenes
# ---------------------------------------------------------

df = df[df["product_type"] == "SLC"].copy()


# ---------------------------------------------------------
# Create pairs
# ---------------------------------------------------------

pairs = []

group_columns = [
    "orbit_direction",
    "relative_orbit"
]

for (orbit_direction, relative_orbit), group in df.groupby(group_columns):

    group = group.sort_values("acquisition_date").reset_index(drop=True)

    for i in range(len(group)):

        for j in range(i + 1, len(group)):

            master = group.iloc[i]
            slave = group.iloc[j]

            temporal_baseline = (
                slave["acquisition_date"] -
                master["acquisition_date"]
            ).days

            if temporal_baseline <= MAX_DAYS:

                pairs.append({
                    "master_scene": master["scene_id"],
                    "slave_scene": slave["scene_id"],
                    "master_date": master["acquisition_date"],
                    "slave_date": slave["acquisition_date"],
                    "orbit_direction": orbit_direction,
                    "relative_orbit": relative_orbit,
                    "master_polarization": master["polarization"],
                    "slave_polarization": slave["polarization"],
                    "temporal_baseline_days": temporal_baseline,
                    "status": "CANDIDATE",
                    "spatial_baseline": "TO_BE_CHECKED",
                    "hyp3_status": "NOT_SUBMITTED",
                    "notes": ""
                })


# ---------------------------------------------------------
# Create DataFrame
# ---------------------------------------------------------

pairs_df = pd.DataFrame(pairs)


if len(pairs_df) == 0:

    print("\nNo candidate pairs found.")

else:

    # Sort shortest temporal baseline first
    pairs_df = pairs_df.sort_values(
        [
            "temporal_baseline_days",
            "orbit_direction",
            "relative_orbit"
        ]
    )

    pairs_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\nCandidate pairs generated:", len(pairs_df))

    print("\nPairs by orbit:")

    print(
        pairs_df.groupby(
            [
                "orbit_direction",
                "relative_orbit"
            ]
        ).size()
    )

    print("\nShortest candidate pairs:")

    print(
        pairs_df[
            [
                "master_scene",
                "slave_scene",
                "orbit_direction",
                "relative_orbit",
                "temporal_baseline_days"
            ]
        ].head(20).to_string(index=False)
    )

    print("\nOutput file:")
    print(OUTPUT_FILE)


print("\n" + "=" * 70)
print("              PAIR GENERATION COMPLETE")
print("=" * 70)