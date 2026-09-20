import hyp3_sdk as hyp3

print("Connecting to HyP3...")

hyp3_client = hyp3.HyP3(prompt="password")

jobs = hyp3_client.find_jobs()

print("\nHyP3 Jobs:")
jobs.print_summary()