from pathlib import Path
import csv
import rasterio
import numpy as np


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

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
    / "hyp3_raster_inventory.csv"
)


# ---------------------------------------------------------
# Find TIFF files
# ---------------------------------------------------------

tif_files = sorted(EXTRACT_DIR.rglob("*.tif"))

if not tif_files:

    print("ERROR: No TIFF files found.")
    print(EXTRACT_DIR)
    raise SystemExit(1)


print("=" * 70)
print("HYP3 RASTER INSPECTION")
print("=" * 70)

print(f"TIFF files found : {len(tif_files)}")
print()


# ---------------------------------------------------------
# Inventory
# ---------------------------------------------------------

inventory = []


# ---------------------------------------------------------
# Inspect every raster
# ---------------------------------------------------------

for index, tif_path in enumerate(tif_files, start=1):

    print("-" * 70)
    print(f"[{index}/{len(tif_files)}]")
    print(tif_path.name)

    try:

        with rasterio.open(tif_path) as src:

            data = src.read(1, masked=True)

            # -------------------------------------------------
            # Basic metadata
            # -------------------------------------------------

            width = src.width
            height = src.height
            count = src.count

            crs = str(src.crs)

            transform = src.transform

            resolution_x = src.res[0]
            resolution_y = src.res[1]

            nodata = src.nodata

            dtype = src.dtypes[0]

            bounds = src.bounds

            # -------------------------------------------------
            # Valid data
            # -------------------------------------------------

            valid = data.compressed()

            valid_count = len(valid)

            total_pixels = width * height

            if valid_count > 0:

                minimum = float(np.min(valid))
                maximum = float(np.max(valid))
                mean = float(np.mean(valid))
                median = float(np.median(valid))

            else:

                minimum = ""
                maximum = ""
                mean = ""
                median = ""

            # -------------------------------------------------
            # Product / layer information
            # -------------------------------------------------

            name = tif_path.name.lower()

            if "los_disp" in name:
                layer = "LOS_DISPLACEMENT"

            elif "unw_phase" in name:
                layer = "UNWRAPPED_PHASE"

            elif "corr" in name:
                layer = "COHERENCE"

            elif "inc_map" in name:
                layer = "INCIDENCE_ANGLE"

            elif "lv_theta" in name:
                layer = "LOOK_VECTOR_THETA"

            elif "lv_phi" in name:
                layer = "LOOK_VECTOR_PHI"

            elif "vert_disp" in name:
                layer = "VERTICAL_DISPLACEMENT"

            elif "_dem" in name:
                layer = "DEM"

            elif "water_mask" in name:
                layer = "WATER_MASK"

            elif "_amp" in name:
                layer = "AMPLITUDE"

            elif "wrapped_phase" in name:
                layer = "WRAPPED_PHASE"

            else:
                layer = "OTHER"

            # -------------------------------------------------
            # Product ID
            # -------------------------------------------------

            relative = tif_path.relative_to(EXTRACT_DIR)

            product_id = relative.parts[0]

            # -------------------------------------------------
            # Print information
            # -------------------------------------------------

            print(f"Product      : {product_id}")
            print(f"Layer        : {layer}")
            print(f"Dimensions   : {width} x {height}")
            print(f"Bands        : {count}")
            print(f"CRS          : {crs}")
            print(
                f"Resolution   : "
                f"{resolution_x:.2f} x {resolution_y:.2f} m"
            )
            print(f"NoData       : {nodata}")
            print(f"Data type    : {dtype}")
            print(f"Valid pixels : {valid_count}")
            print(f"Min          : {minimum}")
            print(f"Max          : {maximum}")
            print(f"Mean         : {mean}")
            print(f"Median       : {median}")

            # -------------------------------------------------
            # Save record
            # -------------------------------------------------

            inventory.append({

                "product_id": product_id,

                "file": str(
                    tif_path.relative_to(PROJECT_ROOT)
                ),

                "layer": layer,

                "width": width,
                "height": height,
                "bands": count,

                "crs": crs,

                "resolution_x": resolution_x,
                "resolution_y": resolution_y,

                "nodata": nodata,

                "dtype": dtype,

                "min": minimum,
                "max": maximum,
                "mean": mean,
                "median": median,

                "valid_pixels": valid_count,

                "total_pixels": total_pixels,

                "valid_percent": (
                    valid_count / total_pixels * 100
                    if total_pixels > 0
                    else 0
                ),

                "left": bounds.left,
                "bottom": bounds.bottom,
                "right": bounds.right,
                "top": bounds.top,

                "status": "OK"
            })

    except Exception as error:

        print(f"ERROR: {error}")

        inventory.append({

            "product_id": "",

            "file": str(
                tif_path.relative_to(PROJECT_ROOT)
            ),

            "layer": "",

            "width": "",
            "height": "",
            "bands": "",

            "crs": "",

            "resolution_x": "",
            "resolution_y": "",

            "nodata": "",

            "dtype": "",

            "min": "",
            "max": "",
            "mean": "",
            "median": "",

            "valid_pixels": "",
            "total_pixels": "",
            "valid_percent": "",

            "left": "",
            "bottom": "",
            "right": "",
            "top": "",

            "status": "ERROR"
        })


# ---------------------------------------------------------
# Write CSV
# ---------------------------------------------------------

fieldnames = [

    "product_id",
    "file",
    "layer",

    "width",
    "height",
    "bands",

    "crs",

    "resolution_x",
    "resolution_y",

    "nodata",
    "dtype",

    "min",
    "max",
    "mean",
    "median",

    "valid_pixels",
    "total_pixels",
    "valid_percent",

    "left",
    "bottom",
    "right",
    "top",

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
    writer.writerows(inventory)


# ---------------------------------------------------------
# Final summary
# ---------------------------------------------------------

successful = sum(
    1
    for item in inventory
    if item["status"] == "OK"
)

errors = sum(
    1
    for item in inventory
    if item["status"] == "ERROR"
)


print()
print("=" * 70)
print("RASTER INSPECTION SUMMARY")
print("=" * 70)

print(f"TIFF files inspected : {len(tif_files)}")
print(f"Successful           : {successful}")
print(f"Errors               : {errors}")

print()
print("Inventory saved:")
print(OUTPUT_FILE)

print()
print("Stage 6 raster inspection complete.")