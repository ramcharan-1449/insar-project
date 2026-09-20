from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import rasterio


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

AOI_FILE = (
    PROJECT_ROOT
    / "config"
    / "mine_aoi_projected.geojson"
)

REFERENCED_LOS_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hyp3"
    / "test_pair_01"
    / "S1AA_20240123T121315_20240204T121314"
    "_referenced_los_disp_aoi.tif"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_referenced_los_qc_test_pair_01.png"
)


# ============================================================
# START
# ============================================================

print("=" * 70)
print("          INSAR REFERENCED LOS SPATIAL QC")
print("=" * 70)


# ------------------------------------------------------------
# Load AOI
# ------------------------------------------------------------

aoi = gpd.read_file(AOI_FILE)

print("\nAOI loaded.")
print(f"AOI CRS: {aoi.crs}")


# ------------------------------------------------------------
# Open referenced LOS raster
# ------------------------------------------------------------

with rasterio.open(REFERENCED_LOS_FILE) as src:

    print("\nReferenced LOS raster loaded.")
    print(f"CRS: {src.crs}")
    print(f"Resolution: {src.res}")
    print(f"Raster size: {src.width} x {src.height}")
    print(f"NoData: {src.nodata}")

    referenced_los = src.read(1)

    bounds = src.bounds


# ------------------------------------------------------------
# Convert metres → millimetres
# ------------------------------------------------------------

referenced_los_mm = referenced_los * 1000.0


# ------------------------------------------------------------
# Calculate statistics
# ------------------------------------------------------------

valid = referenced_los_mm[
    referenced_los_mm == referenced_los_mm
]

print("\nReferenced LOS statistics:")
print(f"Minimum: {valid.min():.3f} mm")
print(f"Maximum: {valid.max():.3f} mm")
print(f"Mean: {valid.mean():.3f} mm")
print(f"Median: {float(__import__('numpy').median(valid)):.3f} mm")
print(f"Std: {valid.std():.3f} mm")


# ------------------------------------------------------------
# Reproject AOI if necessary
# ------------------------------------------------------------

if aoi.crs != src.crs:
    aoi = aoi.to_crs(src.crs)


# ------------------------------------------------------------
# Plot
# ------------------------------------------------------------

fig, ax = plt.subplots(figsize=(10, 8))

image = ax.imshow(
    referenced_los_mm,
    extent=[
        bounds.left,
        bounds.right,
        bounds.bottom,
        bounds.top
    ],
    origin="upper",
    cmap="RdBu_r"
)


# AOI boundary
aoi.boundary.plot(
    ax=ax,
    linewidth=2
)


# Colorbar
colorbar = plt.colorbar(image, ax=ax)

colorbar.set_label(
    "Relative LOS displacement (mm)"
)


# Labels
ax.set_title(
    "Shyamsundarpur InSAR Referenced LOS Displacement QC\n"
    "Pair 01 — 2024-01-23 to 2024-02-04"
)

ax.set_xlabel("Easting (m)")
ax.set_ylabel("Northing (m)")

ax.grid(True, alpha=0.3)


plt.tight_layout()


# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

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
    "This map shows relative LOS displacement after "
    "subtracting the development reference."
)

print(
    "It does not represent absolute ground displacement."
)

print(
    "This is a single 12-day pair and must not be "
    "interpreted as velocity."
)

print("=" * 70)