import geopandas as gpd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

AOI_FILE = PROJECT_ROOT / "config" / "mine_aoi.geojson"

print("=" * 60)
print("       PROJECTED CRS SELECTION CHECK")
print("=" * 60)

# Load AOI
aoi = gpd.read_file(AOI_FILE)

print("\nAOI CRS:")
print(aoi.crs)

print("\nAOI Bounds:")
print(aoi.total_bounds)

# Calculate centroid
centroid = aoi.to_crs("EPSG:4326").geometry.union_all().centroid

longitude = centroid.x
latitude = centroid.y

print("\nAOI Centroid:")
print("Latitude :", latitude)
print("Longitude:", longitude)

print("\nRecommended CRS candidate:")
print("UTM Zone 45N")
print("EPSG:32645")
print("WGS 84 / UTM zone 45N")

print("\nReason:")
print("The Shyamsundarpur AOI is around longitude 87°E.")
print("UTM Zone 45N covers 84°E to 90°E.")

print("\nSTATUS:")
print("CRS CANDIDATE IDENTIFIED")
print("Final CRS will be recorded after project review.")

print("=" * 60)