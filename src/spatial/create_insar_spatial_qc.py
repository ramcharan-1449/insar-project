from pathlib import Path
import geopandas as gpd
import pandas as pd


# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

GRID_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "mine_grid_coverage.geojson"
)

FEATURE_FILE = (
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
    / "insar_spatial_qc_test_pair_01.geojson"
)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print("=" * 70)
    print("        CREATE INSAR SPATIAL QC LAYER")
    print("=" * 70)

    # Load grid
    grid = gpd.read_file(GRID_FILE)

    # Load InSAR spatial features
    features = pd.read_csv(FEATURE_FILE)

    print(f"\nGrid cells     : {len(grid)}")
    print(f"Feature rows   : {len(features)}")

    # -----------------------------------------------------
    # CHECK CELL IDs
    # -----------------------------------------------------

    if grid["cell_id"].duplicated().any():
        raise ValueError("Duplicate cell_id found in grid.")

    if features["cell_id"].duplicated().any():
        raise ValueError("Duplicate cell_id found in feature CSV.")

    # -----------------------------------------------------
    # JOIN GRID + INSAR FEATURES
    # -----------------------------------------------------

    merged = grid.merge(
        features,
        on="cell_id",
        how="left",
        validate="one_to_one",
        indicator=True
    )

    missing = (merged["_merge"] != "both").sum()

    if missing > 0:
        raise ValueError(
            f"{missing} grid cells did not match feature records."
        )

    merged = merged.drop(columns=["_merge"])

    # -----------------------------------------------------
    # SAVE GEOJSON
    # -----------------------------------------------------

    merged.to_file(
        OUTPUT_FILE,
        driver="GeoJSON"
    )

    # -----------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------

    print("\nQuality summary:")
    print(
        merged["quality_flag"]
        .value_counts(dropna=False)
    )

    print("\nCRS:")
    print(merged.crs)

    print("\nOutput:")
    print(OUTPUT_FILE)

    print("\nColumns:")
    print(", ".join(merged.columns))

    print("\n" + "=" * 70)
    print("             QC LAYER CREATED")
    print("=" * 70)


if __name__ == "__main__":
    main()