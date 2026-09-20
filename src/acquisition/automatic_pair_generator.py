from pathlib import Path
from datetime import datetime, timezone

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MANIFEST_FILE = PROJECT_ROOT / "config" / "sentinel1_scene_manifest.csv"

# Existing automatically selected/validated pairs
EXISTING_PAIR_FILES = [
    PROJECT_ROOT / "config" / "sentinel1_final_pairs.csv",
    PROJECT_ROOT / "config" / "sentinel1_final_pairs_geometry_validated.csv",
    PROJECT_ROOT / "config" / "hyp3_job_registry.csv",
]

OUTPUT_FILE = PROJECT_ROOT / "config" / "sentinel1_automatic_pairs.csv"

MAX_TEMPORAL_DAYS = 24
MAX_PERPENDICULAR_BASELINE_M = 200.0


# ============================================================
# HELPERS
# ============================================================

def normalize_scene_pair(scene1, scene2):
    """
    Create a unique pair key independent of ordering.
    """
    scenes = sorted([str(scene1), str(scene2)])
    return f"{scenes[0]}__{scenes[1]}"


def load_existing_pair_keys():
    """
    Load previously processed/submitted pairs so they are
    never automatically submitted again.
    """

    existing_keys = set()

    for file_path in EXISTING_PAIR_FILES:

        if not file_path.exists():
            continue

        try:
            df = pd.read_csv(file_path)

            # Normal pair files
            if "reference_scene" in df.columns and "secondary_scene" in df.columns:

                for _, row in df.iterrows():

                    if pd.notna(row["reference_scene"]) and pd.notna(
                        row["secondary_scene"]
                    ):
                        existing_keys.add(
                            normalize_scene_pair(
                                row["reference_scene"],
                                row["secondary_scene"],
                            )
                        )

            # HyP3 registry may use different names
            elif "reference_scene" in df.columns and "secondary_scene" in df.columns:

                for _, row in df.iterrows():
                    existing_keys.add(
                        normalize_scene_pair(
                            row["reference_scene"],
                            row["secondary_scene"],
                        )
                    )

        except Exception as exc:
            print(f"Warning: could not read {file_path.name}: {exc}")

    return existing_keys


# ============================================================
# LOAD SCENE MANIFEST
# ============================================================

print("=" * 70)
print("PHASE 15 — AUTOMATIC SENTINEL-1 PAIR GENERATION")
print("=" * 70)

if not MANIFEST_FILE.exists():
    raise FileNotFoundError(
        f"Scene manifest not found:\n{MANIFEST_FILE}"
    )

scenes = pd.read_csv(MANIFEST_FILE)

print(f"Scenes in manifest: {len(scenes)}")


# ============================================================
# NORMALIZE COLUMN NAMES
# ============================================================

scenes.columns = [c.strip() for c in scenes.columns]

print("\nManifest columns:")
for column in scenes.columns:
    print(f"  {column}")


# ============================================================
# REQUIRED COLUMNS
# ============================================================

required_columns = [
    "scene_id",
    "acquisition_date",
    "orbit_direction",
    "relative_orbit",
]

missing = [
    column
    for column in required_columns
    if column not in scenes.columns
]

if missing:
    raise ValueError(
        "Missing required manifest columns:\n"
        + "\n".join(f"  - {c}" for c in missing)
    )


# ============================================================
# DATE CONVERSION
# ============================================================

scenes["acquisition_date"] = pd.to_datetime(
    scenes["acquisition_date"],
    utc=True,
    errors="coerce",
)

scenes = scenes.dropna(
    subset=[
        "scene_id",
        "acquisition_date",
        "orbit_direction",
        "relative_orbit",
    ]
)

scenes["relative_orbit"] = pd.to_numeric(
    scenes["relative_orbit"],
    errors="coerce",
)

scenes = scenes.dropna(subset=["relative_orbit"])

scenes["relative_orbit"] = scenes["relative_orbit"].astype(int)


# ============================================================
# SORT CHRONOLOGICALLY
# ============================================================

scenes = scenes.sort_values(
    [
        "orbit_direction",
        "relative_orbit",
        "acquisition_date",
    ]
).reset_index(drop=True)


# ============================================================
# LOAD EXISTING PAIRS
# ============================================================

existing_pairs = load_existing_pair_keys()

print(f"\nPreviously processed/submitted pairs: {len(existing_pairs)}")


# ============================================================
# GENERATE CANDIDATE PAIRS
# ============================================================

candidate_pairs = []

group_columns = [
    "orbit_direction",
    "relative_orbit",
]

grouped = scenes.groupby(group_columns)

for (orbit_direction, relative_orbit), group in grouped:

    group = group.sort_values("acquisition_date").reset_index(drop=True)

    # Compare each scene with later scenes in the same track.
    for i in range(len(group)):

        reference = group.iloc[i]

        for j in range(i + 1, len(group)):

            secondary = group.iloc[j]

            temporal_days = (
                secondary["acquisition_date"]
                - reference["acquisition_date"]
            ).total_seconds() / 86400.0

            # Because scenes are chronological, once this exceeds
            # the allowed temporal window, later scenes will also
            # exceed it.
            if temporal_days > MAX_TEMPORAL_DAYS:
                break

            if temporal_days <= 0:
                continue

            reference_scene = reference["scene_id"]
            secondary_scene = secondary["scene_id"]

            pair_key = normalize_scene_pair(
                reference_scene,
                secondary_scene,
            )

            # Never regenerate an already processed pair.
            if pair_key in existing_pairs:
                continue

            candidate_pairs.append(
                {
                    "reference_scene": reference_scene,
                    "secondary_scene": secondary_scene,
                    "reference_date": reference["acquisition_date"],
                    "secondary_date": secondary["acquisition_date"],
                    "temporal_baseline_days": round(
                        temporal_days,
                        3,
                    ),
                    "orbit_direction": orbit_direction,
                    "relative_orbit": int(relative_orbit),
                    "pair_key": pair_key,
                    "selection_status": "CANDIDATE",
                }
            )


# ============================================================
# CREATE DATAFRAME
# ============================================================

pairs = pd.DataFrame(candidate_pairs)

if pairs.empty:

    print("\nNo new candidate pairs found.")

    # Still create an empty file with predictable columns.
    pairs = pd.DataFrame(
        columns=[
            "reference_scene",
            "secondary_scene",
            "reference_date",
            "secondary_date",
            "temporal_baseline_days",
            "perpendicular_baseline_m",
            "orbit_direction",
            "relative_orbit",
            "quality",
            "selection_status",
            "pair_key",
        ]
    )

else:

    pairs["reference_date"] = pd.to_datetime(
        pairs["reference_date"],
        utc=True,
    ).dt.strftime("%Y-%m-%d")

    pairs["secondary_date"] = pd.to_datetime(
        pairs["secondary_date"],
        utc=True,
    ).dt.strftime("%Y-%m-%d")


# ============================================================
# SAVE
# ============================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

pairs.to_csv(
    OUTPUT_FILE,
    index=False,
)


# ============================================================
# REPORT
# ============================================================

print("\n" + "-" * 70)
print("AUTOMATIC PAIR GENERATION RESULT")
print("-" * 70)

print(f"Scenes available       : {len(scenes)}")
print(f"Existing pair keys     : {len(existing_pairs)}")
print(f"New temporal candidates: {len(pairs)}")

if not pairs.empty:

    print("\nCandidates by orbit:")

    summary = (
        pairs.groupby(
            [
                "orbit_direction",
                "relative_orbit",
            ]
        )
        .size()
        .reset_index(name="pair_count")
    )

    for _, row in summary.iterrows():

        print(
            f"  {row['orbit_direction']} "
            f"orbit {int(row['relative_orbit'])}: "
            f"{int(row['pair_count'])}"
        )

print("\nOutput:")
print(OUTPUT_FILE)

print("\n" + "=" * 70)
print("PHASE 15 TEMPORAL CANDIDATE GENERATION COMPLETE")
print("=" * 70)