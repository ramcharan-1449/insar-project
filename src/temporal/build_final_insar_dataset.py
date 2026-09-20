import pandas as pd
from pathlib import Path

BASE = Path("data/processed/grid")

FILES = [
    BASE / "standardized_test_pair_01.csv",
    BASE / "standardized_test_pair_03.csv",
    BASE / "standardized_test_pair_02.csv",
]

OUTPUT = BASE / "final_insar_dataset.csv"


def main():
    print("Checking InSAR pair files...\n")

    available = []

    for file in FILES:
        if file.exists():
            print(f"FOUND: {file}")
            df = pd.read_csv(file)
            print(f"       Rows: {len(df)}")
            available.append(df)
        else:
            print(f"NOT READY: {file}")

    print()

    if len(available) < 3:
        print("Pair 03 is not ready yet.")
        print("Final dataset will be created after all 3 pairs are available.")
        return

    # Check column compatibility
    columns = list(available[0].columns)

    for i, df in enumerate(available[1:], start=2):
        if list(df.columns) != columns:
            raise ValueError(
                f"Column mismatch between pair 1 and pair {i}"
            )

    # Check cell IDs
    cell_sets = [set(df["cell_id"]) for df in available]

    if not all(cell_set == cell_sets[0] for cell_set in cell_sets[1:]):
        raise ValueError("Grid cell IDs are not identical across all pairs.")

    print("All 3 pairs have:")
    print("  - Same columns")
    print("  - Same column order")
    print("  - Same cell IDs")

    # Combine observations
    final_df = pd.concat(available, ignore_index=True)

    # Sort by cell and observation date
    final_df = final_df.sort_values(
        ["cell_id", "observation_mid_date"]
    ).reset_index(drop=True)

    final_df.to_csv(OUTPUT, index=False)

    print("\nFinal dataset created:")
    print(OUTPUT)
    print(f"Rows: {len(final_df)}")
    print(f"Columns: {len(final_df.columns)}")
    print(f"Unique cells: {final_df['cell_id'].nunique()}")
    print(f"Unique pairs: {final_df['pair_id'].nunique()}")

    print("\nPair counts:")
    print(final_df["pair_id"].value_counts().sort_index())

    print("\nObservation dates:")
    print(
        final_df[
            ["pair_id", "reference_date", "secondary_date"]
        ].drop_duplicates().sort_values("reference_date").to_string(index=False)
    )


if __name__ == "__main__":
    main()