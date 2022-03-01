# BatchProcessingLocalMoran's-I
  This code processes census data of different years(.tif) and geographical features of administiative areas(.shp).
  1. Extract raster cells within administitive areas of China from the minimum enclosing rectangle of raster files.
  2. Extract the administrative boundaries of each province as single documents from administitive boundaries of China.
  3. For each province, extract raster cells with census data of different years by boundary masks.
  4. Transfer each raster cell to point data with demographic.
  5. Calculate values of Anselin Local Moran's I.
  6. Select points that have HH type of cluster.
  7. Use density clustering to identify the topological relatinoship between each points. Retain clustering results greater than the population threshold and identify them as main centers and semi-centers.
  8. For each main cluster, calculate the shortest distances to the other semi-centers. 
