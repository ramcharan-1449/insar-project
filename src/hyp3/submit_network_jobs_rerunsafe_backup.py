import csv
from pathlib import Path
from datetime import datetime

import hyp3_sdk


# ============================================================
# CONFIGURATION
# ============================================================

BASE = Path(__file__).resolve().parents[2]

INPUT_FILE = BASE / "config" / "sentinel1_final_pairs.csv"
REGISTRY_FILE = BASE / "config" / "hyp3_job_registry.csv"

# HyP3 processing options
LOOKS = "20x4"
PHASE_FILTER_PARAMETER = 0.6


# ============================================================
# HELPERS
# ============================================================

def canonical_pair(reference_scene, secondary_scene):
    """
    Create one unique key for an acquisition pair.
    """
    return (
        str(reference_scene).strip(),
        str(secondary_scene).strip()
    )


def load_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_existing_pairs(path):
    """
    Read the existing HyP3 registry and return all
    acquisition pairs already registered.
    """

    if not path.exists():
        return set()

    rows = load_csv(path)

    existing_pairs = set()

    for row in rows:
        reference_scene = row.get("reference_scene", "").strip()
        secondary_scene = row.get("secondary_scene", "").strip()

        if reference_scene and secondary_scene:
            existing_pairs.add(
                canonical_pair(reference_scene, secondary_scene)
            )

    return existing_pairs


def ensure_registry(path):
    """
    Create the registry if it does not exist.
    """

    if path.exists():
        return

    fieldnames = [
        "job_id",
        "reference_scene",
        "secondary_scene",
        "submitted_at",
        "status",
        "downloaded",
        "download_path"
    ]

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()


def append_registry(path, row):
    """
    Immediately append a newly submitted HyP3 job.
    """

    fieldnames = [
        "job_id",
        "reference_scene",
        "secondary_scene",
        "submitted_at",
        "status",
        "downloaded",
        "download_path"
    ]

    file_exists = path.exists()
    file_empty = not file_exists or path.stat().st_size == 0

    with open(path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )

        if file_empty:
            writer.writeheader()

        writer.writerow(row)


# ============================================================
# LOAD INPUT
# ============================================================

print("=" * 70)
print("HyP3 RERUN-SAFE NETWORK SUBMISSION")
print("=" * 70)

print(f"Input pairs : {INPUT_FILE}")
print(f"Registry    : {REGISTRY_FILE}")

ensure_registry(REGISTRY_FILE)

input_rows = load_csv(INPUT_FILE)

print()
print(f"Input rows: {len(input_rows)}")


# ============================================================
# DEDUPLICATE INPUT PAIRS
# ============================================================

unique_pairs = []
seen_pairs = set()

duplicate_input_count = 0

for row in input_rows:

    reference_scene = row.get("reference_scene", "").strip()
    secondary_scene = row.get("secondary_scene", "").strip()

    if not reference_scene or not secondary_scene:
        continue

    pair_key = canonical_pair(
        reference_scene,
        secondary_scene
    )

    if pair_key in seen_pairs:
        duplicate_input_count += 1
        continue

    seen_pairs.add(pair_key)
    unique_pairs.append(row)


print(f"Unique input pairs: {len(unique_pairs)}")
print(f"Duplicate input pairs removed: {duplicate_input_count}")


# ============================================================
# LOAD EXISTING REGISTRY
# ============================================================

existing_pairs = load_existing_pairs(REGISTRY_FILE)

print(f"Existing registry pairs: {len(existing_pairs)}")


# ============================================================
# DETERMINE NEW PAIRS
# ============================================================

new_pairs = []
already_registered = 0

for row in unique_pairs:

    reference_scene = row["reference_scene"].strip()
    secondary_scene = row["secondary_scene"].strip()

    pair_key = canonical_pair(
        reference_scene,
        secondary_scene
    )

    if pair_key in existing_pairs:
        already_registered += 1
        continue

    new_pairs.append(row)


print(f"Already registered: {already_registered}")
print(f"Genuinely new pairs: {len(new_pairs)}")


# ============================================================
# NOTHING NEW
# ============================================================

if not new_pairs:

    print()
    print("No new acquisition pairs require HyP3 submission.")
    print("Existing HyP3 registry already covers all validated pairs.")
    print()
    print("SUBMISSION STATUS: NOTHING NEW")
    print("=" * 70)

    raise SystemExit(0)


# ============================================================
# CONNECT TO HYP3
# ============================================================

print()
print("Connecting to HyP3...")

hyp3 = hyp3_sdk.HyP3(prompt="password")

print("Connected to HyP3.")


# ============================================================
# SUBMIT NEW PAIRS
# ============================================================

submitted = 0
failed = 0

for index, row in enumerate(new_pairs, start=1):

    reference_scene = row["reference_scene"].strip()
    secondary_scene = row["secondary_scene"].strip()

    print()
    print("-" * 70)
    print(f"Submitting pair {index}/{len(new_pairs)}")
    print(f"Reference : {reference_scene}")
    print(f"Secondary : {secondary_scene}")

    try:

        batch = hyp3.submit_insar_job(
            reference_scene,
            secondary_scene,

            name="insar_automated",

            include_look_vectors=True,
            include_inc_map=True,
            looks=LOOKS,

            include_dem=True,
            apply_water_mask=True,

            include_displacement_maps=True,

            phase_filter_parameter=PHASE_FILTER_PARAMETER
        )

        # The SDK returns a Batch object.
        jobs = list(batch)

        if not jobs:
            raise RuntimeError(
                "HyP3 returned an empty batch."
            )

        submitted_job = jobs[0]

        job_id = str(submitted_job.job_id)

        submitted_at = datetime.utcnow().isoformat()

        append_registry(
            REGISTRY_FILE,
            {
                "job_id": job_id,
                "reference_scene": reference_scene,
                "secondary_scene": secondary_scene,
                "submitted_at": submitted_at,
                "status": "SUBMITTED",
                "downloaded": "false",
                "download_path": ""
            }
        )

        # IMPORTANT:
        # Add the pair immediately so that even if the script
        # continues processing, this pair is considered registered.
        existing_pairs.add(
            canonical_pair(
                reference_scene,
                secondary_scene
            )
        )

        submitted += 1

        print(f"HyP3 job ID: {job_id}")
        print("Registry updated.")
        print("SUBMITTED SUCCESSFULLY")

    except Exception as e:

        failed += 1

        print("SUBMISSION FAILED")
        print(f"Error: {e}")


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 70)
print("SUBMISSION SUMMARY")
print("=" * 70)

print(f"Input pairs                 : {len(input_rows)}")
print(f"Unique input pairs          : {len(unique_pairs)}")
print(f"Input duplicates removed    : {duplicate_input_count}")
print(f"Already registered          : {already_registered}")
print(f"Genuinely new pairs         : {len(new_pairs)}")
print(f"Submitted successfully      : {submitted}")
print(f"Submission failures         : {failed}")

print()
print(f"Registry: {REGISTRY_FILE}")

if failed == 0:
    print()
    print("RERUN-SAFE SUBMISSION COMPLETED.")
else:
    print()
    print("SUBMISSION COMPLETED WITH ERRORS.")

print("=" * 70)