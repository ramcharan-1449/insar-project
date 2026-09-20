from pathlib import Path
import subprocess
import sys
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parent


STAGES = [
    (
        "Stage 1 - Sentinel-1 online discovery",
        "src/acquisition/sentinel_search.py",
    ),
    (
        "Stage 2 - Automatic pair selection",
        "src/acquisition/pair_selector.py",
    ),
    (
        "Stage 2.6 - Pair geometry validation",
        "src/acquisition/validate_pair_geometry.py",
    ),
    (
        "Stage 2.7 - Priority pair validation",
        "src/acquisition/validate_priority_pairs.py",
    ),
    (
        "Stage 3 - HyP3 submission",
        "src/hyp3/submit_network_jobs.py",
    ),
    (
        "Stage 4 - HyP3 monitoring and download",
        "src/hyp3/monitor_and_download.py",
    ),
    (
        "Stage 5 - HyP3 extraction and validation",
        "src/hyp3/extract_and_validate.py",
    ),
    (
        "Stage 6 - Spatial feature extraction",
        "src/spatial/extract_grid_features.py",
    ),
    (
        "Stage 13 - Temporal QC",
        "src/temporal/validate_temporal_features.py",
    ),
    (
        "Stage 14 - Temporal observations",
        "src/temporal/build_temporal_observations.py",
    ),
    (
        "Stage 15 - Temporal feature engineering",
        "src/temporal/build_temporal_features_qc.py",
    ),
    (
        "Stage 16 - Final integrity QC",
        "src/temporal/final_dataset_integrity_qc.py",
    ),
    (
        "Stage 17 - Final dataset packaging",
        "src/temporal/build_final_dataset_package.py",
    ),
]


def run_stage(stage_name, script_path):
    print("\n" + "=" * 70)
    print(stage_name)
    print("=" * 70)

    full_path = PROJECT_ROOT / script_path

    if not full_path.exists():
        print(f"ERROR: Script not found:")
        print(full_path)
        return False

    result = subprocess.run(
        [sys.executable, str(full_path)],
        cwd=PROJECT_ROOT,
    )

    if result.returncode != 0:
        print("\n" + "!" * 70)
        print(f"FAILED: {stage_name}")
        print("!" * 70)
        print(f"Exit code: {result.returncode}")
        return False

    print("\n" + "-" * 70)
    print(f"COMPLETED: {stage_name}")
    print("-" * 70)

    return True


def main():

    start_time = datetime.now()

    print("=" * 70)
    print("AUTOMATED INSAR PIPELINE")
    print("=" * 70)
    print(f"Project root : {PROJECT_ROOT}")
    print(f"Started      : {start_time}")
    print("=" * 70)

    completed = []

    for stage_name, script_path in STAGES:

        success = run_stage(
            stage_name,
            script_path,
        )

        if not success:

            print("\n" + "=" * 70)
            print("PIPELINE STOPPED")
            print("=" * 70)

            print("\nCompleted stages:")

            for stage in completed:
                print(f"  PASS - {stage}")

            print(f"\nFailed stage:")
            print(f"  FAIL - {stage_name}")

            sys.exit(1)

        completed.append(stage_name)

    end_time = datetime.now()

    print("\n" + "=" * 70)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 70)

    print(f"Started  : {start_time}")
    print(f"Finished : {end_time}")
    print(f"Stages   : {len(completed)}")

    print("\nCompleted stages:")

    for stage in completed:
        print(f"  PASS - {stage}")

    print("\nFinal dataset:")
    print(
        PROJECT_ROOT
        / "data"
        / "final_dataset"
    )

    print("\nAUTOMATED INSAR PIPELINE COMPLETE.")


if __name__ == "__main__":
    main()