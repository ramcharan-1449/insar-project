import geopandas as gpd

FILE = "data/raw/aoi_source/Shyamsundarpur_boundary.geojson"

aoi = gpd.read_file(FILE)

print("=" * 50)
print("SHYAMSUNDARPUR AOI INSPECTION")
print("=" * 50)

print("\nNumber of features:")
print(len(aoi))

print("\nCRS:")
print(aoi.crs)

print("\nGeometry types:")
print(aoi.geometry.geom_type.value_counts())

print("\nBounds:")
print(aoi.total_bounds)

print("\nGeometry validity:")
print(aoi.geometry.is_valid)

print("\nColumns:")
print(aoi.columns.tolist())

print("\nAttributes:")
print(aoi)