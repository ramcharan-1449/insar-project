import pandas as pd
from pathlib import Path

BASE = Path("data/processed/grid")

FILES = {
    "Pair 01": BASE / "standardized_test_pair_01.csv",
    "Pair 02": BASE / "standardized_test_pair_02.csv",
    "Pair 03": BASE / "standardized_test_pair_03.csv",
}

EXPECTED_CELLS = 292

EXPECTED_COLUMNS = [
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

ALLOWED_QUALITY = {
    "NO_DATA",
    "LOW_COVERAGE",
    "LOW_CORRELATION",
    "VALID",
}


def main():

    print("=" * 60)
    print("FINAL INSAR DATASET QC")
    print("=" * 60)

    dataframes = {}

    # ---------------------------------------------------------
    # 1. Check files
    # ---------------------------------------------------------
    print("\n[1] FILE CHECK")

    for name, path in FILES.items():

        if path.exists():
            print(f"PASS  {name}: {path}")
            dataframes[name] = pd.read_csv(path)
        else:
            print(f"WAIT  {name}: file not available")

    if len(dataframes) < 3:
        print("\nQC cannot be completed yet.")
        print("Waiting for all 3 standardized pair files.")
        return

    # ---------------------------------------------------------
    # 2. Row and cell count
    # ---------------------------------------------------------
    print("\n[2] GRID CHECK")

    all_cells = []

    for name, df in dataframes.items():

        cells = set(df["cell_id"])

        print(
            f"{name}: rows={len(df)}, "
            f"unique_cells={len(cells)}"
        )

        if len(df) != EXPECTED_CELLS:
            print(f"WARNING: {name} does not contain {EXPECTED_CELLS} rows.")

        if len(cells) != EXPECTED_CELLS:
            print(f"WARNING: {name} does not contain {EXPECTED_CELLS} unique cells.")

        all_cells.append(cells)

    same_grid = all(
        cells == all_cells[0]
        for cells in all_cells[1:]
    )

    print(f"Same grid across all pairs: {same_grid}")

    # ---------------------------------------------------------
    # 3. Schema check
    # ---------------------------------------------------------
    print("\n[3] SCHEMA CHECK")

    schema_ok = True

    for name, df in dataframes.items():

        if list(df.columns) == EXPECTED_COLUMNS:
            print(f"PASS  {name}: 22-column schema")
        else:
            print(f"FAIL  {name}: column mismatch")
            schema_ok = False

    # ---------------------------------------------------------
    # 4. Duplicate check
    # ---------------------------------------------------------
    print("\n[4] DUPLICATE CHECK")

    duplicates_ok = True

    for name, df in dataframes.items():

        duplicates = df.duplicated(
            subset=["cell_id"]
        ).sum()

        if duplicates == 0:
            print(f"PASS  {name}: no duplicate cell IDs")
        else:
            print(f"FAIL  {name}: {duplicates} duplicate cells")
            duplicates_ok = False

    # ---------------------------------------------------------
    # 5. Numeric data check
    # ---------------------------------------------------------
    print("\n[5] NUMERIC DATA CHECK")

    numeric_columns = [
        "mean_los_disp_m",
        "median_los_disp_m",
        "mean_los_disp_mm",
        "median_los_disp_mm",
        "mean_correlation",
        "valid_pixel_count",
        "total_pixel_count",
        "valid_pixel_percentage",
        "los_displacement_mm",
        "pair_displacement_mm",
    ]

    numeric_ok = True

    for name, df in dataframes.items():

        bad_columns = []

        for column in numeric_columns:

            if not pd.api.types.is_numeric_dtype(df[column]):
                bad_columns.append(column)

        if not bad_columns:
            print(f"PASS  {name}: numeric fields valid")
        else:
            print(f"FAIL  {name}: {bad_columns}")
            numeric_ok = False

    # ---------------------------------------------------------
    # 6. Quality flag check
    # ---------------------------------------------------------
    print("\n[6] QUALITY FLAG CHECK")

    quality_ok = True

    for name, df in dataframes.items():

        invalid = set(df["quality_flag"].dropna()) - ALLOWED_QUALITY

        if not invalid:
            print(f"PASS  {name}: quality flags valid")
        else:
            print(f"FAIL  {name}: unexpected flags {invalid}")
            quality_ok = False

    # ---------------------------------------------------------
    # 7. Observation type check
    # ---------------------------------------------------------
    print("\n[7] OBSERVATION TYPE CHECK")

    for name, df in dataframes.items():

        print(
            f"{name}: "
            f"{df['observation_type'].unique().tolist()}"
        )

    # ---------------------------------------------------------
    # 8. Date and baseline check
    # ---------------------------------------------------------
    print("\n[8] TEMPORAL CHECK")

    temporal_ok = True

    for name, df in dataframes.items():

        ref = pd.to_datetime(df["reference_date"])
        sec = pd.to_datetime(df["secondary_date"])

        calculated_days = (
            sec - ref
        ).dt.days

        if (
            calculated_days
            == df["temporal_baseline_days"]
        ).all():

            print(f"PASS  {name}: temporal baselines correct")

        else:
            print(f"FAIL  {name}: temporal baseline mismatch")
            temporal_ok = False

    # ---------------------------------------------------------
    # 9. Pair summary
    # ---------------------------------------------------------
    print("\n[9] PAIR SUMMARY")

    for name, df in dataframes.items():

        first = df.iloc[0]

        print(
            f"{name}: "
            f"{first['reference_date']} -> "
            f"{first['secondary_date']} | "
            f"{first['temporal_baseline_days']} days | "
            f"{first['pair_id']}"
        )

    # ---------------------------------------------------------
    # FINAL RESULT
    # ---------------------------------------------------------
    print("\n" + "=" * 60)
    print("QC RESULT")
    print("=" * 60)

    if (
        same_grid
        and schema_ok
        and duplicates_ok
        and numeric_ok
        and quality_ok
        and temporal_ok
    ):

        print("PASS: Structural QC completed successfully.")

    else:

        print("REVIEW REQUIRED: One or more QC checks failed.")

    print("\nImportant:")
    print("- This QC checks data structure and consistency.")
    print("- It does NOT prove physical ground stability.")
    print("- It does NOT convert pair displacement into velocity.")
    print("- Final scientific interpretation still requires reference review.")
    print("- Current AOI is still temporary and must be replaced by the")
    print("  authoritative mine boundary before final scientific results.")


if __name__ == "__main__":
    main()
    