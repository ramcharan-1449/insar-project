from pathlib import Path
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CANDIDATE_FILE = (
    PROJECT_ROOT
    / "config"
    / "sentinel1_connectivity_pairs.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "config"
    / "sentinel1_network_extension_pairs.csv"
)


# ============================================================
# SETTINGS
# ============================================================

# Maximum number of new connections selected per track.
# We deliberately keep this small because these are candidates
# that will later need baseline and geometry validation.

MAX_PER_TRACK = 6


# ============================================================
# HELPERS
# ============================================================

def normalize_date(value):

    return pd.to_datetime(
        value,
        utc=True
    ).strftime("%Y-%m-%d")


def component_count(nodes, edges):

    parent = {
        node: node
        for node in nodes
    }

    def find(node):

        while parent[node] != node:

            parent[node] = parent[parent[node]]
            node = parent[node]

        return node

    def union(a, b):

        root_a = find(a)
        root_b = find(b)

        if root_a != root_b:
            parent[root_b] = root_a
            return True

        return False

    unions = 0

    for a, b in edges:

        if union(a, b):
            unions += 1

    roots = {
        find(node)
        for node in nodes
    }

    return len(roots), unions


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("       TRACK-AWARE TEMPORAL NETWORK SELECTION")
    print("=" * 70)

    # --------------------------------------------------------
    # Load candidates
    # --------------------------------------------------------

    print("\nLoading connectivity candidates...")

    df = pd.read_csv(CANDIDATE_FILE)

    print(
        f"Connectivity candidates : {len(df)}"
    )

    if df.empty:

        raise RuntimeError(
            "No connectivity candidates found."
        )

    # --------------------------------------------------------
    # Normalize dates
    # --------------------------------------------------------

    df["reference_date_norm"] = (
        df["reference_date"]
        .apply(normalize_date)
    )

    df["secondary_date_norm"] = (
        df["secondary_date"]
        .apply(normalize_date)
    )

    # --------------------------------------------------------
    # Check required columns
    # --------------------------------------------------------

    required = [
        "reference_date_norm",
        "secondary_date_norm",
        "orbit_direction",
        "relative_orbit",
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:

        raise RuntimeError(
            "Missing required columns: "
            + ", ".join(missing)
        )

    # --------------------------------------------------------
    # Process each track separately
    # --------------------------------------------------------

    selected_parts = []

    print("\nProcessing tracks...")

    for (direction, orbit), track_df in df.groupby(
        [
            "orbit_direction",
            "relative_orbit"
        ]
    ):

        track_df = track_df.copy()

        print(
            f"\nTrack: {direction} | "
            f"Relative orbit {int(orbit)}"
        )

        print(
            f"  Candidates: {len(track_df)}"
        )

        # ----------------------------------------------------
        # Sort by temporal baseline
        # ----------------------------------------------------

        if "temporal_baseline_days" in track_df.columns:

            track_df = track_df.sort_values(
                by=[
                    "temporal_baseline_days"
                ]
            )

        # ----------------------------------------------------
        # Greedy connectivity selection
        # ----------------------------------------------------

        selected = []

        nodes = set()

        for _, row in track_df.iterrows():

            ref = row["reference_date_norm"]
            sec = row["secondary_date_norm"]

            # Start with the first available edge.

            if not selected:

                selected.append(row)
                nodes.update([ref, sec])

                continue

            # Add a pair when it introduces a new date
            # connected to the current network.

            if (
                (ref in nodes and sec not in nodes)
                or
                (sec in nodes and ref not in nodes)
            ):

                selected.append(row)
                nodes.update([ref, sec])

            if len(selected) >= MAX_PER_TRACK:
                break

        # ----------------------------------------------------
        # Store selected pairs
        # ----------------------------------------------------

        if selected:

            selected_df = pd.DataFrame(
                selected
            )

            selected_df[
                "network_selection"
            ] = "SELECTED_EXTENSION"

            selected_df[
                "network_rank"
            ] = range(
                1,
                len(selected_df) + 1
            )

            selected_parts.append(
                selected_df
            )

            print(
                f"  Selected: {len(selected_df)}"
            )

            for _, row in selected_df.iterrows():

                print(
                    f"    "
                    f"{row['reference_date_norm']} "
                    f"→ "
                    f"{row['secondary_date_norm']}"
                )

        else:

            print(
                "  No suitable extension selected."
            )

    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

    if not selected_parts:

        raise RuntimeError(
            "No network extension pairs selected."
        )

    result = pd.concat(
        selected_parts,
        ignore_index=True
    )

    # --------------------------------------------------------
    # Remove helper columns
    # --------------------------------------------------------

    result = result.drop(
        columns=[
            "reference_date_norm",
            "secondary_date_norm",
        ],
        errors="ignore"
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("TEMPORAL NETWORK SELECTION COMPLETE")
    print("=" * 70)

    print(
        f"\nSelected extension pairs : "
        f"{len(result)}"
    )

    print("\nSelected by track:")

    summary = (
        result
        .groupby(
            [
                "orbit_direction",
                "relative_orbit"
            ]
        )
        .size()
    )

    for (direction, orbit), count in summary.items():

        print(
            f"  {direction} | "
            f"orbit {int(orbit)} : "
            f"{count} pairs"
        )

    print("\nOutput:")
    print(OUTPUT_FILE)

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()