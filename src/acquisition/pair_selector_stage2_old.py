import pandas as pd
from pathlib import Path
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

BASE = Path(__file__).resolve().parents[2]

INPUT_FILE = BASE / "config" / "sentinel1_scene_inventory_auto.csv"

OUTPUT_FILE = BASE / "config" / "sentinel1_candidate_pairs_auto.csv"

PRIORITY_FILE = BASE / "config" / "sentinel1_priority_pairs_auto.csv"


# Maximum temporal separation allowed
MAX_TEMPORAL_DAYS = 24

# Number of best pairs to keep from each track
PAIRS_PER_TRACK = 3


# ============================================================
# LOAD SCENE INVENTORY
# ============================================================

def load_inventory():

    print("=" * 60)
    print("LOADING AUTOMATIC SENTINEL-1 INVENTORY")
    print("=" * 60)

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"Inventory file not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    print(f"Scenes loaded: {len(df)}")

    return df


# ============================================================
# CLEAN INVENTORY
# ============================================================

def clean_inventory(df):

    print()
    print("=" * 60)
    print("CLEANING SCENE INVENTORY")
    print("=" * 60)

    required_columns = [
        "scene_id",
        "acquisition_date",
        "orbit_direction",
        "relative_orbit",
        "frame",
        "product_type",
        "beam_mode"
    ]

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:

        raise ValueError(
            f"Missing required columns: {missing}"
        )

    # Convert acquisition date
    df["acquisition_date"] = pd.to_datetime(
        df["acquisition_date"],
        errors="coerce"
    )

    # Remove invalid dates
    before = len(df)

    df = df.dropna(
        subset=[
            "scene_id",
            "acquisition_date",
            "orbit_direction",
            "relative_orbit"
        ]
    )

    print(
        f"Removed invalid scenes: "
        f"{before - len(df)}"
    )

    # Remove duplicate scene IDs
    before = len(df)

    df = df.drop_duplicates(
        subset=["scene_id"]
    )

    print(
        f"Removed duplicate scenes: "
        f"{before - len(df)}"
    )

    # Keep only Sentinel-1 SLC IW
    df = df[
        (df["product_type"].astype(str).str.upper() == "SLC")
        &
        (df["beam_mode"].astype(str).str.upper() == "IW")
    ]

    print(f"Scenes after filtering: {len(df)}")

    return df


# ============================================================
# GENERATE CANDIDATE PAIRS
# ============================================================

def generate_pairs(df):

    print()
    print("=" * 60)
    print("GENERATING CANDIDATE PAIRS")
    print("=" * 60)

    all_pairs = []

    # Group by orbit direction and relative orbit
    grouped = df.groupby(
        [
            "orbit_direction",
            "relative_orbit"
        ]
    )

    for (orbit_direction, relative_orbit), group in grouped:

        group = group.sort_values(
            "acquisition_date"
        ).reset_index(drop=True)

        print()
        print(
            f"Track: {orbit_direction} "
            f"Relative Orbit: {relative_orbit}"
        )

        print(
            f"Scenes in track: {len(group)}"
        )

        for i in range(len(group)):

            reference = group.iloc[i]

            for j in range(i + 1, len(group)):

                secondary = group.iloc[j]

                temporal_days = (
                    secondary["acquisition_date"]
                    - reference["acquisition_date"]
                ).total_seconds() / 86400.0

                # Only keep pairs within allowed time
                if temporal_days > MAX_TEMPORAL_DAYS:

                    # Since data is sorted by date,
                    # later pairs will only be longer.
                    break

                if temporal_days <= 0:
                    continue

                all_pairs.append({

                    "reference_scene":
                        reference["scene_id"],

                    "secondary_scene":
                        secondary["scene_id"],

                    "reference_date":
                        reference["acquisition_date"].strftime(
                            "%Y-%m-%d"
                        ),

                    "secondary_date":
                        secondary["acquisition_date"].strftime(
                            "%Y-%m-%d"
                        ),

                    "temporal_baseline_days":
                        round(temporal_days, 2),

                    "orbit_direction":
                        orbit_direction,

                    "relative_orbit":
                        relative_orbit,

                    "reference_frame":
                        reference["frame"],

                    "secondary_frame":
                        secondary["frame"],

                    "reference_url":
                        reference["url"],

                    "secondary_url":
                        secondary["url"]

                })

    pairs = pd.DataFrame(all_pairs)

    print()
    print(f"Candidate pairs generated: {len(pairs)}")

    return pairs


# ============================================================
# RANK PAIRS
# ============================================================

def rank_pairs(pairs):

    print()
    print("=" * 60)
    print("RANKING CANDIDATE PAIRS")
    print("=" * 60)

    if pairs.empty:

        print("No candidate pairs found.")

        return pairs

    # For now, temporal baseline is the only
    # automatically available baseline measurement.
    #
    # Shorter temporal baseline gets better score.
    #
    # Perpendicular baseline will be added after
    # we connect ASF baseline metadata.

    pairs["score"] = (
        pairs["temporal_baseline_days"].abs()
    )

    pairs = pairs.sort_values(
        [
            "orbit_direction",
            "relative_orbit",
            "score"
        ]
    ).reset_index(drop=True)

    return pairs


# ============================================================
# SELECT PRIORITY PAIRS
# ============================================================

def select_priority_pairs(pairs):

    print()
    print("=" * 60)
    print("SELECTING PRIORITY PAIRS")
    print("=" * 60)

    priority = []

    grouped = pairs.groupby(
        [
            "orbit_direction",
            "relative_orbit"
        ]
    )

    for (orbit_direction, relative_orbit), group in grouped:

        selected = group.head(
            PAIRS_PER_TRACK
        )

        priority.append(selected)

        print()
        print(
            f"{orbit_direction} "
            f"Relative Orbit {relative_orbit}: "
            f"{len(selected)} pairs selected"
        )

    if priority:

        priority_df = pd.concat(
            priority,
            ignore_index=True
        )

    else:

        priority_df = pd.DataFrame()

    return priority_df


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(pairs, priority):

    print()
    print("=" * 60)
    print("SAVING AUTOMATIC PAIR RESULTS")
    print("=" * 60)

    pairs.to_csv(
        OUTPUT_FILE,
        index=False
    )

    priority.to_csv(
        PRIORITY_FILE,
        index=False
    )

    print()
    print(f"Candidate pairs:")
    print(OUTPUT_FILE)

    print()
    print(f"Priority pairs:")
    print(PRIORITY_FILE)


# ============================================================
# MAIN
# ============================================================

def main():

    df = load_inventory()

    df = clean_inventory(df)

    pairs = generate_pairs(df)

    pairs = rank_pairs(pairs)

    priority = select_priority_pairs(
        pairs
    )

    save_results(
        pairs,
        priority
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 60)
    print("AUTOMATIC PAIR SELECTION COMPLETE")
    print("=" * 60)

    print(
        f"Total candidate pairs: {len(pairs)}"
    )

    print(
        f"Priority pairs: {len(priority)}"
    )

    if not priority.empty:

        print()
        print("SELECTED PAIRS:")
        print()

        display_columns = [
            "reference_date",
            "secondary_date",
            "temporal_baseline_days",
            "orbit_direction",
            "relative_orbit",
            "reference_scene",
            "secondary_scene"
        ]

        print(
            priority[display_columns]
            .to_string(index=False)
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()