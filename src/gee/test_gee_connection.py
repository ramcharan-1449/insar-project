import ee

print("=" * 70)
print("             GOOGLE EARTH ENGINE TEST")
print("=" * 70)

print("\nInitializing Google Earth Engine...")

try:
    ee.Initialize()

    print("\nSUCCESS! ✅")
    print("Google Earth Engine connection is working.")

    print("\nTesting Earth Engine computation...")

    result = ee.Number(10).multiply(5).getInfo()

    print("Test calculation: 10 × 5 =", result)

    print("\nGEE is ready for the project.")

except Exception as error:

    print("\nERROR:")
    print(error)

print("\n" + "=" * 70)
print("              GEE TEST COMPLETE")
print("=" * 70)
