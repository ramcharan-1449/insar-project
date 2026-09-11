import geopandas as gpd
from pathlib import Path

SOURCE = Path(
    "data/raw/aoi_source/Shyamsundarpur_boundary.geojson"
)

OUTPUT = Path(
    "config/mine_aoi.geojson"
)

print("=" * 50)
print("CREATING FINAL AOI")
print("=" * 50)

# Read source boundary
aoi = gpd.read_file(SOURCE)

print("\nSource loaded.")
print("Features:", len(aoi))
print("Original CRS:", aoi.crs)

# Convert to WGS84
aoi = aoi.to_crs("EPSG:4326")

# Keep only geometry
aoi = aoi[["geometry"]]

# Remove invalid geometries
aoi = aoi[aoi.geometry.is_valid]

# Save final AOI
aoi.to_file(
    OUTPUT,
    driver="GeoJSON"
)

print("\nFinal AOI created:")
print(OUTPUT)

print("\nFinal CRS:")
print(aoi.crs)

print("\nFinal bounds:")
print(aoi.total_bounds)

print("\nSTATUS:")
print("ASSUMED AOI — NOT FOR FINAL SCIENTIFIC ANALYSIS")