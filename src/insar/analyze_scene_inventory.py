import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CSV_FILE = PROJECT_ROOT / "config" / "sentinel1_scene_inventory.csv"

print("=" * 70)
print("       SENTINEL-1 SCENE INVENTORY ANALYSIS")
print("=" * 70)

print("\nLoading inventory:")
print(CSV_FILE)

df = pd.read_csv(CSV_FILE)

print("\nTotal scenes:", len(df))

# ---------------------------------------------------------
# 1. Orbit direction
# ---------------------------------------------------------

print("\n" + "-" * 70)
print("1. SCENES BY ORBIT DIRECTION")
print("-" * 70)

print(df["orbit_direction"].value_counts())

# ---------------------------------------------------------
# 2. Relative orbit
# ---------------------------------------------------------

print("\n" + "-" * 70)
print("2. SCENES BY RELATIVE ORBIT")
print("-" * 70)

print(df["relative_orbit"].value_counts().sort_index())

# ---------------------------------------------------------
# 3. Orbit direction + relative orbit
# ---------------------------------------------------------

print("\n" + "-" * 70)
print("3. ORBIT DIRECTION + RELATIVE ORBIT")
print("-" * 70)

orbit_summary = (
    df.groupby(["orbit_direction", "relative_orbit"])
    .size()
    .reset_index(name="scene_count")
)

print(orbit_summary.to_string(index=False))

# ---------------------------------------------------------
# 4. Polarization
# ---------------------------------------------------------

print("\n" + "-" * 70)
print("4. POLARIZATION")
print("-" * 70)

print(df["polarization"].value_counts())

# ---------------------------------------------------------
# 5. Product type
# ---------------------------------------------------------

print("\n" + "-" * 70)
print("5. PRODUCT TYPE")
print("-" * 70)

print(df["product_type"].value_counts())

# ---------------------------------------------------------
# 6. Date range
# ---------------------------------------------------------

df["acquisition_date"] = pd.to_datetime(df["acquisition_date"])

print("\n" + "-" * 70)
print("6. ACQUISITION DATE RANGE")
print("-" * 70)

print("Earliest scene:", df["acquisition_date"].min())
print("Latest scene  :", df["acquisition_date"].max())

# ---------------------------------------------------------
# 7. Detailed list
# ---------------------------------------------------------

print("\n" + "-" * 70)
print("7. SCENES SORTED BY DATE")
print("-" * 70)

sorted_df = df.sort_values("acquisition_date")

print(
    sorted_df[
        [
            "scene_id",
            "acquisition_date",
            "orbit_direction",
            "relative_orbit",
            "polarization"
        ]
    ].to_string(index=False)
)

print("\n" + "=" * 70)
print("                 ANALYSIS COMPLETE")
print("=" * 70)