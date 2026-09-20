from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[2]

AOI_FILE = (
    PROJECT_ROOT
    / "config"
    / "mine_aoi_projected.geojson"
)

REFERENCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_reference_qc_test_pair_01.geojson"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_reference_qc_test_pair_01.png"
)


print("=" * 70)
print("             PLOT INSAR REFERENCE QC")
print("=" * 70)


# ------------------------------------------------------------
# Load data
# ------------------------------------------------------------

aoi = gpd.read_file(AOI_FILE)
reference = gpd.read_file(REFERENCE_FILE)

print("\nAOI loaded.")
print(f"AOI CRS: {aoi.crs}")

print("\nReference candidates loaded.")
print(f"Candidate points: {len(reference)}")
print(f"Reference CRS: {reference.crs}")


# ------------------------------------------------------------
# Create plot
# ------------------------------------------------------------

fig, ax = plt.subplots(figsize=(10, 8))

# AOI boundary
aoi.boundary.plot(
    ax=ax,
    linewidth=2
)

# Reference candidate pixels
reference.plot(
    ax=ax,
    column="correlation",
    cmap="viridis",
    markersize=12,
    legend=True,
    legend_kwds={
        "label": "Correlation",
        "shrink": 0.7
    }
)

ax.set_title(
    "Shyamsundarpur InSAR Reference Candidate QC\n"
    "Pair 01 — High-Correlation Pixels"
)

ax.set_xlabel("Easting (m)")
ax.set_ylabel("Northing (m)")

ax.grid(True, alpha=0.3)

plt.tight_layout()

plt.savefig(
    OUTPUT_FILE,
    dpi=200,
    bbox_inches="tight"
)

plt.close()


print("\nOutput:")
print(OUTPUT_FILE)

print("\nIMPORTANT:")
print(
    "This map shows high-correlation reference candidates."
)

print(
    "It does NOT prove physical ground stability."
)

print("=" * 70)