from pathlib import Path
import csv
import json

import rasterio
from shapely.geometry import shape, box
from shapely.ops import transform
from pyproj import Transformer


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

AOI_FILE = PROJECT_ROOT / "config" / "mine_aoi.geojson"

EXTRACT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hyp3"
    / "extracted"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "config"
    / "hyp3_spatial_qc.csv"
)


# ============================================================
# LOAD AOI
# ============================================================

with open(AOI_FILE, "r", encoding="utf-8") as file:
    aoi = json.load(file)


if not aoi.get("features"):
    print("ERROR: AOI contains no features.")
    raise SystemExit(1)


aoi_geometry = shape(
    aoi["features"][0]["geometry"]
)


if not aoi_geometry.is_valid:
    print("ERROR: AOI geometry is invalid.")
    raise SystemExit(1)


print("=" * 70)
print("HYP3 SPATIAL QC")
print("=" * 70)

print(f"AOI file : {AOI_FILE}")
print(f"AOI area : {aoi_geometry.area:.8f} square degrees")
print()


# ============================================================
# FIND PRODUCT DIRECTORIES
# ============================================================

product_dirs = sorted(
    [
        path
        for path in EXTRACT_DIR.iterdir()
        if path.is_dir()
    ]
)


if not product_dirs:
    print("ERROR: No extracted product directories found.")
    raise SystemExit(1)


print(f"Products found : {len(product_dirs)}")
print()


# ============================================================
# REQUIRED LAYERS
# ============================================================

required_layers = {
    "LOS_DISPLACEMENT": "*_los_disp.tif",
    "COHERENCE": "*_corr.tif",
    "UNWRAPPED_PHASE": "*_unw_phase.tif",
}


# ============================================================
# RESULTS
# ============================================================

results = []


# ============================================================
# CHECK EACH PRODUCT
# ============================================================

for product_dir in product_dirs:

    product_id = product_dir.name

    print("-" * 70)
    print(f"PRODUCT: {product_id}")

    los_files = list(
        product_dir.glob("*_los_disp.tif")
    )

    corr_files = list(
        product_dir.glob("*_corr.tif")
    )

    phase_files = list(
        product_dir.glob("*_unw_phase.tif")
    )

    # --------------------------------------------------------
    # Check required layers
    # --------------------------------------------------------

    has_los = len(los_files) == 1
    has_corr = len(corr_files) == 1
    has_phase = len(phase_files) == 1

    if not has_los:
        print("LOS displacement : MISSING")

    if not has_corr:
        print("Coherence        : MISSING")

    if not has_phase:
        print("Unwrapped phase  : MISSING")

    if not (has_los and has_corr and has_phase):

        results.append({
            "product_id": product_id,
            "los_file": "",
            "crs": "",
            "resolution_x": "",
            "resolution_y": "",
            "width": "",
            "height": "",
            "aoi_coverage_percent": "",
            "layer_alignment": "FAIL",
            "aoi_intersection": "FAIL",
            "status": "FAIL"
        })

        continue

    los_path = los_files[0]
    corr_path = corr_files[0]
    phase_path = phase_files[0]

    # --------------------------------------------------------
    # Open rasters
    # --------------------------------------------------------

    with rasterio.open(los_path) as los:
        with rasterio.open(corr_path) as corr:
            with rasterio.open(phase_path) as phase:

                # ------------------------------------------------
                # Metadata
                # ------------------------------------------------

                crs = los.crs

                width = los.width
                height = los.height

                resolution_x = los.res[0]
                resolution_y = los.res[1]

                print(
                    f"CRS       : {crs}"
                )

                print(
                    f"Resolution: "
                    f"{resolution_x:.2f} x "
                    f"{resolution_y:.2f} m"
                )

                print(
                    f"Dimensions: "
                    f"{width} x {height}"
                )

                # ------------------------------------------------
                # Layer alignment
                # ------------------------------------------------

                same_shape = (
                    los.width == corr.width
                    and los.height == corr.height
                    and los.width == phase.width
                    and los.height == phase.height
                )

                same_crs = (
                    los.crs == corr.crs
                    and los.crs == phase.crs
                )

                same_transform = (
                    los.transform == corr.transform
                    and los.transform == phase.transform
                )

                same_resolution = (
                    los.res == corr.res
                    and los.res == phase.res
                )

                layer_alignment = (
                    same_shape
                    and same_crs
                    and same_transform
                    and same_resolution
                )

                # ------------------------------------------------
                # Convert AOI from WGS84 to raster CRS
                # ------------------------------------------------

                transformer = Transformer.from_crs(
                    "EPSG:4326",
                    crs,
                    always_xy=True
                )

                aoi_projected = transform(
                    transformer.transform,
                    aoi_geometry
                )

                # ------------------------------------------------
                # Raster footprint
                # ------------------------------------------------

                raster_footprint = box(
                    los.bounds.left,
                    los.bounds.bottom,
                    los.bounds.right,
                    los.bounds.top
                )

                # ------------------------------------------------
                # AOI intersection
                # ------------------------------------------------

                intersection = (
                    aoi_projected.intersection(
                        raster_footprint
                    )
                )

                aoi_intersection = (
                    not intersection.is_empty
                    and intersection.area > 0
                )

                # ------------------------------------------------
                # AOI coverage percentage
                # ------------------------------------------------

                aoi_area = aoi_projected.area

                if aoi_area > 0:

                    coverage_percent = (
                        intersection.area
                        / aoi_area
                        * 100
                    )

                else:

                    coverage_percent = 0

                # ------------------------------------------------
                # Status
                # ------------------------------------------------

                if layer_alignment and aoi_intersection:

                    status = "PASS"

                else:

                    status = "FAIL"

                # ------------------------------------------------
                # Print result
                # ------------------------------------------------

                print(
                    f"Layer alignment : "
                    f"{'PASS' if layer_alignment else 'FAIL'}"
                )

                print(
                    f"AOI intersection: "
                    f"{'PASS' if aoi_intersection else 'FAIL'}"
                )

                print(
                    f"AOI coverage    : "
                    f"{coverage_percent:.2f}%"
                )

                print(
                    f"STATUS          : {status}"
                )

                # ------------------------------------------------
                # Save result
                # ------------------------------------------------

                results.append({

                    "product_id": product_id,

                    "los_file": str(
                        los_path.relative_to(
                            PROJECT_ROOT
                        )
                    ),

                    "crs": str(crs),

                    "resolution_x": resolution_x,
                    "resolution_y": resolution_y,

                    "width": width,
                    "height": height,

                    "aoi_coverage_percent":
                        round(
                            coverage_percent,
                            4
                        ),

                    "layer_alignment":
                        "PASS"
                        if layer_alignment
                        else "FAIL",

                    "aoi_intersection":
                        "PASS"
                        if aoi_intersection
                        else "FAIL",

                    "status": status
                })


# ============================================================
# WRITE CSV
# ============================================================

fieldnames = [
    "product_id",
    "los_file",
    "crs",
    "resolution_x",
    "resolution_y",
    "width",
    "height",
    "aoi_coverage_percent",
    "layer_alignment",
    "aoi_intersection",
    "status"
]


with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(results)


# ============================================================
# SUMMARY
# ============================================================

passed = sum(
    1
    for row in results
    if row["status"] == "PASS"
)

failed = sum(
    1
    for row in results
    if row["status"] == "FAIL"
)


print()
print("=" * 70)
print("SPATIAL QC SUMMARY")
print("=" * 70)

print(f"Products checked : {len(results)}")
print(f"PASS             : {passed}")
print(f"FAIL             : {failed}")

print()
print("QC file:")
print(OUTPUT_FILE)

print()
print("Stage 7 spatial QC complete.")