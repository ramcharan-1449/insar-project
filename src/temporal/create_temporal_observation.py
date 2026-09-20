from pathlib import Path

import pandas as pd


# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SPATIAL_FEATURE_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "spatial_features_test_pair_01.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "temporal_observations_test_pair_01.csv"
)


# ---------------------------------------------------------
# TEST PAIR INFORMATION
# ---------------------------------------------------------

PAIR_ID = "test_pair_01"

REFERENCE_SCENE = (
    "S1A_IW_SLC__1SDV_20240123T121315_20240123T121341_052234_065093_F3A2"
)

SECONDARY_SCENE = (
    "S1A_IW_SLC__1SDV_20240204T121314_20240204T121341_052409_06567F_3AFD"
)

REFERENCE_DATE = "2024-01-23"
SECONDARY_DATE = "2024-02-04"

TEMPORAL_BASELINE_DAYS = 12


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print("=" * 70)
    print("        CREATE TEMPORAL INSAR OBSERVATION")
    print("=" * 70)

    # -----------------------------------------------------
    # LOAD SPATIAL FEATURES
    # -----------------------------------------------------

    df = pd.read_csv(SPATIAL_FEATURE_FILE)

    print(f"\nInput rows: {len(df)}")

    # -----------------------------------------------------
    # ADD TEMPORAL INFORMATION
    # -----------------------------------------------------

    df.insert(0, "pair_id", PAIR_ID)

    df.insert(1, "reference_date", REFERENCE_DATE)

    df.insert(2, "secondary_date", SECONDARY_DATE)

    df.insert(3, "temporal_baseline_days", TEMPORAL_BASELINE_DAYS)

    df.insert(4, "reference_scene", REFERENCE_SCENE)

    df.insert(5, "secondary_scene", SECONDARY_SCENE)

    # -----------------------------------------------------
    # ADD OBSERVATION TYPE
    # -----------------------------------------------------

    df["observation_type"] = "PAIR_DISPLACEMENT"

    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    required_columns = [
        "pair_id",
        "reference_date",
        "secondary_date",
        "temporal_baseline_days",
        "reference_scene",
        "secondary_scene",
        "cell_id",
        "median_los_disp_m",
        "median_los_disp_mm",
        "mean_correlation",
        "valid_pixel_percentage",
        "quality_flag",
        "observation_type",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # Check unique grid-cell records
    if df["cell_id"].duplicated().any():
        raise ValueError(
            "Duplicate cell_id found in temporal observation."
        )

    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # -----------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------

    print(f"\nOutput rows: {len(df)}")

    print("\nPair:")
    print(f"  {REFERENCE_DATE} → {SECONDARY_DATE}")

    print(f"Temporal baseline: {TEMPORAL_BASELINE_DAYS} days")

    print("\nObservation type:")
    print(df["observation_type"].value_counts())

    print("\nQuality:")
    print(df["quality_flag"].value_counts())

    print("\nOutput:")
    print(OUTPUT_FILE)

    print("\n" + "=" * 70)
    print("       TEMPORAL OBSERVATION CREATED")
    print("=" * 70)


if __name__ == "__main__":
    main()