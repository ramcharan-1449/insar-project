import geopandas as gpd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "config" / "mine_aoi.geojson"
OUTPUT_FILE = PROJECT_ROOT / "config" / "mine_aoi_projected.geojson"

PROJECTED_CRS = "EPSG:32645"

print("=" * 60)
print("          PROJECTING SHYAMSUNDARPUR AOI")
print("=" * 60)

# Read geographic AOI
aoi = gpd.read_file(INPUT_FILE)

print("\nOriginal CRS:")
print(aoi.crs)

print("\nOriginal bounds:")
print(aoi.total_bounds)

# Convert to projected CRS
projected_aoi = aoi.to_crs(PROJECTED_CRS)

print("\nProjected CRS:")
print(projected_aoi.crs)

print("\nProjected bounds in meters:")
print(projected_aoi.total_bounds)

# Calculate area
area = projected_aoi.geometry.area.sum()

print("\nApproximate AOI area:")
print(f"{area:.2f} square meters")

print("\nApproximate AOI area:")
print(f"{area / 1_000_000:.4f} square kilometers")

# Save projected AOI
projected_aoi.to_file(
    OUTPUT_FILE,
    driver="GeoJSON"
)

print("\nProjected AOI saved:")
print(OUTPUT_FILE)

print("\nSTATUS:")
print("PROJECTED AOI CREATED")
print("FOR DEVELOPMENT / METRIC GIS OPERATIONS ONLY")

print("=" * 60)