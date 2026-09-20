from pathlib import Path

import hyp3_sdk as sdk


def main():

    print("=" * 70)
    print("             CHECK HYP3 PAIR 02")
    print("=" * 70)

    print("\nConnecting to HyP3...")

    hyp3 = sdk.HyP3(prompt="password")

    print("\nSearching for Pair 02 job...")

    jobs = hyp3.find_jobs(
        name="Shyamsundarpur_pair_02"
    )

    print(f"\nJobs found: {len(jobs)}")

    if len(jobs) == 0:
        print("\nNo job found with this name.")
        return

    for job in jobs:

        print("\n----------------------------------------")
        print(f"Job ID : {job.job_id}")
        print(f"Status : {job.status_code}")

        if hasattr(job, "name"):
            print(f"Name   : {job.name}")

        print("----------------------------------------")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()