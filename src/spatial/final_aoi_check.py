import geopandas as gpd
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

AOI_FILE = PROJECT_ROOT / "config" / "mine_aoi.geojson"
PROJECTED_AOI_FILE = PROJECT_ROOT / "config" / "mine_aoi_projected.geojson"
AOI_CONFIG_FILE = PROJECT_ROOT / "config" / "aoi_config.json"
CRS_FILE = PROJECT_ROOT / "config" / "crs_info.json"


print("=" * 65)
print("        SHYAMSUNDARPUR AOI FINAL DEVELOPMENT CHECK")
print("=" * 65)


# --------------------------------------------------
# 1. Check geographic AOI
# --------------------------------------------------

print("\n[1] Geographic AOI")

aoi = gpd.read_file(AOI_FILE)

print("File:", AOI_FILE)
print("CRS:", aoi.crs)
print("Features:", len(aoi))
print("Geometry:", list(aoi.geometry.geom_type))
print("Valid:", list(aoi.geometry.is_valid))


# --------------------------------------------------
# 2. Check projected AOI
# --------------------------------------------------

print("\n[2] Projected AOI")

projected_aoi = gpd.read_file(PROJECTED_AOI_FILE)

print("File:", PROJECTED_AOI_FILE)
print("CRS:", projected_aoi.crs)
print("Features:", len(projected_aoi))
print("Geometry:", list(projected_aoi.geometry.geom_type))
print("Valid:", list(projected_aoi.geometry.is_valid))


# --------------------------------------------------
# 3. Calculate area
# --------------------------------------------------

area_m2 = projected_aoi.geometry.area.sum()
area_km2 = area_m2 / 1_000_000

print("\n[3] AOI Area")

print(f"Area: {area_m2:.2f} m²")
print(f"Area: {area_km2:.4f} km²")


# --------------------------------------------------
# 4. Read configuration
# --------------------------------------------------

print("\n[4] Configuration")

with open(AOI_CONFIG_FILE, "r") as file:
    aoi_config = json.load(file)

with open(CRS_FILE, "r") as file:
    crs_config = json.load(file)

print("Mine:", aoi_config["mine_name"])
print("Coalfield:", aoi_config["coalfield_name"])
print("District:", aoi_config["district"])

print("Geographic CRS:", crs_config["geographic_crs"])
print("Projected CRS:", crs_config["projected_crs"])


# --------------------------------------------------
# 5. Important development status
# --------------------------------------------------

print("\n[5] DEVELOPMENT STATUS")

print("AOI status:", aoi_config["aoi_status"])
print("Assumed AOI:", aoi_config["assumed_aoi"])
print("Replacement required:", aoi_config["replacement_required"])


# --------------------------------------------------
# 6. Final decision
# --------------------------------------------------

print("\n" + "=" * 65)
print("                    CHECKPOINT")
print("=" * 65)

if (
    aoi.crs.to_string() == "EPSG:4326"
    and
    projected_aoi.crs.to_string() == "EPSG:32645"
    and
    all(aoi.geometry.is_valid)
    and
    all(projected_aoi.geometry.is_valid)
):

    print("\n✅ AOI GEOMETRY: OK")
    print("✅ GEOGRAPHIC CRS: EPSG:4326")
    print("✅ PROJECTED CRS: EPSG:32645")
    print("✅ GEOMETRY VALIDITY: OK")

    print("\n⚠️ AOI IS STILL ASSUMED.")

    print("\nDO NOT USE THIS AOI FOR FINAL")
    print("SCIENTIFIC INSAR ANALYSIS.")

else:

    print("\n❌ AOI CHECK FAILED.")
    print("Please inspect the errors above.")

print("\n" + "=" * 65)