import ee


PROJECT_ID = "insar-project-508217"


def initialize_gee():

    try:
        ee.Initialize(project=PROJECT_ID)

        print("================================")
        print("Google Earth Engine")
        print("STATUS: CONNECTED")
        print("================================")

    except Exception as error:

        print("Authentication required...")

        ee.Authenticate()

        ee.Initialize(project=PROJECT_ID)

        print("Google Earth Engine connected successfully.")


if __name__ == "__main__":
    initialize_gee()