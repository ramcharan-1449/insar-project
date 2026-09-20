from pathlib import Path
import pandas as pd
import hyp3_sdk


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONFIG_DIR = PROJECT_ROOT / "config"

PAIR_FILE = CONFIG_DIR / "sentinel1_priority_pairs_scientific.csv"
REGISTRY_FILE = CONFIG_DIR / "hyp3_job_registry.csv"


# ============================================================
# HELPERS
# ============================================================

def pair_key(reference_scene, secondary_scene):
    return (
        str(reference_scene).strip(),
        str(secondary_scene).strip()
    )


def load_registry():
    """
    Load the existing HyP3 registry.
    If it does not exist, create an empty registry.
    """

    if not REGISTRY_FILE.exists():
        print("No existing HyP3 registry found.")
        return pd.DataFrame()

    registry = pd.read_csv(REGISTRY_FILE)

    print(f"Existing registry entries: {len(registry)}")

    return registry


def get_registered_pairs(registry):
    """
    Return all reference/secondary scene pairs already registered.
    """

    registered = set()

    if registry.empty:
        return registered

    if (
        "reference_scene" not in registry.columns
        or "secondary_scene" not in registry.columns
    ):
        return registered

    for _, row in registry.iterrows():

        reference = row["reference_scene"]
        secondary = row["secondary_scene"]

        if pd.isna(reference) or pd.isna(secondary):
            continue

        registered.add(
            pair_key(reference, secondary)
        )

    return registered


def save_registry(registry):
    REGISTRY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    registry.to_csv(
        REGISTRY_FILE,
        index=False
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("STAGE 3 — INCREMENTAL HYP3 SUBMISSION")
    print("=" * 70)

    # --------------------------------------------------------
    # Check pair file
    # --------------------------------------------------------

    if not PAIR_FILE.exists():

        print()
        print("ERROR: Priority pair file not found:")
        print(PAIR_FILE)
        return

    pairs = pd.read_csv(PAIR_FILE)

    print()
    print(f"Priority pairs available: {len(pairs)}")

    if pairs.empty:

        print()
        print("No priority pairs available.")
        return

    # --------------------------------------------------------
    # Load existing registry
    # --------------------------------------------------------

    registry = load_registry()

    registered_pairs = get_registered_pairs(registry)

    print(
        f"Already registered pairs: "
        f"{len(registered_pairs)}"
    )

    # --------------------------------------------------------
    # Remove already registered pairs
    # --------------------------------------------------------

    new_pairs = []

    for _, row in pairs.iterrows():

        reference_scene = row["reference_scene"]
        secondary_scene = row["secondary_scene"]

        key = pair_key(
            reference_scene,
            secondary_scene
        )

        if key in registered_pairs:

            print(
                f"SKIP already registered: "
                f"{row['reference_date']} -> "
                f"{row['secondary_date']}"
            )

            continue

        new_pairs.append(row)

    print()
    print(f"New pairs to submit: {len(new_pairs)}")

    # --------------------------------------------------------
    # Nothing new
    # --------------------------------------------------------

    if len(new_pairs) == 0:

        print()
        print("No new HyP3 jobs need to be submitted.")
        print("Existing jobs will not be duplicated.")

        print("=" * 70)

        return

    # --------------------------------------------------------
    # Authenticate with HyP3
    # --------------------------------------------------------

    print()
    print("Connecting to HyP3...")

    try:

        hyp3 = hyp3_sdk.HyP3(
            prompt="password"
        )

        print("HyP3 connection successful.")

    except Exception as e:

        print()
        print("ERROR: HyP3 authentication failed.")
        print(e)
        return

    # --------------------------------------------------------
    # Submit new jobs
    # --------------------------------------------------------

    submitted_count = 0

    for _, row in pd.DataFrame(new_pairs).iterrows():

        reference_scene = str(
            row["reference_scene"]
        ).strip()

        secondary_scene = str(
            row["secondary_scene"]
        ).strip()

        print()
        print("-" * 70)

        print(
            f"Submitting:"
        )

        print(
            f"Reference : {reference_scene}"
        )

        print(
            f"Secondary : {secondary_scene}"
        )

        try:

            batch = hyp3.submit_insar_job(
                reference_scene,
                secondary_scene,

                name="insar_automated",

                include_look_vectors=True,

                include_inc_map=True,

                looks="20x4",

                include_dem=True,

                apply_water_mask=True,

                include_displacement_maps=True,

                phase_filter_parameter=0.6
            )

            # ------------------------------------------------
            # Extract returned job information
            # ------------------------------------------------

            jobs = list(batch)

            if len(jobs) == 0:

                print(
                    "WARNING: HyP3 returned no jobs."
                )

                continue

            for job in jobs:

                job_id = getattr(
                    job,
                    "job_id",
                    None
                )

                if job_id is None:

                    job_id = getattr(
                        job,
                        "id",
                        None
                    )

                if job_id is None:

                    print(
                        "WARNING: Could not determine "
                        "HyP3 job ID."
                    )

                    continue

                # --------------------------------------------
                # Create registry entry
                # --------------------------------------------

                new_entry = {

                    "job_id": str(job_id),

                    "reference_scene":
                        reference_scene,

                    "secondary_scene":
                        secondary_scene,

                    "reference_date":
                        row.get(
                            "reference_date",
                            ""
                        ),

                    "secondary_date":
                        row.get(
                            "secondary_date",
                            ""
                        ),

                    "temporal_baseline_days":
                        row.get(
                            "temporal_baseline_days",
                            ""
                        ),

                    "perpendicular_baseline_m":
                        row.get(
                            "perpendicular_baseline_m",
                            ""
                        ),

                    "orbit_direction":
                        row.get(
                            "orbit_direction",
                            ""
                        ),

                    "relative_orbit":
                        row.get(
                            "relative_orbit",
                            ""
                        ),

                    "quality":
                        row.get(
                            "quality",
                            ""
                        ),

                    "status":
                        "SUBMITTED",

                    "downloaded":
                        False
                }

                registry = pd.concat(
                    [
                        registry,
                        pd.DataFrame(
                            [new_entry]
                        )
                    ],
                    ignore_index=True
                )

                registered_pairs.add(
                    pair_key(
                        reference_scene,
                        secondary_scene
                    )
                )

                submitted_count += 1

                print(
                    f"SUCCESS — HyP3 job: {job_id}"
                )

        except Exception as e:

            print()
            print(
                "ERROR submitting pair:"
            )

            print(e)

    # --------------------------------------------------------
    # Save registry
    # --------------------------------------------------------

    save_registry(registry)

    print()
    print("=" * 70)
    print("STAGE 3 SUBMISSION COMPLETE")
    print("=" * 70)

    print(
        f"New jobs submitted: {submitted_count}"
    )

    print(
        f"Registry entries  : {len(registry)}"
    )

    print()
    print(
        f"Registry saved:"
    )

    print(
        REGISTRY_FILE
    )

    print("=" * 70)


if __name__ == "__main__":
    main()