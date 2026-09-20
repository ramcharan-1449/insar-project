import asf_search as asf
import geopandas as gpd
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

AOI_FILE = PROJECT_ROOT / "config" / "mine_aoi.geojson"

REFERENCE_ID = (
    "S1A_IW_SLC__1SDV_20240510T121316_20240510T121343_053809_068A02_58C3"
)

START_DATE = "2024-01-01"
END_DATE = "2025-12-31"


print("=" * 70)
print("DYNAMIC ASF REFERENCE SCENE TEST")
print("=" * 70)

# Load AOI
aoi = gpd.read_file(AOI_FILE).to_crs("EPSG:4326")
geometry = aoi.geometry.union_all()

print("\nSearching ASF using the same method that already worked...")

results = asf.search(
    platform=asf.PLATFORM.SENTINEL1,
    intersectsWith=geometry.wkt,
    start=START_DATE,
    end=END_DATE,
    processingLevel=asf.PRODUCT_TYPE.SLC,
)

print("Total ASF scenes:", len(results))

reference = None

for scene in results:
    scene_id = scene.properties.get("sceneName", "")

    if scene_id == REFERENCE_ID:
        reference = scene
        break


if reference is None:
    print("\nREFERENCE SCENE NOT FOUND")
    print("The dynamic ASF search did not return the reference scene.")
    print("\nFirst 10 returned scenes:")

    for scene in results[:10]:
        print(scene.properties.get("sceneName", ""))

    raise SystemExit


print("\nREFERENCE FOUND!")
print("----------------------------------------")
print("Type:", type(reference))
print("Scene:", reference.properties.get("sceneName"))
print("Date:", reference.properties.get("startTime"))
print("Path:", reference.properties.get("pathNumber"))
print("Direction:", reference.properties.get("flightDirection"))
print("Frame:", reference.properties.get("frameNumber"))
print("Polarization:", reference.properties.get("polarization"))

print("\nTesting ASF product stack...")

try:
    stack = reference.stack()

    print("\nSTACK SUCCESS!")
    print("Stack type:", type(stack))
    print("Stack size:", len(stack))

except Exception as e:
    print("\nSTACK ERROR:")
    print(type(e).__name__)
    print(e)

print("\n" + "=" * 70)