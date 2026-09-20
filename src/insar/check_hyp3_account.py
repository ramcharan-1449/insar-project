import hyp3_sdk as sdk

print("=" * 70)
print("              HYP3 ACCOUNT CHECK")
print("=" * 70)

print("\nConnecting to HyP3...")

try:
    hyp3 = sdk.HyP3(prompt="password")

    print("\nSUCCESS! HyP3 connection established.")

    print("\nChecking account information...")

    info = hyp3.my_info()

    print("\nAccount Information:")
    print(info)

    print("\nChecking available credits...")

    credits = hyp3.check_credits()

    print("\nAvailable Credits:")
    print(credits)

except Exception as error:
    print("\nERROR:")
    print(error)

print("\n" + "=" * 70)
print("                 ACCOUNT CHECK COMPLETE")
print("=" * 70)