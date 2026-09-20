from pathlib import Path
import zipfile
import csv
import rasterio


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ZIP_DIR = PROJECT_ROOT / "data" / "processed" / "hyp3"
EXTRACT_DIR = ZIP_DIR / "extracted_short"
INVENTORY_FILE = ZIP_DIR / "product_inventory.csv"


def classify_layer(filename):
    name = filename.lower()

    if "_los_disp" in name:
        return "los_displacement"
    if "_vert_disp" in name:
        return "vertical_displacement"
    if "_unw_phase" in name:
        return "unwrapped_phase"
    if "_corr" in name:
        return "coherence"
    if "_amp" in name:
        return "amplitude"
    if "_inc_map" in name:
        return "incidence_angle"
    if "_lv_phi" in name:
        return "look_vector_phi"
    if "_lv_theta" in name:
        return "look_vector_theta"
    if "_dem" in name:
        return "dem"
    if "_water_mask" in name:
        return "water_mask"

    return "other"


def extract_zip(zip_path, output_dir):

    output_dir.mkdir(parents=True, exist_ok=True)

    extracted_count = 0

    with zipfile.ZipFile(zip_path, "r") as z:

        for member in z.infolist():

            # Ignore directories
            if member.is_dir():
                continue

            # Only extract useful scientific files
            filename = Path(member.filename).name

            # Avoid deeply nested ZIP paths.
            target = output_dir / filename

            try:

                with z.open(member) as source:
                    with open(target, "wb") as destination:
                        destination.write(source.read())

                extracted_count += 1

            except Exception as e:

                print(f"  WARNING: Could not extract {filename}")
                print(f"           {e}")

    return extracted_count


def inspect_raster(tif_path):

    try:

        with rasterio.open(tif_path) as src:

            return {
                "crs": str(src.crs),
                "width": src.width,
                "height": src.height,
                "resolution_x": src.res[0],
                "resolution_y": src.res[1],
                "nodata": src.nodata,
                "dtype": str(src.dtypes[0]),
            }

    except Exception as e:

        print(f"  WARNING: Could not inspect {tif_path.name}")
        print(f"           {e}")

        return {
            "crs": "",
            "width": "",
            "height": "",
            "resolution_x": "",
            "resolution_y": "",
            "nodata": "",
            "dtype": "",
        }


def main():

    print("=" * 70)
    print("HyP3 Product Extraction and Validation")
    print("=" * 70)

    ZIP_DIR.mkdir(parents=True, exist_ok=True)
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)

    zip_files = sorted(ZIP_DIR.glob("*.zip"))

    print(f"ZIP products found : {len(zip_files)}")
    print(f"Extraction folder  : {EXTRACT_DIR}")
    print()

    if not zip_files:

        print("ERROR: No HyP3 ZIP files found.")
        return

    inventory = []

    successful_zips = 0
    failed_zips = 0

    for index, zip_path in enumerate(zip_files, start=1):

        product_id = f"P{index:03d}"

        output_dir = EXTRACT_DIR / product_id

        print("-" * 70)
        print(f"{product_id}: {zip_path.name}")

        try:

            with zipfile.ZipFile(zip_path, "r") as z:

                members = [
                    m for m in z.infolist()
                    if not m.is_dir()
                ]

                extracted_count = 0

                for member in members:

                    filename = Path(member.filename).name

                    target = output_dir / filename

                    try:

                        output_dir.mkdir(
                            parents=True,
                            exist_ok=True
                        )

                        with z.open(member) as source:

                            with open(target, "wb") as destination:

                                destination.write(source.read())

                        extracted_count += 1

                    except Exception as e:

                        print(
                            f"  WARNING: Could not extract "
                            f"{filename}"
                        )
                        print(f"           {e}")

            print(
                f"Files extracted    : "
                f"{extracted_count}/{len(members)}"
            )

            successful_zips += 1

        except zipfile.BadZipFile:

            print("  ERROR: Invalid ZIP file.")
            failed_zips += 1
            continue

        except Exception as e:

            print(f"  ERROR: {e}")
            failed_zips += 1
            continue

        # Inspect TIFF files
        tif_files = sorted(output_dir.glob("*.tif"))

        print(f"Raster files found : {len(tif_files)}")

        for tif_path in tif_files:

            layer = classify_layer(tif_path.name)

            info = inspect_raster(tif_path)

            relative_path = tif_path.relative_to(
                PROJECT_ROOT
            )

            row = {
                "product_id": product_id,
                "zip_file": zip_path.name,
                "extracted_folder": str(
                    output_dir.relative_to(PROJECT_ROOT)
                ),
                "raster_file": tif_path.name,
                "layer_type": layer,
                "relative_path": str(relative_path),
                **info,
            }

            inventory.append(row)

            print(
                f"  {layer:22s} "
                f"{tif_path.name}"
            )

            print(
                f"      CRS: {info['crs']} | "
                f"Size: {info['width']} x {info['height']} | "
                f"Resolution: "
                f"{info['resolution_x']} x "
                f"{info['resolution_y']}"
            )

    fieldnames = [
        "product_id",
        "zip_file",
        "extracted_folder",
        "raster_file",
        "layer_type",
        "relative_path",
        "crs",
        "width",
        "height",
        "resolution_x",
        "resolution_y",
        "nodata",
        "dtype",
    ]

    with open(
        INVENTORY_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(inventory)

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(f"ZIP products found   : {len(zip_files)}")
    print(f"ZIPs processed       : {successful_zips}")
    print(f"ZIPs failed          : {failed_zips}")
    print(f"Raster records       : {len(inventory)}")
    print(f"Inventory            : {INVENTORY_FILE}")

    if len(inventory) == 0:

        print()
        print("ERROR: No TIFF rasters were extracted.")
        print("Stage 5 FAILED.")

    else:

        print()
        print("Stage 5 completed successfully.")


if __name__ == "__main__":
    main()