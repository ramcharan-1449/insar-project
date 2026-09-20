from pathlib import Path
import pandas as pd
import hyp3_sdk as sdk


# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PAIR_FILE = (
    PROJECT_ROOT
    / "config"
    / "sentinel1_final_pairs_normalized.csv"
)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print("=" * 70)
    print("             SUBMIT HYP3 PAIR 02")
    print("=" * 70)

    # -----------------------------------------------------
    # LOAD NORMALIZED PAIRS
    # -----------------------------------------------------

    pairs = pd.read_csv(PAIR_FILE)

    if len(pairs) < 2:
        raise ValueError("Pair 02 was not found.")

    # Pair 02 = second row
    pair = pairs.iloc[1]

    reference_scene = pair["reference_scene"]
    secondary_scene = pair["secondary_scene"]

    print("\nPair information:")

    print(f"Reference date : {pair['reference_date']}")
    print(f"Secondary date : {pair['secondary_date']}")
    print(f"Orbit direction: {pair['orbit_direction']}")
    print(f"Relative orbit : {pair['relative_orbit']}")
    print(
        f"Temporal baseline: "
        f"{pair['temporal_baseline_days']} days"
    )
    print(
        f"Perpendicular baseline: "
        f"{pair['perpendicular_baseline_m']} m"
    )

    print("\nReference scene:")
    print(reference_scene)

    print("\nSecondary scene:")
    print(secondary_scene)

    # -----------------------------------------------------
    # CONNECT TO HYP3
    # -----------------------------------------------------

    print("\nConnecting to HyP3...")

    hyp3 = sdk.HyP3(prompt="password")

    credits = hyp3.check_credits()

    print(f"Available credits: {credits}")

    # -----------------------------------------------------
    # SUBMIT JOB
    # -----------------------------------------------------

    print("\nSubmitting Pair 02...")

    job = hyp3.submit_insar_job(
    reference_scene,
    secondary_scene,
    include_displacement_maps=True,
    include_inc_map=True,
    include_look_vectors=True,
)

    # -----------------------------------------------------
    # JOB INFORMATION
    # -----------------------------------------------------

    print("\nHyP3 job submitted successfully.")

    print(f"Job name : {job.name}")
    print(f"Job ID   : {job.job_id}")
    print(f"Status   : {job.status_code}")

    print("\nIMPORTANT:")
    print("Save the Job ID above for status checking.")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
