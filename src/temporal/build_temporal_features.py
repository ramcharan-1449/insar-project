from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_grid_features.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "insar_temporal_features.csv"
)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("Stage 7 - Temporal Feature Engineering")
    print("=" * 70)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # LOAD SPATIAL FEATURES
    # --------------------------------------------------------

    print()
    print("Loading spatial feature dataset...")

    df = pd.read_csv(INPUT_FILE)

    print(f"Rows    : {len(df)}")
    print(f"Columns : {len(df.columns)}")

    # --------------------------------------------------------
    # CONVERT DATES
    # --------------------------------------------------------

    df["reference_date"] = pd.to_datetime(
        df["reference_date"]
    )

    df["secondary_date"] = pd.to_datetime(
        df["secondary_date"]
    )

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    df = df.sort_values(
        [
            "cell_id",
            "reference_date",
            "secondary_date",
        ]
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # BASIC TEMPORAL INFORMATION
    # --------------------------------------------------------

    df["mid_date"] = (
        df["reference_date"]
        + (
            df["secondary_date"]
            - df["reference_date"]
        ) / 2
    )

    # --------------------------------------------------------
    # PAIR-WISE LOS DISPLACEMENT
    # --------------------------------------------------------

    # Convert metres to millimetres

    df["los_displacement_mm"] = (
        df["los_displacement_mean"]
        * 1000.0
    )

    df["vertical_displacement_mm"] = (
        df["vertical_displacement_mean"]
        * 1000.0
    )

    # --------------------------------------------------------
    # PAIR-WISE DISPLACEMENT RATE
    # --------------------------------------------------------

    # This is the displacement rate for an individual
    # interferogram pair, NOT a final long-term velocity.

    df["los_pair_rate_mm_per_year"] = np.where(
        df["temporal_baseline_days"] > 0,
        (
            df["los_displacement_mm"]
            / df["temporal_baseline_days"]
        ) * 365.25,
        np.nan,
    )

    df["vertical_pair_rate_mm_per_year"] = np.where(
        df["temporal_baseline_days"] > 0,
        (
            df["vertical_displacement_mm"]
            / df["temporal_baseline_days"]
        ) * 365.25,
        np.nan,
    )

    # --------------------------------------------------------
    # GROUP BY GRID CELL
    # --------------------------------------------------------

    print()
    print("Calculating temporal features per grid cell...")

    grouped = df.groupby(
        "cell_id",
        sort=True
    )

    temporal = grouped.agg(
        observation_count=(
            "los_displacement_mm",
            "count"
        ),

        mean_los_displacement_mm=(
            "los_displacement_mm",
            "mean"
        ),

        std_los_displacement_mm=(
            "los_displacement_mm",
            "std"
        ),

        min_los_displacement_mm=(
            "los_displacement_mm",
            "min"
        ),

        max_los_displacement_mm=(
            "los_displacement_mm",
            "max"
        ),

        mean_vertical_displacement_mm=(
            "vertical_displacement_mm",
            "mean"
        ),

        std_vertical_displacement_mm=(
            "vertical_displacement_mm",
            "std"
        ),

        mean_los_pair_rate_mm_per_year=(
            "los_pair_rate_mm_per_year",
            "mean"
        ),

        std_los_pair_rate_mm_per_year=(
            "los_pair_rate_mm_per_year",
            "std"
        ),

        mean_vertical_pair_rate_mm_per_year=(
            "vertical_pair_rate_mm_per_year",
            "mean"
        ),

        mean_coherence=(
            "coherence_mean",
            "mean"
        ),

        min_coherence=(
            "coherence_mean",
            "min"
        ),

        std_coherence=(
            "coherence_mean",
            "std"
        ),

        mean_valid_pixel_fraction=(
            "valid_pixel_fraction",
            "mean"
        ),
    ).reset_index()

    # --------------------------------------------------------
    # TEMPORAL RANGE
    # --------------------------------------------------------

    dates = grouped["mid_date"].agg(
        first_observation="min",
        last_observation="max",
    ).reset_index()

    temporal = temporal.merge(
        dates,
        on="cell_id",
        how="left"
    )

    temporal["observation_span_days"] = (
        temporal["last_observation"]
        - temporal["first_observation"]
    ).dt.days

    temporal["observation_span_years"] = (
        temporal["observation_span_days"]
        / 365.25
    )

    # --------------------------------------------------------
    # VALID OBSERVATION RATIO
    # --------------------------------------------------------

    total_products = df["product_id"].nunique()

    temporal["valid_observation_ratio"] = (
        temporal["observation_count"]
        / total_products
    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    temporal.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("STAGE 7 SUMMARY")
    print("=" * 70)

    print(
        f"Input rows          : {len(df)}"
    )

    print(
        f"HyP3 products       : {total_products}"
    )

    print(
        f"Grid cells          : {len(temporal)}"
    )

    print(
        f"Temporal columns    : {len(temporal.columns)}"
    )

    print(
        f"Output              : {OUTPUT_FILE}"
    )

    print()

    print("Temporal feature columns:")

    for column in temporal.columns:
        print(f"  {column}")

    print()
    print("Stage 7 completed.")


if __name__ == "__main__":
    main()