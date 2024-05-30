import arcpy
import bs4


# Function used to create point objects from all placemark tags within the kml file. The function uses a cursor to
# insert necessary data into rows such as the coordinates and names for each location.
def createPoint(pointCursor, coords, spatRef, locName):
    point = arcpy.Point(lat, lon)
    pt_geometry = arcpy.PointGeometry(point, spatRef, locName)
    pointCursor.insertRow((pt_geometry, locName))


# Function to create polygons from all GroundOverlay tags in the kml. Since it's a function creating polygons, it uses a
# separate InsertCursor.
def createPolygon(polyCursor, array, spatRef, locName):
    polygon = arcpy.Polygon(array, spatRef, locName)
    polyCursor.insertRow((polygon, locName))
    array.removeAll()


# The input kml file location
inKML = "C:/PSUGIS/GEOG485/GEOG485_FinalProject/Middle-Earth.kml"

# The workspace
arcpy.env.workspace = "C:/PSUGIS/GEOG485/GEOG485_FinalProject"

# The name of the output feature classes
pointFC = "MiddleEarthLocations.shp"
polygonFC = "MiddleEarthPolygons.shp"

# Check to see if feature classes by the same name already exists in the location. If so, delete them.
if arcpy.Exists(pointFC):
    arcpy.Delete_management(pointFC)

if arcpy.Exists(polygonFC):
    arcpy.Delete_management(polygonFC)

# The spatial reference object that gets passed into the feature classes upon creation.
SR = arcpy.SpatialReference("GCS_WGS_1984")

# Create the point/polygon shapefiles.
arcpy.CreateFeatureclass_management(arcpy.env.workspace, pointFC, "POINT", spatial_reference=SR)
# Adding a field for the points shapefile to display the respective location names.
arcpy.AddField_management(pointFC, "LocName", "TEXT")
arcpy.CreateFeatureclass_management(arcpy.env.workspace, polygonFC, "POLYGON", spatial_reference=SR)
# Adding a field called LocName to store the respective names of the polygons in the attribute table.
arcpy.AddField_management(polygonFC, "LocName", "TEXT")
# The spatial reference data that will be passed to the createPoint/createPolygon functions in the InsertCursor.
spatialRef = arcpy.Describe(pointFC).spatialReference
polygonSpatialRef = arcpy.Describe(polygonFC).spatialReference

# Open up the inKML file to begin reading through it.
with open(inKML, "r") as kml:
    try:
        # The soup object is basically our parser here. Think of it as the equivalent of a csvReader object.
        soup = bs4.BeautifulSoup(kml, features="lxml")

        # We're interested in the Placemarks and the GroundOverlays to map the points and polygons
        placemarks = soup.findAll("placemark")
        groundOverlay = soup.findAll("groundoverlay")

        # placemarkChild finds child tags in Placemarks
        placemarkChild = soup.findChild("placemark")

        # groundOverlayChild finds child tags inside GroundOverlays
        groundOverlayChild = soup.findChild("groundoverlay")

    except arcpy.ExecuteError:
        print(arcpy.GetMessages("Something went terribly wrong!"))

    # Begin the InsertCursor for the points shapefile.
    with arcpy.da.InsertCursor(pointFC, ["SHAPE@XY", "LocName"]) as cursor:
        try:
            # Loop through all the placemarks
            for placemarkChild in placemarks:
                # The names are the text elements within each <name> tag.
                names = placemarkChild.find("name").get_text()
                # coordinatesTag is the <coordinates> tag inside the placemarks.
                coordinatesTag = placemarkChild.find("coordinates")
                # coordText is the text element we need inside each <coordinates> tag.
                coordText = coordinatesTag.get_text()
                # Now the list is split along the ","
                coordSplit = coordText.split(",")
                # Latitude is the 0 index
                lat = coordSplit[0]
                # Longitude is the 1 index.
                lon = coordSplit[1]
                # Now create the tuple called coordinates.
                coordinates = [float(lat), float(lon)]
                # Declare the dictionary object
                locationDict = {names: coordinates}
                # Print the dictionary for viewing on the console
                print(locationDict)
                # Create the point with the createPoint function defined above.
                createPoint(cursor, coordinates, spatialRef, names)

        except arcpy.ExecuteError:
            print(arcpy.GetMessages("Something else went terribly wrong!"))

    # Now that the points shapefile is finished, it's time to populate the polygon shapefile.
    with arcpy.da.InsertCursor(polygonFC, ["SHAPE@", "LocName"]) as polygonCursor:
        try:
            # Loop through the GroundOverlays
            for groundOverlayChild in groundOverlay:
                # The groundOverlayName is the text inside the <name> tags within each GroundOverlay tag.
                groundOverlayName = groundOverlayChild.find("name").get_text()
                # north, south, east, and west are the text elements inside their respective tags within each
                # GroundOverlay.
                north = groundOverlayChild.find("north").get_text()
                south = groundOverlayChild.find("south").get_text()
                east = groundOverlayChild.find("east").get_text()
                west = groundOverlayChild.find("west").get_text()
                # We need a vertexArray to store the points.
                vertexArray = arcpy.Array([])
                # We have to make lat/lon coordinates out of the north/south/east/west tags. This needs to be lists
                # inside of a list so we can assign a lat/lon point to each list index to map out the four corners of
                # the polygon.
                groundOverlayCoords = [[float(north), float(west)], [float(north), float(east)],
                                       [float(south), float(east)], [float(south), float(west)]]
                # Now we can assign each index in groundOverlayCoords to a point.
                NWPoint = groundOverlayCoords[0]
                NEPoint = groundOverlayCoords[1]
                SEPoint = groundOverlayCoords[2]
                SWPoint = groundOverlayCoords[3]
                # Make another list of all the newly created variables.
                pointList = [NWPoint, NEPoint, SEPoint, SWPoint]
                # Now loop through the pointList and define our latitude/longitude that will be appended to the
                # vertexArray using arcpy.Point
                for points in pointList:
                    latitude = points[0]
                    longitude = points[1]
                    # Append the vertexArray with the latitude/longitude point. It's lon/lat because I think I
                    # accidentally reversed things in an earlier step.
                    vertexArray.append(arcpy.Point(longitude, latitude))
                # Now, finally, we create the polygons.
                createPolygon(polygonCursor, vertexArray, polygonSpatialRef, groundOverlayName)

        except arcpy.ExecuteError:
            print(arcpy.GetMessages("Something went terribly wrong! Hopefully for the last time"))
# That's it! Job's done!
