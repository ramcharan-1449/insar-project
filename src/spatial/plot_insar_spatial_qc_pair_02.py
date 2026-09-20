import geopandas as gpd
import matplotlib.pyplot as plt
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

INPUT_FILE = Path(
    "data/processed/grid/"
    "insar_spatial_qc_test_pair_02.geojson"
)

OUTPUT_FILE = Path(
    "data/processed/grid/"
    "insar_spatial_qc_test_pair_02.png"
)


# ============================================================
# LOAD
# ============================================================

gdf = gpd.read_file(INPUT_FILE)

print("=" * 70)
print("             PAIR 02 INSAR SPATIAL QC MAP")
print("=" * 70)

print("\nCells:", len(gdf))
print("CRS:", gdf.crs)


# ============================================================
# PLOT
# ============================================================

fig, ax = plt.subplots(
    figsize=(10, 8)
)

# All grid cells
gdf.plot(
    ax=ax,
    facecolor="lightgray",
    edgecolor="black",
    linewidth=0.3
)

# Valid cells
valid = gdf[
    gdf["quality_flag"] == "VALID"
]

if len(valid) > 0:

    valid.plot(
        ax=ax,
        column="median_los_mm",
        cmap="viridis",
        legend=True,
        edgecolor="black",
        linewidth=0.4
    )


# ============================================================
# TITLE
# ============================================================

ax.set_title(
    "Pair 02 InSAR Spatial QC\n"
    "Referenced LOS Displacement",
    fontsize=14
)

ax.set_xlabel("Easting (m)")
ax.set_ylabel("Northing (m)")

plt.tight_layout()


# ============================================================
# SAVE
# ============================================================

plt.savefig(
    OUTPUT_FILE,
    dpi=200,
    bbox_inches="tight"
)

plt.close()

print("\nOutput:")
print(OUTPUT_FILE)

print("\nVALID cells:", len(valid))

print("\n" + "=" * 70)
print("PAIR 02 QC MAP CREATED")
print("=" * 70)