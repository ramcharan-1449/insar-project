from pathlib import Path
import pandas as pd


# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "config"
    / "sentinel1_final_pairs.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "config"
    / "sentinel1_final_pairs_normalized.csv"
)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print("=" * 70)
    print("          NORMALIZE INSAR PAIR ORDER")
    print("=" * 70)

    df = pd.read_csv(INPUT_FILE)

    print(f"\nInput pairs: {len(df)}")

    normalized_rows = []

    for _, row in df.iterrows():

        reference_date = pd.to_datetime(row["reference_date"])
        secondary_date = pd.to_datetime(row["secondary_date"])

        # -------------------------------------------------
        # Older acquisition becomes Reference
        # Newer acquisition becomes Secondary
        # -------------------------------------------------

        if reference_date <= secondary_date:

            older_scene = row["reference_scene"]
            newer_scene = row["secondary_scene"]

            older_date = reference_date
            newer_date = secondary_date

        else:

            older_scene = row["secondary_scene"]
            newer_scene = row["reference_scene"]

            older_date = secondary_date
            newer_date = reference_date

        # -------------------------------------------------
        # Calculate positive temporal baseline
        # -------------------------------------------------

        temporal_days = (
            newer_date - older_date
        ).days

        new_row = row.copy()

        new_row["reference_scene"] = older_scene
        new_row["secondary_scene"] = newer_scene

        new_row["reference_date"] = older_date.strftime("%Y-%m-%d")
        new_row["secondary_date"] = newer_date.strftime("%Y-%m-%d")

        new_row["temporal_baseline_days"] = temporal_days

        # Record what we did
        new_row["selection_reason"] = (
            str(row["selection_reason"])
            + "; normalized older-to-newer"
        )

        normalized_rows.append(new_row)

    normalized = pd.DataFrame(normalized_rows)

    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    invalid = (
        pd.to_datetime(normalized["reference_date"])
        >
        pd.to_datetime(normalized["secondary_date"])
    )

    if invalid.any():
        raise ValueError(
            "Some pairs are still in reverse chronological order."
        )

    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    normalized.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # -----------------------------------------------------
    # DISPLAY
    # -----------------------------------------------------

    print("\nNormalized pairs:\n")

    for i, row in normalized.iterrows():

        print(
            f"Pair {i + 1}: "
            f"{row['reference_date']} -> "
            f"{row['secondary_date']} | "
            f"{row['orbit_direction']} | "
            f"Path {row['relative_orbit']} | "
            f"{row['temporal_baseline_days']} days | "
            f"{row['perpendicular_baseline_m']} m"
        )

    print("\nAll pairs are chronologically ordered.")

    print("\nOutput:")
    print(OUTPUT_FILE)

    print("\n" + "=" * 70)
    print("          NORMALIZATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
    