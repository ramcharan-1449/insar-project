from pathlib import Path
import pandas as pd


# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

GRID_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
)

OUTPUT_FILE = (
    GRID_DIR
    / "temporal_dataset.csv"
)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print("=" * 70)
    print("             BUILD TEMPORAL DATASET")
    print("=" * 70)

    # Find all temporal feature files
    files = sorted(
        GRID_DIR.glob("temporal_features_*.csv")
    )

    if not files:
        raise FileNotFoundError(
            "No temporal feature CSV files found."
        )

    print(f"\nTemporal files found: {len(files)}")

    for file in files:
        print(f"  - {file.name}")

    datasets = []

    # -----------------------------------------------------
    # Read each observation
    # -----------------------------------------------------

    for file in files:

        df = pd.read_csv(file)

        print(
            f"\nReading {file.name}: "
            f"{len(df)} rows"
        )

        required_columns = [
            "cell_id",
            "pair_id",
            "reference_date",
            "secondary_date",
            "temporal_baseline_days",
            "observation_type",
            "pair_displacement_mm",
            "mean_correlation",
            "valid_pixel_percentage",
            "temporal_quality_flag",
        ]

        missing = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing:
            raise ValueError(
                f"{file.name} is missing columns: {missing}"
            )

        # Keep only the columns needed for the
        # multi-date temporal dataset.
        df = df[required_columns].copy()

        datasets.append(df)

    # -----------------------------------------------------
    # Combine observations
    # -----------------------------------------------------

    temporal = pd.concat(
        datasets,
        ignore_index=True
    )

    # Convert dates
    temporal["reference_date"] = pd.to_datetime(
        temporal["reference_date"]
    )

    temporal["secondary_date"] = pd.to_datetime(
        temporal["secondary_date"]
    )

    # -----------------------------------------------------
    # Sort chronologically
    # -----------------------------------------------------

    temporal = temporal.sort_values(
        [
            "cell_id",
            "reference_date",
            "secondary_date",
        ]
    ).reset_index(drop=True)

    # -----------------------------------------------------
    # Assign observation sequence per cell
    # -----------------------------------------------------

    temporal["observation_sequence"] = (
        temporal.groupby("cell_id")
        .cumcount()
        + 1
    )

    # -----------------------------------------------------
    # Calculate midpoint date
    # -----------------------------------------------------

    temporal["observation_mid_date"] = (
        temporal["reference_date"]
        + (
            temporal["secondary_date"]
            - temporal["reference_date"]
        ) / 2
    )

    # -----------------------------------------------------
    # Validation
    # -----------------------------------------------------

    if temporal["cell_id"].isna().any():
        raise ValueError("Missing cell IDs found.")

    if temporal["pair_id"].isna().any():
        raise ValueError("Missing pair IDs found.")

    if (
        temporal["secondary_date"]
        < temporal["reference_date"]
    ).any():
        raise ValueError(
            "Found reverse chronological observations."
        )

    # A cell can occur multiple times,
    # but the same cell/pair combination must be unique.
    duplicates = temporal.duplicated(
        subset=["cell_id", "pair_id"]
    )

    if duplicates.any():
        raise ValueError(
            "Duplicate cell_id + pair_id observations found."
        )

    # -----------------------------------------------------
    # Save
    # -----------------------------------------------------

    temporal.to_csv(
        OUTPUT_FILE,
        index=False,
        date_format="%Y-%m-%d"
    )

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    print("\n" + "-" * 70)

    print(
        f"Total observations: {len(temporal)}"
    )

    print(
        f"Unique cells: "
        f"{temporal['cell_id'].nunique()}"
    )

    print(
        f"Unique pairs: "
        f"{temporal['pair_id'].nunique()}"
    )

    print("\nObservation types:")
    print(
        temporal["observation_type"]
        .value_counts()
        .to_string()
    )

    print("\nQuality:")
    print(
        temporal["temporal_quality_flag"]
        .value_counts()
        .to_string()
    )

    print("\nDate range:")

    print(
        f"  First: "
        f"{temporal['reference_date'].min().date()}"
    )

    print(
        f"  Last: "
        f"{temporal['secondary_date'].max().date()}"
    )

    print("\nOutput:")
    print(OUTPUT_FILE)

    print("\nNOTE:")
    print(
        "This dataset stores pair observations in "
        "chronological order."
    )

    print(
        "Velocity and long-term trends will only be "
        "calculated after enough multi-date observations "
        "are available."
    )

    print("=" * 70)


if __name__ == "__main__":
    main()