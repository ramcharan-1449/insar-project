from pathlib import Path
import zipfile
import csv
import shutil


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ZIP_DIR = PROJECT_ROOT / "data" / "processed" / "hyp3"
EXTRACT_DIR = ZIP_DIR / "extracted"
INVENTORY_FILE = PROJECT_ROOT / "config" / "hyp3_product_inventory.csv"

EXTRACT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# Extract ZIP while removing the unnecessary top folder
# ---------------------------------------------------------

def extract_zip(zip_path, destination):

    destination.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as archive:

        members = archive.infolist()

        for info in members:

            filename = info.filename.replace("\\", "/")

            # Remove leading slash
            filename = filename.lstrip("/")

            parts = [
                part
                for part in filename.split("/")
                if part
            ]

            if not parts:
                continue

            # HyP3 ZIPs normally contain:
            #
            # PRODUCT_NAME/
            #     files...
            #
            # We remove that first directory.
            if len(parts) > 1:
                relative_parts = parts[1:]
            else:
                relative_parts = parts

            if not relative_parts:
                continue

            target = destination.joinpath(*relative_parts)

            # Security check
            target_resolved = target.resolve()
            destination_resolved = destination.resolve()

            try:
                target_resolved.relative_to(destination_resolved)
            except ValueError:
                raise RuntimeError(
                    f"Unsafe ZIP entry: {info.filename}"
                )

            # Directory
            if info.is_dir():
                target.mkdir(
                    parents=True,
                    exist_ok=True
                )
                continue

            # Create parent directory
            target.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            # Extract file
            with archive.open(info) as source:

                with open(target, "wb") as output:

                    while True:

                        chunk = source.read(1024 * 1024)

                        if not chunk:
                            break

                        output.write(chunk)


# ---------------------------------------------------------
# Find TIFF files
# ---------------------------------------------------------

def find_tiffs(directory):

    return sorted(
        [
            p
            for p in directory.rglob("*")
            if p.is_file()
            and p.suffix.lower() in [".tif", ".tiff"]
        ]
    )


# ---------------------------------------------------------
# Identify important layers
# ---------------------------------------------------------

def identify_layers(tiff_files):

    layers = []

    for tif in tiff_files:

        name = tif.name.lower()

        if "los_disp" in name:
            layers.append("LOS_DISPLACEMENT")

        elif "unw_phase" in name:
            layers.append("UNWRAPPED_PHASE")

        elif "corr" in name:
            layers.append("COHERENCE")

        elif "inc_map" in name:
            layers.append("INCIDENCE_ANGLE")

        elif "lv_theta" in name:
            layers.append("LOOK_VECTOR_THETA")

        elif "lv_phi" in name:
            layers.append("LOOK_VECTOR_PHI")

        elif "vert_disp" in name:
            layers.append("VERTICAL_DISPLACEMENT")

        elif "_dem" in name:
            layers.append("DEM")

        elif "water_mask" in name:
            layers.append("WATER_MASK")

        elif "_amp" in name:
            layers.append("AMPLITUDE")

        elif "wrapped_phase" in name:
            layers.append("WRAPPED_PHASE")

    return sorted(set(layers))


# ---------------------------------------------------------
# Find ZIP files
# ---------------------------------------------------------

zip_files = sorted(ZIP_DIR.glob("*.zip"))

if not zip_files:

    print("ERROR: No HyP3 ZIP files found.")
    raise SystemExit(1)


print("=" * 70)
print("HyP3 PRODUCT EXTRACTION")
print("=" * 70)

print(f"ZIP files : {len(zip_files)}")
print(f"Output    : {EXTRACT_DIR}")
print()


inventory = []


# ---------------------------------------------------------
# Process each product
# ---------------------------------------------------------

for index, zip_path in enumerate(zip_files, start=1):

    product_name = zip_path.stem

    # SHORT extraction folder
    product_id = f"P{index:02d}"

    product_dir = EXTRACT_DIR / product_id

    print("-" * 70)
    print(f"[{index}/{len(zip_files)}] {product_name}")
    print(f"Extraction folder: {product_id}")

    # -----------------------------------------------------
    # Remove incomplete extraction
    # -----------------------------------------------------

    if product_dir.exists():

        existing_tiffs = find_tiffs(product_dir)

        if not existing_tiffs:

            print("Removing incomplete extraction...")
            shutil.rmtree(product_dir)

    try:

        # -------------------------------------------------
        # Check existing extraction
        # -------------------------------------------------

        existing_tiffs = (
            find_tiffs(product_dir)
            if product_dir.exists()
            else []
        )

        if existing_tiffs:

            print("Already extracted.")
            status = "ALREADY_EXTRACTED"

        else:

            print("Extracting ZIP...")

            extract_zip(
                zip_path,
                product_dir
            )

            print("Extraction completed.")

            status = "EXTRACTED"

        # -------------------------------------------------
        # Inspect TIFFs
        # -------------------------------------------------

        tif_files = find_tiffs(product_dir)

        layers = identify_layers(tif_files)

        print(f"TIFF files : {len(tif_files)}")

        if layers:
            print(
                "Layers     : "
                + ", ".join(layers)
            )
        else:
            print("Layers     : None detected")

        # -------------------------------------------------
        # Save inventory
        # -------------------------------------------------

        inventory.append({
            "product_id": product_id,
            "product_name": product_name,
            "zip_file": zip_path.name,
            "extract_directory": str(
                product_dir.relative_to(PROJECT_ROOT)
            ),
            "status": status,
            "tif_count": len(tif_files),
            "files": ";".join(
                str(p.relative_to(PROJECT_ROOT))
                for p in tif_files
            ),
            "layers": ";".join(layers)
        })

    except Exception as error:

        print(f"ERROR: {error}")

        inventory.append({
            "product_id": product_id,
            "product_name": product_name,
            "zip_file": zip_path.name,
            "extract_directory": str(
                product_dir.relative_to(PROJECT_ROOT)
            ),
            "status": "ERROR",
            "tif_count": 0,
            "files": "",
            "layers": ""
        })


# ---------------------------------------------------------
# Write inventory CSV
# ---------------------------------------------------------

fieldnames = [
    "product_id",
    "product_name",
    "zip_file",
    "extract_directory",
    "status",
    "tif_count",
    "files",
    "layers"
]


with open(
    INVENTORY_FILE,
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
# Summary
# ---------------------------------------------------------

successful = sum(
    1
    for item in inventory
    if item["status"] in [
        "EXTRACTED",
        "ALREADY_EXTRACTED"
    ]
)

errors = sum(
    1
    for item in inventory
    if item["status"] == "ERROR"
)

total_tiffs = sum(
    item["tif_count"]
    for item in inventory
)


print()
print("=" * 70)
print("EXTRACTION SUMMARY")
print("=" * 70)

print(f"ZIP files found : {len(zip_files)}")
print(f"Successful      : {successful}")
print(f"Errors          : {errors}")
print(f"Total TIFFs     : {total_tiffs}")

print()
print("Inventory:")
print(INVENTORY_FILE)

print()
print("Stage 5 extraction complete.")