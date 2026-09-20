import hyp3_sdk as sdk


print("=" * 70)
print("             HYP3 CONNECTION TEST")
print("=" * 70)

print("\nConnecting to HyP3...")

try:

    hyp3 = sdk.HyP3(
        prompt="password"
    )

    print("\nSUCCESS!")
    print("HyP3 connection established.")

except Exception as error:

    print("\nERROR:")
    print(error)

print("\n" + "=" * 70)