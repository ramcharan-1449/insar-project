from pathlib import Path
import csv
from collections import defaultdict, deque
from datetime import datetime


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

FINAL_PAIRS = (
    PROJECT_ROOT
    / "config"
    / "sentinel1_final_pairs_geometry_validated.csv"
)

NETWORK_PAIRS = (
    PROJECT_ROOT
    / "config"
    / "sentinel1_network_pairs_validated.csv"
)

OUTPUT_NETWORK = (
    PROJECT_ROOT
    / "config"
    / "insar_temporal_network.csv"
)

OUTPUT_REPORT = (
    PROJECT_ROOT
    / "config"
    / "insar_temporal_network_report.txt"
)


# ============================================================
# DEVELOPMENT PAIRS
# ============================================================

DEVELOPMENT_PAIRS = [
    {
        "reference_date": "2024-01-23",
        "secondary_date": "2024-02-04",
        "source": "DEVELOPMENT"
    },
    {
        "reference_date": "2024-05-10",
        "secondary_date": "2024-06-03",
        "source": "DEVELOPMENT"
    },
    {
        "reference_date": "2024-06-03",
        "secondary_date": "2024-06-15",
        "source": "DEVELOPMENT"
    }
]


# ============================================================
# HELPERS
# ============================================================

def parse_date(value):
    """Convert YYYY-MM-DD to datetime."""

    return datetime.strptime(
        value,
        "%Y-%m-%d"
    )


def normalize_date(value):
    """
    Convert possible date/time strings to YYYY-MM-DD.
    """

    value = value.strip()

    if "T" in value:
        value = value.split("T")[0]

    if len(value) == 8 and value.isdigit():
        return (
            f"{value[0:4]}-"
            f"{value[4:6]}-"
            f"{value[6:8]}"
        )

    return value


def read_pair_file(path, source):

    pairs = []

    if not path.exists():

        print(f"WARNING: File not found: {path}")
        return pairs

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            reference = (
                row.get("reference_date")
                or row.get("referenceDate")
                or row.get("reference")
            )

            secondary = (
                row.get("secondary_date")
                or row.get("secondaryDate")
                or row.get("secondary")
            )

            if not reference or not secondary:
                continue

            reference = normalize_date(reference)
            secondary = normalize_date(secondary)

            pairs.append({
                "reference_date": reference,
                "secondary_date": secondary,
                "source": source
            })

    return pairs


# ============================================================
# BUILD NETWORK
# ============================================================

def build_network(pairs):

    adjacency = defaultdict(set)

    for pair in pairs:

        ref = pair["reference_date"]
        sec = pair["secondary_date"]

        adjacency[ref].add(sec)
        adjacency[sec].add(ref)

    return adjacency


# ============================================================
# FIND CONNECTED COMPONENTS
# ============================================================

def find_components(adjacency):

    visited = set()
    components = []

    for start in sorted(adjacency):

        if start in visited:
            continue

        component = []

        queue = deque([start])
        visited.add(start)

        while queue:

            current = queue.popleft()

            component.append(current)

            for neighbor in adjacency[current]:

                if neighbor not in visited:

                    visited.add(neighbor)
                    queue.append(neighbor)

        components.append(
            sorted(component)
        )

    return sorted(
        components,
        key=lambda x: (
            -len(x),
            x[0]
        )
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("       COMPLETE INSAR TEMPORAL NETWORK VALIDATION")
    print("=" * 70)

    # --------------------------------------------------------
    # LOAD ORIGINAL AUTOMATED PAIRS
    # --------------------------------------------------------

    print()
    print("Loading validated automated pairs...")

    automated_pairs = read_pair_file(
        FINAL_PAIRS,
        "AUTOMATED"
    )

    print(
        f"Validated automated pairs : "
        f"{len(automated_pairs)}"
    )

    # --------------------------------------------------------
    # LOAD NETWORK EXTENSION
    # --------------------------------------------------------

    print()
    print("Loading network-extension pairs...")

    network_pairs = read_pair_file(
        NETWORK_PAIRS,
        "NETWORK_EXTENSION"
    )

    print(
        f"Network extension pairs   : "
        f"{len(network_pairs)}"
    )

    # --------------------------------------------------------
    # DEVELOPMENT PAIRS
    # --------------------------------------------------------

    print()
    print("Adding development pairs...")

    development_pairs = []

    for pair in DEVELOPMENT_PAIRS:

        development_pairs.append({
            "reference_date": pair["reference_date"],
            "secondary_date": pair["secondary_date"],
            "source": pair["source"]
        })

    print(
        f"Development pairs         : "
        f"{len(development_pairs)}"
    )

    # --------------------------------------------------------
    # COMBINE
    # --------------------------------------------------------

    all_pairs = (
        automated_pairs
        + network_pairs
        + development_pairs
    )

    # --------------------------------------------------------
    # REMOVE EXACT DUPLICATE PAIRS
    # --------------------------------------------------------

    unique_pairs = []
    seen = set()

    for pair in all_pairs:

        key = (
            pair["reference_date"],
            pair["secondary_date"]
        )

        if key in seen:
            continue

        seen.add(key)
        unique_pairs.append(pair)

    print()
    print(
        f"Total pair records         : "
        f"{len(all_pairs)}"
    )

    print(
        f"Unique temporal pairs      : "
        f"{len(unique_pairs)}"
    )

    # --------------------------------------------------------
    # BUILD NETWORK
    # --------------------------------------------------------

    print()
    print("Building complete temporal network...")

    adjacency = build_network(
        unique_pairs
    )

    components = find_components(
        adjacency
    )

    # --------------------------------------------------------
    # STATISTICS
    # --------------------------------------------------------

    unique_dates = sorted(
        adjacency.keys()
    )

    largest_component = (
        max(
            components,
            key=len
        )
        if components
        else []
    )

    isolated_dates = [
        date
        for date in unique_dates
        if len(adjacency[date]) == 1
    ]

    # --------------------------------------------------------
    # SAVE NETWORK CSV
    # --------------------------------------------------------

    with open(
        OUTPUT_NETWORK,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "reference_date",
                "secondary_date",
                "source",
                "component_id"
            ]
        )

        writer.writeheader()

        # Map dates to components

        date_to_component = {}

        for index, component in enumerate(
            components,
            start=1
        ):

            for date in component:

                date_to_component[date] = index

        for pair in unique_pairs:

            writer.writerow({
                "reference_date":
                    pair["reference_date"],

                "secondary_date":
                    pair["secondary_date"],

                "source":
                    pair["source"],

                "component_id":
                    date_to_component[
                        pair["reference_date"]
                    ]
            })

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    report_lines = []

    report_lines.append(
        "COMPLETE INSAR TEMPORAL NETWORK VALIDATION"
    )

    report_lines.append("=" * 60)

    report_lines.append(
        f"Original automated pairs : "
        f"{len(automated_pairs)}"
    )

    report_lines.append(
        f"Network extension pairs  : "
        f"{len(network_pairs)}"
    )

    report_lines.append(
        f"Development pairs        : "
        f"{len(development_pairs)}"
    )

    report_lines.append(
        f"Unique temporal pairs    : "
        f"{len(unique_pairs)}"
    )

    report_lines.append(
        f"Unique acquisition dates : "
        f"{len(unique_dates)}"
    )

    report_lines.append(
        f"Connected components      : "
        f"{len(components)}"
    )

    report_lines.append(
        f"Largest component        : "
        f"{len(largest_component)} dates"
    )

    report_lines.append(
        f"Isolated dates           : "
        f"{len(isolated_dates)}"
    )

    report_lines.append("")
    report_lines.append("COMPONENTS")
    report_lines.append("-" * 60)

    for index, component in enumerate(
        components,
        start=1
    ):

        report_lines.append(
            f"Component {index}: "
            f"{len(component)} dates"
        )

        report_lines.append(
            "  " + " → ".join(component)
        )

    with open(
        OUTPUT_REPORT,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(report_lines)
        )

    # --------------------------------------------------------
    # CONSOLE OUTPUT
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("TEMPORAL NETWORK VALIDATION COMPLETE")
    print("=" * 70)

    print(
        f"Pair records          : "
        f"{len(unique_pairs)}"
    )

    print(
        f"Unique dates          : "
        f"{len(unique_dates)}"
    )

    print(
        f"Connected components  : "
        f"{len(components)}"
    )

    print(
        f"Largest component     : "
        f"{len(largest_component)} dates"
    )

    print(
        f"Isolated dates        : "
        f"{len(isolated_dates)}"
    )

    print()
    print("Components:")

    for index, component in enumerate(
        components,
        start=1
    ):

        print(
            f"  Component {index}: "
            f"{len(component)} dates"
        )

        print(
            "    "
            + " → ".join(component)
        )

    print()
    print("Network file:")
    print(OUTPUT_NETWORK)

    print()
    print("Report:")
    print(OUTPUT_REPORT)

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()