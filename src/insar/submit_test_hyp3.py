import hyp3_sdk as sdk

print("=" * 70)
print("              HYP3 TEST INSAR SUBMISSION")
print("=" * 70)

# ---------------------------------------------------------
# TEST PAIR #1
# Older scene = reference
# Newer scene = secondary
# ---------------------------------------------------------

REFERENCE_SCENE = (
    "S1A_IW_SLC__1SDV_20240123T121315_20240123T121341_"
    "052234_065093_F3A2"
)

SECONDARY_SCENE = (
    "S1A_IW_SLC__1SDV_20240204T121314_20240204T121341_"
    "052409_06567F_3AFD"
)

JOB_NAME = "Shyamsundarpur_test_pair_01"

print("\nConnecting to HyP3...")

try:
    hyp3 = sdk.HyP3(
        prompt="password"
    )

    print("HyP3 connection: SUCCESS")

    print("\nSubmitting InSAR job...")
    print("Reference :", REFERENCE_SCENE)
    print("Secondary :", SECONDARY_SCENE)
    print("Job name  :", JOB_NAME)

    jobs = hyp3.submit_insar_job(
        REFERENCE_SCENE,
        SECONDARY_SCENE,
        name=JOB_NAME,

        # Useful outputs for our first inspection
        include_displacement_maps=True,
        include_inc_map=True,
        include_look_vectors=True
    )

    print("\n" + "=" * 70)
    print("              JOB SUBMITTED SUCCESSFULLY")
    print("=" * 70)

    print("\nHyP3 Job Information:")
    print(jobs)

    print("\nIMPORTANT:")
    print("The job is now submitted to HyP3.")
    print("Processing may take some time.")
    print("Do NOT submit the remaining pairs yet.")

except Exception as error:

    print("\n" + "=" * 70)
    print("                    ERROR")
    print("=" * 70)

    print(error)

print("\n" + "=" * 70)
print("                  SUBMISSION COMPLETE")
print("=" * 70)