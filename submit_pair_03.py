import hyp3_sdk as hyp3

print("Connecting to HyP3...")
print("Please enter your NASA Earthdata Login credentials.")

hyp3_connection = hyp3.HyP3(prompt="password")

reference_scene = (
    "S1A_IW_SLC__1SDV_20240510T121316_20240510T121343_053809_068A02_58C3"
)

secondary_scene = (
    "S1A_IW_SLC__1SDV_20240603T121315_20240603T121342_054159_069615_B498"
)

print("\nSubmitting Pair 03...")
print("Reference:", reference_scene)
print("Secondary:", secondary_scene)

batch = hyp3_connection.submit_insar_job(
    reference_scene,
    secondary_scene,
    looks="20x4",
    include_dem=True
)

print("\nPair 03 submitted successfully!")
print(batch)