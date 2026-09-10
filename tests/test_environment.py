import numpy as np
import pandas as pd
import geopandas as gpd
import shapely
import pyproj
import rasterio
import matplotlib
import ee

print("========== InSAR GIS Environment Test ==========")

print("NumPy:", np.__version__)
print("Pandas:", pd.__version__)
print("GeoPandas:", gpd.__version__)
print("Shapely:", shapely.__version__)
print("PyProj:", pyproj.__version__)
print("Rasterio:", rasterio.__version__)
print("Matplotlib:", matplotlib.__version__)

print("\nAll GIS Python libraries imported successfully.")