import hyp3_sdk as sdk

print("=" * 70)
print("                 HYP3 JOB STATUS")
print("=" * 70)

print("\nConnecting to HyP3...")

try:
    hyp3 = sdk.HyP3(
        prompt="password"
    )

    print("HyP3 connection: SUCCESS")

    print("\nSearching for your HyP3 job...")

    jobs = hyp3.find_jobs(
        name="Shyamsundarpur_test_pair_01"
    )

    print("\nJob information:")
    print(jobs)

    print("\n" + "=" * 70)

    if len(jobs) == 0:

        print("No matching job found.")

    else:

        for job in jobs:

            print("\nJob name    :", job.name)
            print("Job ID      :", job.job_id)
            print("Status code :", job.status_code)

            if job.pending():

                print("\n⏳ STATUS: PENDING")
                print("HyP3 has accepted the job.")
                print("It is waiting for processing.")

            elif job.running():

                print("\n🔄 STATUS: RUNNING")
                print("HyP3 is currently processing the InSAR pair.")

            elif job.succeeded():

                print("\n✅ STATUS: SUCCEEDED")
                print("The InSAR product is ready.")

            elif job.failed():

                print("\n❌ STATUS: FAILED")
                print("The HyP3 processing job failed.")

            else:

                print("\nUNKNOWN STATUS")

    print("\n" + "=" * 70)

except Exception as error:

    print("\nERROR:")
    print(error)

print("\n" + "=" * 70)
print("                  STATUS CHECK COMPLETE")
print("=" * 70)