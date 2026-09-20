
from pathlib import Path
import csv
import shutil
from collections import defaultdict


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REGISTRY_FILE = PROJECT_ROOT / "config" / "hyp3_job_registry.csv"
BACKUP_FILE = PROJECT_ROOT / "config" / "hyp3_job_registry_before_dedup.csv"


def main():

    print("=" * 70)
    print("HyP3 Job Registry Deduplication")
    print("=" * 70)

    # ------------------------------------------------------------
    # Load registry
    # ------------------------------------------------------------

    with open(
        REGISTRY_FILE,
        "r",
        encoding="utf-8",
        newline=""
    ) as f:

        rows = list(csv.DictReader(f))

        fieldnames = list(rows[0].keys())

    print(f"Input jobs : {len(rows)}")

    # ------------------------------------------------------------
    # Create backup BEFORE changing anything
    # ------------------------------------------------------------

    shutil.copy2(
        REGISTRY_FILE,
        BACKUP_FILE
    )

    print(f"Backup     : {BACKUP_FILE}")

    # ------------------------------------------------------------
    # Group jobs by exact acquisition pair
    # ------------------------------------------------------------

    groups = defaultdict(list)

    for row in rows:

        reference = row.get(
            "reference_scene",
            ""
        ).strip()

        secondary = row.get(
            "secondary_scene",
            ""
        ).strip()

        pair_key = (
            reference,
            secondary
        )

        groups[pair_key].append(row)

    # ------------------------------------------------------------
    # Deduplicate
    #
    # Keep the FIRST job for every exact pair.
    # ------------------------------------------------------------

    unique_rows = []
    duplicate_rows = []

    for pair_key, pair_rows in groups.items():

        # Keep first job
        unique_rows.append(pair_rows[0])

        # Everything after first is duplicate
        if len(pair_rows) > 1:

            duplicate_rows.extend(
                pair_rows[1:]
            )

            print()
            print("DUPLICATE PAIR")
            print("-" * 70)
            print(
                "Reference:",
                pair_key[0]
            )
            print(
                "Secondary:",
                pair_key[1]
            )

            print(
                "KEEP:",
                pair_rows[0].get("job_id")
            )

            for duplicate in pair_rows[1:]:

                print(
                    "REMOVE:",
                    duplicate.get("job_id")
                )

    # ------------------------------------------------------------
    # Write cleaned registry
    # ------------------------------------------------------------

    with open(
        REGISTRY_FILE,
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(unique_rows)

    # ------------------------------------------------------------
    # Final verification
    # ------------------------------------------------------------

    print()
    print("=" * 70)
    print("RESULT")
    print("=" * 70)

    print(
        f"Original jobs       : {len(rows)}"
    )

    print(
        f"Unique jobs         : {len(unique_rows)}"
    )

    print(
        f"Duplicate jobs removed: {len(duplicate_rows)}"
    )

    # ------------------------------------------------------------
    # Safety check
    # ------------------------------------------------------------

    unique_job_ids = {
        row.get("job_id", "")
        for row in unique_rows
    }

    if len(unique_job_ids) != len(unique_rows):

        print()
        print(
            "ERROR: Duplicate job IDs remain!"
        )

        return

    unique_pairs = {
        (
            row.get("reference_scene", ""),
            row.get("secondary_scene", "")
        )
        for row in unique_rows
    }

    if len(unique_pairs) != len(unique_rows):

        print()
        print(
            "ERROR: Duplicate acquisition pairs remain!"
        )

        return

    print()
    print(
        "All acquisition pairs are now unique."
    )

    print(
        "Original registry backup preserved."
    )

    print()
    print("DEDUPLICATION COMPLETED.")


if __name__ == "__main__":
    main()

