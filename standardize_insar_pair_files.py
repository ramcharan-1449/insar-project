import pandas as pd
from pathlib import Path

base = Path("data/processed/grid")

files = {
    "test_pair_01": base / "temporal_features_test_pair_01.csv",
    "test_pair_02": base / "temporal_features_test_pair_02.csv",
}

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

for pair_id, path in files.items():

    print(f"\nProcessing {pair_id}...")
    df = pd.read_csv(path)

    # Standardize Pair 02 naming
    rename_map = {
        "mean_los_m": "mean_los_disp_m",
        "median_los_m": "median_los_disp_m",
        "mean_los_mm": "mean_los_disp_mm",
        "median_los_mm": "median_los_disp_mm",
        "valid_percentage": "valid_pixel_percentage",
    }

    df = df.rename(columns=rename_map)

    # Add missing pair_id if necessary
    if "pair_id" not in df.columns:
        df["pair_id"] = pair_id

    # Add missing displacement field if necessary
    if "los_displacement_mm" not in df.columns:
        df["los_displacement_mm"] = df["pair_displacement_mm"]

    # Check required columns
    missing = [c for c in output_columns if c not in df.columns]

    if missing:
        print("Missing columns:")
        for col in missing:
            print("  -", col)
        continue

    df = df[output_columns]

    output = base / f"standardized_{pair_id}.csv"
    df.to_csv(output, index=False)

    print(f"Saved: {output}")
    print(f"Rows: {len(df)}")
    print("Columns:", len(df.columns))

print("\nStandardization complete.")