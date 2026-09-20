from pathlib import Path
import subprocess
import sys
from datetime import datetime


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent


# ============================================================
# PIPELINE STAGES
# ============================================================

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
        "Stage 3 - Google Earth Engine setup",
        "src/gee/gee_setup.py",
    ),

    (
        "Stage 4 - Rerun-safe HyP3 submission",
        "src/hyp3/submit_network_jobs.py",
    ),

    (
        "Stage 5 - HyP3 monitoring and download",
        "src/hyp3/monitor_and_download.py",
    ),

    (
        "Stage 6 - Unique HyP3 product extraction",
        "src/hyp3/extract_unique_products.py",
    ),

    (
        "Stage 7 - Create canonical 80 m mine grid",
        "src/spatial/create_mine_grid.py",
    ),

    (
        "Stage 8 - Validate canonical mine grid",
        "src/spatial/validate_mine_grid.py",
    ),

    (
        "Stage 9 - Validate reference decision",
        "src/reference/validate_reference_decision.py",
    ),

    (
        "Stage 10 - Spatial feature extraction",
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


# ============================================================
# RUN ONE STAGE
# ============================================================

def run_stage(stage_number, stage_name, script_path):

    print("\n")
    print("=" * 70)
    print(f"STAGE {stage_number}")
    print(stage_name)
    print("=" * 70)

    full_path = PROJECT_ROOT / script_path

    print(f"Script: {full_path}")

    # --------------------------------------------------------
    # Check script exists
    # --------------------------------------------------------

    if not full_path.exists():

        print()
        print("ERROR: Script not found.")
        print(full_path)

        return False

    # --------------------------------------------------------
    # Execute stage
    # --------------------------------------------------------

    start = datetime.now()

    print(f"Started: {start}")
    print()

    result = subprocess.run(
        [sys.executable, str(full_path)],
        cwd=PROJECT_ROOT,
    )

    end = datetime.now()

    # --------------------------------------------------------
    # Failure
    # --------------------------------------------------------

    if result.returncode != 0:

        print()
        print("!" * 70)
        print(f"FAILED: {stage_name}")
        print("!" * 70)

        print(f"Exit code : {result.returncode}")
        print(f"Finished  : {end}")

        return False

    # --------------------------------------------------------
    # Success
    # --------------------------------------------------------

    duration = end - start

    print()
    print("-" * 70)
    print(f"COMPLETED: {stage_name}")
    print(f"Duration  : {duration}")
    print("-" * 70)

    return True


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():

    pipeline_start = datetime.now()

    print()
    print("=" * 70)
    print("AUTOMATED INSAR DATA PRODUCTION PIPELINE")
    print("=" * 70)

    print(f"Project root : {PROJECT_ROOT}")
    print(f"Started      : {pipeline_start}")

    print()
    print("Pipeline stages:")
    
    for index, (stage_name, script_path) in enumerate(STAGES, start=1):
        print(f"  {index:02d}. {stage_name}")

    print("=" * 70)


    # --------------------------------------------------------
    # Run stages
    # --------------------------------------------------------

    completed = []

    for index, (stage_name, script_path) in enumerate(STAGES, start=1):

        success = run_stage(
            index,
            stage_name,
            script_path,
        )

        if not success:

            print()
            print("=" * 70)
            print("PIPELINE STOPPED")
            print("=" * 70)

            print()
            print("Completed stages:")

            for stage in completed:
                print(f"  PASS - {stage}")

            print()
            print("Failed stage:")
            print(f"  FAIL - {stage_name}")

            print()
            print("The pipeline stopped to prevent downstream processing")
            print("from using incomplete or invalid data.")

            sys.exit(1)

        completed.append(stage_name)


    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    pipeline_end = datetime.now()

    duration = pipeline_end - pipeline_start

    print()
    print("=" * 70)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 70)

    print(f"Started  : {pipeline_start}")
    print(f"Finished : {pipeline_end}")
    print(f"Duration : {duration}")
    print(f"Stages   : {len(completed)}")

    print()
    print("Completed stages:")

    for index, stage in enumerate(completed, start=1):
        print(f"  PASS - {index:02d} - {stage}")

    # --------------------------------------------------------
    # Final dataset
    # --------------------------------------------------------

    final_dataset = (
        PROJECT_ROOT
        / "data"
        / "final_dataset"
    )

    print()
    print("Final dataset:")
    print(final_dataset)

    # --------------------------------------------------------
    # Verify final package
    # --------------------------------------------------------

    required_files = [
        "insar_observations.csv",
        "insar_temporal_features.csv",
        "insar_spatial_features.csv",
        "grid.geojson",
        "dataset_metadata.json",
        "README.md",
    ]

    print()
    print("Final package verification:")

    package_ok = True

    for filename in required_files:

        path = final_dataset / filename

        if path.exists():

            print(f"  OK   {filename}")

        else:

            print(f"  FAIL {filename}")
            package_ok = False

    print()

    if not package_ok:

        print("=" * 70)
        print("WARNING: FINAL PACKAGE IS INCOMPLETE")
        print("=" * 70)

        sys.exit(1)


    print("=" * 70)
    print("FINAL PACKAGE VERIFIED")
    print("=" * 70)

    print()
    print("AUTOMATED INSAR PIPELINE COMPLETE.")
    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
