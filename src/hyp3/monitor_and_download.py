
from pathlib import Path
import csv
import time

import hyp3_sdk


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REGISTRY_FILE = PROJECT_ROOT / "config" / "hyp3_job_registry.csv"
DOWNLOAD_DIR = PROJECT_ROOT / "data" / "processed" / "hyp3"


# ============================================================
# SETTINGS
# ============================================================

POLL_SECONDS = 30
MAX_DOWNLOAD_ATTEMPTS = 3


# ============================================================
# REGISTRY FUNCTIONS
# ============================================================

def load_registry():
    """Load all HyP3 jobs from the registry."""

    with open(REGISTRY_FILE, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def save_registry(rows):
    """Save the registry while preserving all existing columns."""

    if not rows:
        return

    fieldnames = list(rows[0].keys())

    with open(REGISTRY_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )

        writer.writeheader()
        writer.writerows(rows)


# ============================================================
# VALUE HELPERS
# ============================================================

def is_true(value):
    """Safely interpret a registry boolean value."""

    return str(value).strip().lower() == "true"


def is_false_or_empty(value):
    """Return True when a value is not explicitly true."""

    return not is_true(value)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("HyP3 Monitor and Download")
    print("=" * 70)

    print(f"Registry : {REGISTRY_FILE}")
    print(f"Jobs     : {len(load_registry())}")
    print(f"Download : {DOWNLOAD_DIR}")
    print()

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # Load registry
    # --------------------------------------------------------

    rows = load_registry()

    if not rows:
        print("No jobs found in registry.")
        return

    # --------------------------------------------------------
    # Validate job IDs
    # --------------------------------------------------------

    missing_job_ids = [
        row for row in rows
        if not str(row.get("job_id", "")).strip()
    ]

    if missing_job_ids:
        print(
            f"ERROR: {len(missing_job_ids)} registry rows "
            "have no job_id."
        )
        return

    # --------------------------------------------------------
    # Connect to HyP3
    # --------------------------------------------------------

    print("Connecting to HyP3...")

    hyp3 = hyp3_sdk.HyP3(prompt="password")

    print("Connected to HyP3.")
    print()

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    succeeded_this_pass = 0
    downloaded_this_pass = 0
    failed_count = 0
    error_count = 0

    # --------------------------------------------------------
    # Process jobs
    # --------------------------------------------------------

    for row in rows:

        job_id = str(row.get("job_id", "")).strip()

        if not job_id:
            continue

        # ====================================================
        # IMPORTANT:
        # Check DOWNLOADED using the HyP3 JOB ID.
        #
        # We DO NOT use Sentinel scene names here.
        # ====================================================

        if is_true(row.get("downloaded", "")):

            print(
                f"{job_id}: already downloaded - SKIP"
            )

            continue

        # ====================================================
        # Fetch this exact HyP3 job
        # ====================================================

        print("-" * 70)
        print(f"Checking HyP3 job: {job_id}")

        try:

            job = hyp3.get_job_by_id(job_id)

        except Exception as exc:

            print(
                f"{job_id}: ERROR while checking job: {exc}"
            )

            error_count += 1
            continue

        # ====================================================
        # STATUS
        # ====================================================

        try:
            if job.failed():

                print(f"{job_id}: FAILED")

                row["status"] = "FAILED"
                failed_count += 1

                save_registry(rows)
                continue

        except Exception:
            pass

        try:
            if job.expired():

                print(f"{job_id}: EXPIRED")

                row["status"] = "EXPIRED"
                failed_count += 1

                save_registry(rows)
                continue

        except Exception:
            pass

        # ----------------------------------------------------
        # Still running?
        # ----------------------------------------------------

        try:

            if job.pending():

                print(f"{job_id}: PENDING")

                row["status"] = "PENDING"

                save_registry(rows)
                continue

        except Exception:
            pass

        try:

            if job.running():

                print(f"{job_id}: RUNNING")

                row["status"] = "RUNNING"

                save_registry(rows)
                continue

        except Exception:
            pass

        # ====================================================
        # SUCCESS
        # ====================================================

        try:

            if not job.succeeded():

                print(
                    f"{job_id}: status not final yet"
                )

                continue

        except Exception as exc:

            print(
                f"{job_id}: unable to determine success: {exc}"
            )

            error_count += 1
            continue

        print(f"{job_id}: SUCCEEDED")

        succeeded_this_pass += 1

        row["status"] = "SUCCEEDED"

        # ====================================================
        # DOWNLOAD
        # ====================================================

        download_success = False

        for attempt in range(
            1,
            MAX_DOWNLOAD_ATTEMPTS + 1
        ):

            print(
                f"{job_id}: downloading "
                f"(attempt {attempt}/{MAX_DOWNLOAD_ATTEMPTS})..."
            )

            try:

                files = job.download_files(
                    location=str(DOWNLOAD_DIR)
                )

                # ------------------------------------------------
                # Convert result to list safely
                # ------------------------------------------------

                files = list(files)

                if not files:

                    print(
                        f"{job_id}: download returned no files."
                    )

                    if attempt < MAX_DOWNLOAD_ATTEMPTS:
                        time.sleep(5)

                    continue

                # ------------------------------------------------
                # Download successful
                # ------------------------------------------------

                print(
                    f"{job_id}: downloaded "
                    f"{len(files)} file(s)"
                )

                # =================================================
                # CRITICAL:
                # Mark THIS JOB ID as downloaded immediately.
                # =================================================

                row["downloaded"] = "true"

                row["download_path"] = str(DOWNLOAD_DIR)

                row["status"] = "SUCCEEDED"

                # ------------------------------------------------
                # Save registry immediately
                # ------------------------------------------------

                save_registry(rows)

                print(
                    f"{job_id}: registry updated as downloaded"
                )

                downloaded_this_pass += 1

                download_success = True

                break

            except Exception as exc:

                print(
                    f"{job_id}: download error: {exc}"
                )

                if attempt < MAX_DOWNLOAD_ATTEMPTS:
                    time.sleep(5)

        # ----------------------------------------------------
        # Download failed after retries
        # ----------------------------------------------------

        if not download_success:

            print(
                f"{job_id}: download failed after "
                f"{MAX_DOWNLOAD_ATTEMPTS} attempts"
            )

            error_count += 1

            row["status"] = "DOWNLOAD_ERROR"

            save_registry(rows)

    # ============================================================
    # FINAL SUMMARY
    # ============================================================

    # Re-read registry from disk.
    #
    # This is intentional.
    # It ensures the summary reflects what was actually saved.
    # ============================================================

    final_rows = load_registry()

    downloaded_total = sum(
        is_true(row.get("downloaded", ""))
        for row in final_rows
    )

    total_jobs = len(final_rows)

    still_processing = sum(
        str(row.get("status", "")).upper()
        in {"PENDING", "RUNNING"}
        for row in final_rows
    )

    failed_total = sum(
        str(row.get("status", "")).upper()
        in {"FAILED", "EXPIRED"}
        for row in final_rows
    )

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(f"Total jobs            : {total_jobs}")
    print(f"Downloaded            : {downloaded_total}")
    print(f"Succeeded this pass   : {succeeded_this_pass}")
    print(f"Downloaded this pass  : {downloaded_this_pass}")
    print(f"Failed                : {failed_total}")
    print(f"Errors                : {error_count}")
    print(f"Still processing      : {still_processing}")

    print()

    if (
        downloaded_total == total_jobs
        and failed_total == 0
        and still_processing == 0
    ):

        print("All HyP3 jobs have reached a final state.")
        print("All jobs completed successfully.")

    elif still_processing > 0:

        print(
            "Some HyP3 jobs are still processing."
        )

        print(
            "Run this monitor again later."
        )

    else:

        print(
            "Monitoring completed with failures or errors."
        )


if __name__ == "__main__":
    main()

