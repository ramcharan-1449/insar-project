import hyp3_sdk as sdk
from pathlib import Path

print("=" * 70)
print("              HYP3 PRODUCT DOWNLOAD")
print("=" * 70)

OUTPUT_DIR = Path("data/processed/hyp3")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("\nConnecting to HyP3...")

hyp3 = sdk.HyP3(prompt="password")

print("HyP3 connection: SUCCESS")

print("\nFinding completed job...")

jobs = hyp3.find_jobs(
    name="Shyamsundarpur_test_pair_01"
)

if len(jobs) == 0:
    print("ERROR: HyP3 job not found.")
    raise SystemExit

job = jobs[0]

print("\nJob name :", job.name)
print("Job ID   :", job.job_id)
print("Status   :", job.status_code)

if not job.succeeded():
    print("\nERROR: Job has not succeeded.")
    raise SystemExit

print("\nDownloading HyP3 product...")
print("Output folder:", OUTPUT_DIR)

jobs.download_files(
    location=str(OUTPUT_DIR)
)

print("\n" + "=" * 70)
print("DOWNLOAD COMPLETE")
print("=" * 70)