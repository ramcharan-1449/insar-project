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

LOOKS = "20x4"
PHASE_FILTER_PARAMETER = 0.6


# ============================================================
# PAIR KEY
# ============================================================

def pair_key(reference_scene, secondary_scene):
    return (
        str(reference_scene).strip(),
        str(secondary_scene).strip()
    )


# ============================================================
# CSV HELPERS
# ============================================================

def load_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def save_registry(path, rows):
    """
    Save the registry while preserving its existing columns.
    """

    if not rows:
        return

    fieldnames = list(rows[0].keys())

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)


# ============================================================
# REGISTRY NORMALIZATION
# ============================================================

def normalize_registry(rows):
    """
    Keep exactly one registry row per acquisition pair.

    If historical duplicate rows exist, keep the last row.
    """

    unique = {}

    for row in rows:

        reference = row.get("reference_scene", "").strip()
        secondary = row.get("secondary_scene", "").strip()

        if not reference or not secondary:
            continue

        key = pair_key(reference, secondary)

        unique[key] = row

    return list(unique.values())


# ============================================================
# HYP3 STATUS
# ============================================================

def get_job_status(hyp3, job_id):
    """
    Query the current HyP3 status for one job.
    """

    try:

        job = hyp3.get_job_by_id(job_id)

        if job.succeeded():
            return "SUCCEEDED"

        if job.failed():
            return "FAILED"

        if job.running():
            return "RUNNING"

        if job.pending():
            return "PENDING"

        if job.expired():
            return "EXPIRED"

        return "UNKNOWN"

    except Exception as e:

        print(f"Could not query job {job_id}: {e}")

        return "UNKNOWN"


# ============================================================
# SUBMIT ONE JOB
# ============================================================

def submit_pair(hyp3, reference_scene, secondary_scene):

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

    jobs = list(batch)

    if not jobs:
        raise RuntimeError("HyP3 returned an empty batch.")

    return jobs[0]


# ============================================================
# MAIN
# ============================================================

print("=" * 70)
print("HyP3 FAILURE-AWARE RERUN-SAFE SUBMISSION")
print("=" * 70)

print(f"Input pairs : {INPUT_FILE}")
print(f"Registry    : {REGISTRY_FILE}")


# ------------------------------------------------------------
# Load input pairs
# ------------------------------------------------------------

input_rows = load_csv(INPUT_FILE)

print()
print(f"Input rows: {len(input_rows)}")


# ------------------------------------------------------------
# Remove duplicate input pairs
# ------------------------------------------------------------

unique_input = []
seen = set()

duplicate_input_count = 0

for row in input_rows:

    reference = row.get("reference_scene", "").strip()
    secondary = row.get("secondary_scene", "").strip()

    if not reference or not secondary:
        continue

    key = pair_key(reference, secondary)

    if key in seen:
        duplicate_input_count += 1
        continue

    seen.add(key)
    unique_input.append(row)


print(f"Unique input pairs: {len(unique_input)}")
print(f"Duplicate input pairs removed: {duplicate_input_count}")


# ------------------------------------------------------------
# Load and normalize registry
# ------------------------------------------------------------

if REGISTRY_FILE.exists():
    registry_rows = load_csv(REGISTRY_FILE)
else:
    registry_rows = []


original_registry_count = len(registry_rows)

registry_rows = normalize_registry(registry_rows)

print()
print(f"Registry rows before normalization: {original_registry_count}")
print(f"Unique registry pairs: {len(registry_rows)}")


# ------------------------------------------------------------
# Connect to HyP3
# ------------------------------------------------------------

print()
print("Connecting to HyP3...")

hyp3 = hyp3_sdk.HyP3(prompt="password")

print("Connected to HyP3.")


# ------------------------------------------------------------
# Refresh existing HyP3 statuses
# ------------------------------------------------------------

registry_by_pair = {}

succeeded_count = 0
running_count = 0
pending_count = 0
failed_count = 0
expired_count = 0
unknown_count = 0

print()
print("Checking existing HyP3 jobs...")
print("-" * 70)

for row in registry_rows:

    reference = row.get("reference_scene", "").strip()
    secondary = row.get("secondary_scene", "").strip()
    job_id = row.get("job_id", "").strip()

    if not job_id:
        row["status"] = "UNKNOWN"
        unknown_count += 1

        registry_by_pair[pair_key(reference, secondary)] = row
        continue

    status = get_job_status(hyp3, job_id)

    row["status"] = status

    if status == "SUCCEEDED":
        succeeded_count += 1
    elif status == "RUNNING":
        running_count += 1
    elif status == "PENDING":
        pending_count += 1
    elif status == "FAILED":
        failed_count += 1
    elif status == "EXPIRED":
        expired_count += 1
    else:
        unknown_count += 1

    registry_by_pair[pair_key(reference, secondary)] = row

    print(
        f"{status:10s} | "
        f"{job_id} | "
        f"{reference[-20:]} -> {secondary[-20:]}"
    )


# ------------------------------------------------------------
# Determine what needs submission
# ------------------------------------------------------------

new_pairs = []
retry_pairs = []

already_succeeded = 0
already_processing = 0
already_unknown = 0

for row in unique_input:

    reference = row["reference_scene"].strip()
    secondary = row["secondary_scene"].strip()

    key = pair_key(reference, secondary)

    if key not in registry_by_pair:

        new_pairs.append(row)
        continue

    existing = registry_by_pair[key]
    status = existing.get("status", "UNKNOWN")

    if status == "SUCCEEDED":
        already_succeeded += 1

    elif status in ("RUNNING", "PENDING"):
        already_processing += 1

    elif status in ("FAILED", "EXPIRED"):
        retry_pairs.append(existing)

    else:
        already_unknown += 1


# ------------------------------------------------------------
# Summary before submission
# ------------------------------------------------------------

print()
print("=" * 70)
print("PAIR DECISION SUMMARY")
print("=" * 70)

print(f"New pairs                    : {len(new_pairs)}")
print(f"Already succeeded            : {already_succeeded}")
print(f"Already processing           : {already_processing}")
print(f"Failed/expired - retry      : {len(retry_pairs)}")
print(f"Unknown status               : {already_unknown}")


# ------------------------------------------------------------
# Submit genuinely new pairs
# ------------------------------------------------------------

submitted_new = 0
submitted_retry = 0
submission_failures = 0


for row in new_pairs:

    reference = row["reference_scene"].strip()
    secondary = row["secondary_scene"].strip()

    print()
    print("-" * 70)
    print("Submitting NEW pair")
    print(f"Reference : {reference}")
    print(f"Secondary : {secondary}")

    try:

        job = submit_pair(
            hyp3,
            reference,
            secondary
        )

        job_id = str(job.job_id)

        new_row = {
            "job_id": job_id,
            "reference_scene": reference,
            "secondary_scene": secondary,
            "submitted_at": datetime.utcnow().isoformat(),
            "status": "SUBMITTED",
            "downloaded": "false",
            "download_path": ""
        }

        registry_rows.append(new_row)

        registry_by_pair[
            pair_key(reference, secondary)
        ] = new_row

        submitted_new += 1

        print(f"HyP3 job ID: {job_id}")
        print("NEW PAIR SUBMITTED")

    except Exception as e:

        submission_failures += 1

        print("SUBMISSION FAILED")
        print(f"Error: {e}")


# ------------------------------------------------------------
# Retry failed/expired pairs
# ------------------------------------------------------------

for old_row in retry_pairs:

    reference = old_row["reference_scene"].strip()
    secondary = old_row["secondary_scene"].strip()
    old_job_id = old_row.get("job_id", "").strip()

    print()
    print("-" * 70)
    print("Retrying failed/expired pair")
    print(f"Old job ID : {old_job_id}")
    print(f"Reference  : {reference}")
    print(f"Secondary  : {secondary}")

    try:

        job = submit_pair(
            hyp3,
            reference,
            secondary
        )

        new_job_id = str(job.job_id)

        # Update the existing registry row rather than
        # creating another acquisition-pair row.
        old_row["job_id"] = new_job_id
        old_row["submitted_at"] = datetime.utcnow().isoformat()
        old_row["status"] = "SUBMITTED"
        old_row["downloaded"] = "false"
        old_row["download_path"] = ""

        submitted_retry += 1

        print(f"New HyP3 job ID: {new_job_id}")
        print("RETRY SUBMITTED")

    except Exception as e:

        submission_failures += 1

        print("RETRY FAILED")
        print(f"Error: {e}")


# ------------------------------------------------------------
# Save registry
# ------------------------------------------------------------

save_registry(
    REGISTRY_FILE,
    registry_rows
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print("=" * 70)
print("FINAL SUBMISSION SUMMARY")
print("=" * 70)

print(f"Input pairs                 : {len(input_rows)}")
print(f"Unique input pairs          : {len(unique_input)}")
print(f"Input duplicates removed    : {duplicate_input_count}")

print()
print("Existing registry:")
print(f"  Succeeded                 : {succeeded_count}")
print(f"  Running                   : {running_count}")
print(f"  Pending                   : {pending_count}")
print(f"  Failed                    : {failed_count}")
print(f"  Expired                   : {expired_count}")
print(f"  Unknown                   : {unknown_count}")

print()
print(f"New jobs submitted          : {submitted_new}")
print(f"Failed jobs retried         : {submitted_retry}")
print(f"Submission failures         : {submission_failures}")

print()
print(f"Registry: {REGISTRY_FILE}")

print()
if submission_failures == 0:
    print("RERUN-SAFE SUBMISSION COMPLETED.")
else:
    print("SUBMISSION COMPLETED WITH ERRORS.")

print("=" * 70)