from pathlib import Path
import pandas as pd
import hyp3_sdk


# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PAIR_FILE = (
    PROJECT_ROOT
    / "config"
    / "sentinel1_final_pairs.csv"
)

REGISTRY_FILE = (
    PROJECT_ROOT
    / "config"
    / "hyp3_job_registry.csv"
)


# --------------------------------------------------
# HYP3 PROCESSING SETTINGS
# --------------------------------------------------

LOOKS = "20x4"

PHASE_FILTER_PARAMETER = 0.6

INCLUDE_LOOK_VECTORS = True
INCLUDE_INC_MAP = True
INCLUDE_DEM = True
APPLY_WATER_MASK = True
INCLUDE_DISPLACEMENT_MAPS = True


# --------------------------------------------------
# LOAD VALIDATED PAIRS
# --------------------------------------------------

pairs = pd.read_csv(PAIR_FILE)

print("=" * 60)
print("HYP3 NETWORK SUBMISSION")
print("=" * 60)

print(f"Validated network pairs : {len(pairs)}")


# --------------------------------------------------
# LOAD EXISTING REGISTRY
# --------------------------------------------------

if REGISTRY_FILE.exists():

    registry = pd.read_csv(REGISTRY_FILE)

else:

    registry = pd.DataFrame(
        columns=[
            "pair_key",
            "reference_scene",
            "secondary_scene",
            "job_id"
        ]
    )


# Make sure required columns exist
for column in [
    "pair_key",
    "reference_scene",
    "secondary_scene",
    "job_id"
]:

    if column not in registry.columns:
        registry[column] = ""


existing_pairs = set(
    registry["pair_key"]
    .dropna()
    .astype(str)
)


# --------------------------------------------------
# CREATE PAIR KEYS
# --------------------------------------------------

new_pairs = []

for _, row in pairs.iterrows():

    reference_scene = str(row["reference_scene"])
    secondary_scene = str(row["secondary_scene"])

    pair_key = (
        reference_scene
        + "__"
        + secondary_scene
    )

    if pair_key in existing_pairs:

        continue

    new_pairs.append(
        {
            "pair_key": pair_key,
            "reference_scene": reference_scene,
            "secondary_scene": secondary_scene
        }
    )


print(f"Already registered      : {len(pairs) - len(new_pairs)}")
print(f"New pairs to submit     : {len(new_pairs)}")


# --------------------------------------------------
# STOP IF NOTHING NEW
# --------------------------------------------------

if not new_pairs:

    print()
    print("No new HyP3 jobs need to be submitted.")
    print("=" * 60)
    raise SystemExit


# --------------------------------------------------
# CONNECT TO HYP3
# --------------------------------------------------

print()
print("Connecting to HyP3...")

hyp3 = hyp3_sdk.HyP3(prompt="password")

print("HyP3 connection successful.")


# --------------------------------------------------
# SUBMIT JOBS
# --------------------------------------------------

new_registry_rows = []

for index, pair in enumerate(new_pairs, start=1):

    reference_scene = pair["reference_scene"]
    secondary_scene = pair["secondary_scene"]

    print()
    print("-" * 60)
    print(f"[{index}/{len(new_pairs)}]")
    print(f"Reference : {reference_scene}")
    print(f"Secondary : {secondary_scene}")

    try:

        batch = hyp3.submit_insar_job(
            granule1=reference_scene,
            granule2=secondary_scene,
            name="shyamsundarpur-network-insar",
            looks=LOOKS,
            include_look_vectors=INCLUDE_LOOK_VECTORS,
            include_inc_map=INCLUDE_INC_MAP,
            include_dem=INCLUDE_DEM,
            apply_water_mask=APPLY_WATER_MASK,
            include_displacement_maps=INCLUDE_DISPLACEMENT_MAPS,
            phase_filter_parameter=PHASE_FILTER_PARAMETER
        )

        print("Submitted successfully.")

        # HyP3 batch normally contains one job
        for job in batch:

            job_id = getattr(job, "job_id", None)

            if job_id is None:
                job_id = getattr(job, "id", None)

            if job_id is None:
                print("WARNING: Job ID could not be read.")
                continue

            print(f"Job ID : {job_id}")

            new_registry_rows.append(
                {
                    "pair_key": pair["pair_key"],
                    "reference_scene": reference_scene,
                    "secondary_scene": secondary_scene,
                    "job_id": job_id
                }
            )

    except Exception as error:

        print("SUBMISSION FAILED")
        print(error)


# --------------------------------------------------
# UPDATE REGISTRY
# --------------------------------------------------

if new_registry_rows:

    new_registry = pd.DataFrame(new_registry_rows)

    registry = pd.concat(
        [
            registry,
            new_registry
        ],
        ignore_index=True
    )

    registry.to_csv(
        REGISTRY_FILE,
        index=False
    )

    print()
    print("=" * 60)
    print("REGISTRY UPDATED")
    print("=" * 60)
    print(f"New jobs recorded : {len(new_registry_rows)}")
    print(f"Registry          : {REGISTRY_FILE}")

else:

    print()
    print("No new jobs were successfully recorded.")


print()
print("=" * 60)
print("SUBMISSION STAGE COMPLETE")
print("=" * 60)