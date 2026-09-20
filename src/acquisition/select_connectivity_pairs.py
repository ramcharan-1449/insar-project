from pathlib import Path
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CANDIDATE_FILE = (
    PROJECT_ROOT
    / "config"
    / "sentinel1_automatic_pairs.csv"
)

NETWORK_FILE = (
    PROJECT_ROOT
    / "config"
    / "insar_temporal_network.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "config"
    / "sentinel1_connectivity_pairs.csv"
)


# ============================================================
# HELPERS
# ============================================================

def normalize_date(value):
    return pd.to_datetime(
        value,
        utc=True
    ).strftime("%Y-%m-%d")


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("       CONNECTIVITY-AWARE INSAR PAIR SELECTION")
    print("=" * 70)

    # --------------------------------------------------------
    # Load candidates
    # --------------------------------------------------------

    print("\nLoading automatic temporal candidates...")

    candidates = pd.read_csv(CANDIDATE_FILE)

    print(
        f"Candidate pairs : {len(candidates)}"
    )

    # --------------------------------------------------------
    # Load existing network
    # --------------------------------------------------------

    print("\nLoading existing temporal network...")

    network = pd.read_csv(NETWORK_FILE)

    # Existing acquisition dates

    existing_dates = set(
        network["reference_date"]
        .apply(normalize_date)
    )

    existing_dates.update(
        network["secondary_date"]
        .apply(normalize_date)
    )

    print(
        f"Existing dates  : {len(existing_dates)}"
    )

    # --------------------------------------------------------
    # Normalize candidate dates
    # --------------------------------------------------------

    candidates["reference_date_norm"] = (
        candidates["reference_date"]
        .apply(normalize_date)
    )

    candidates["secondary_date_norm"] = (
        candidates["secondary_date"]
        .apply(normalize_date)
    )

    # --------------------------------------------------------
    # Identify useful connections
    # --------------------------------------------------------

    print("\nSearching for pairs that connect existing dates...")

    connectivity_rows = []

    for _, row in candidates.iterrows():

        ref = row["reference_date_norm"]
        sec = row["secondary_date_norm"]

        ref_exists = ref in existing_dates
        sec_exists = sec in existing_dates

        # A pair is useful for connectivity if:
        #
        # one endpoint already exists in the network
        # while the other endpoint is a new acquisition.
        #
        # This extends an existing temporal component.

        if ref_exists != sec_exists:

            row_data = row.to_dict()

            row_data["reference_date_exists"] = ref_exists
            row_data["secondary_date_exists"] = sec_exists
            row_data["connectivity_type"] = (
                "EXTEND_NETWORK"
            )

            connectivity_rows.append(
                row_data
            )

    connectivity_df = pd.DataFrame(
        connectivity_rows
    )

    # --------------------------------------------------------
    # If no direct extensions exist
    # --------------------------------------------------------

    if connectivity_df.empty:

        print(
            "\nNo candidates directly extend "
            "the existing network."
        )

        print(
            "The available candidates may themselves "
            "form new temporal components."
        )

        # Keep all candidates for secondary analysis

        connectivity_df = candidates.copy()

        connectivity_df[
            "connectivity_type"
        ] = "NEW_COMPONENT_CANDIDATE"

    # --------------------------------------------------------
    # Remove helper columns
    # --------------------------------------------------------

    helper_columns = [
        "reference_date_norm",
        "secondary_date_norm",
        "reference_date_exists",
        "secondary_date_exists",
    ]

    for column in helper_columns:

        if column in connectivity_df.columns:

            connectivity_df = connectivity_df.drop(
                columns=column
            )

    # --------------------------------------------------------
    # Rank candidates
    # --------------------------------------------------------

    print("\nRanking connectivity candidates...")

    # Lower perpendicular baseline is preferred.
    # Shorter temporal baseline is preferred.
    #
    # If baseline_score exists, use it directly.

    if "baseline_score" in connectivity_df.columns:

        connectivity_df = connectivity_df.sort_values(
            by=[
                "baseline_score",
                "temporal_baseline_days",
            ]
        )

    elif "perpendicular_baseline_m" in connectivity_df.columns:

        connectivity_df = connectivity_df.sort_values(
            by=[
                "perpendicular_baseline_m",
                "temporal_baseline_days",
            ],
            key=lambda column: column.abs()
        )

    else:

        connectivity_df = connectivity_df.sort_values(
            by="temporal_baseline_days"
        )

    connectivity_df = (
        connectivity_df
        .drop_duplicates(
            subset=[
                "reference_scene",
                "secondary_scene",
            ]
        )
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Assign priority
    # --------------------------------------------------------

    connectivity_df["connectivity_rank"] = (
        range(
            1,
            len(connectivity_df) + 1
        )
    )

    connectivity_df["selection_status"] = (
        "CONNECTIVITY_CANDIDATE"
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    connectivity_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("CONNECTIVITY PAIR SELECTION COMPLETE")
    print("=" * 70)

    print(
        f"\nConnectivity candidates : "
        f"{len(connectivity_df)}"
    )

    if not connectivity_df.empty:

        print("\nTop candidates:")

        display_columns = [
            "reference_date",
            "secondary_date",
            "temporal_baseline_days",
            "perpendicular_baseline_m",
            "orbit_direction",
            "relative_orbit",
            "connectivity_type",
        ]

        available_columns = [
            column
            for column in display_columns
            if column in connectivity_df.columns
        ]

        print(
            connectivity_df[
                available_columns
            ]
            .head(20)
            .to_string(index=False)
        )

    print("\nOutput:")
    print(OUTPUT_FILE)

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()