
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import render
from shapeeditor.shared.models import Shapefile
from django.http import HttpResponseRedirect
from shapeeditor.editor.forms import ImportShapefileForm
from shapeeditor.shapefileIO import importer
from shapeeditor.shapefileIO import exporter
import traceback
from django.contrib.gis.geos import Point
from shapeeditor.shared.models import Feature
from shapeeditor.shared import utils
from django.http import JsonResponse

#===================================================
from django.http import Http404
import math
from django.shortcuts import get_object_or_404
import mapnik
from django.conf import settings

selected = 2


MAX_ZOOM_LEVEL = 10
TILE_WIDTH = 256
TILE_HEIGHT = 256
#===============================================
def list_shapefiles(request):
	shapefiles = Shapefile.objects.all().order_by('filename')
	return render(request, 'list_shapefiles.html', {'shapefiles' : shapefiles})

def import_shapefile(request):
	if request.method == 'GET':
		form = ImportShapefileForm()
		return render(request, 'import_shapefile.html', {'form' : form, 'err_msg' : None})
	elif request.method == 'POST':
		form = ImportShapefileForm(request.POST, request.FILES)
		if form.is_valid():
			shapefile = request.FILES['import_file']
			encoding = request.POST['character_encoding']

			err_msg = importer.import_data(shapefile, encoding)
			if err_msg == 'None':
				return HttpResponseRedirect('/shape-editor')
		else:
			err_msg = None
		return render(request, 'import_shapefile.html', {'form' : form, 'err_msg' : err_msg})


def edit_shapefile(request, shapefile_id):
    try:
        shapefile = Shapefile.objects.get(id=shapefile_id)
    except Shapefile.DoesNotExist:
        return HttpResponseNotFound
    #find_feature_url = "http://" + request.get_host() + "/shape-editor/find_feature"
    tms_url = "http://"+request.get_host()+"/shape-editor/"

    find_feature_url = "http://" + request.get_host() + "/shape-editor/find_feature"
    return render(request, "select_feature.html", {'shapefile': shapefile, 'find_feature_url' : find_feature_url, 'tmsss_url': tms_url})


def delete_shapefile(request, shapefile_id):
	shapefile = Shapefile.objects.get(id=shapefile_id)
	if request.method == "GET":
		return render(request, "deleteShapefile.html", {'shapefile' : shapefile})
	elif request.method == "POST":
		if request.POST['confirm'] == "1":
			shapefile.delete()
		return HttpResponseRedirect("/shape-editor")





#====================================================================
def root(request):
    """ Return the root resource for our Tile Map Server.

        This tells the TMS client about our one and only TileMapService.
    """
    try:
        baseURL = request.build_absolute_uri()
        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8" ?>')
        xml.append('<Services>')
        xml.append('  <TileMapService title="ShapeEditor Tile Map Service"')
        xml.append('                  version="1.0"')
        xml.append('                  href="' + baseURL + '/1.0"/>')
        xml.append('</Services>')
        return HttpResponse("\n".join(xml), content_type="text/xml")
    except:
        traceback.print_exc()
        return HttpResponse("WTF dude!!!??")

def service(request, version):
    """ Return the TileMapService resource for our Tile Map Server.

        This tells the TMS client about the tile maps available within our Tile
        Map Service.  Note that each tile map corresponds to a shapefile in our
        database.
    """
    try:
        if version != "1.0":
            raise Http404

        baseURL = request.build_absolute_uri()
        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8" ?>')
        xml.append('<TileMapService version="1.0" services="' + baseURL + '">')
        xml.append('  <Title>ShapeEditor Tile Map Service</Title>')
        xml.append('  <Abstract></Abstract>')
        xml.append('  <TileMaps>')
        for shapefile in Shapefile.objects.all():
            id = str(shapefile.id)
            xml.append('    <TileMap title="' + shapefile.filename + '"')
            xml.append('             srs="EPSG:4326"')
            xml.append('             href="' + baseURL + '/' + id + '"/>')
        xml.append('  </TileMaps>')
        xml.append('</TileMapService>')
        return HttpResponse("\n".join(xml), content_type="text/xml")
    except:
        traceback.print_exc()
        raise
def tileMap(request, version, shapefile_id):
    """ Return a TileMap resource for our Tile Map Server.

        This returns information about a single TileMap within our Tile Map
        Service.  Note that each TileMap corresponds to a single shapefile in
        our database.
    """
    if version != "1.0":
            raise Http404
    try:

        shapefile = Shapefile.objects.get(id=shapefile_id)
    except Shapefile.DoesNotExist:
        raise Http404
    try:
        baseURL = request.build_absolute_uri()
        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8" ?>')
        xml.append('<TileMap version="1.0" ' +
                   'tilemapservice="' + baseURL + '">')
        xml.append('  <Title>' + shapefile.filename + '</Title>')
        xml.append('  <Abstract></Abstract>')
        xml.append('  <SRS>EPSG:4326</SRS>')
        xml.append('  <BoundingBox minx="-180" miny="-90" ' +
                                  'maxx="180" maxy="90"/>')
        xml.append('  <Origin x="-180" y="-90"/>')
        xml.append('  <TileFormat width="' + str(TILE_WIDTH) +
                   '" height="' + str(TILE_HEIGHT) + '" ' +
                   'content_type="image/png" extension="png"/>')
        xml.append('  <TileSets profile="global-geodetic">')
        for zoomLevel in range(0, MAX_ZOOM_LEVEL+1):
            unitsPerPixel = _unitsPerPixel(zoomLevel)
            xml.append('    <TileSet href="' + baseURL+'/'+str(zoomLevel) +
                       '" units-per-pixel="' + str(unitsPerPixel) +
                       '" order="' + str(zoomLevel) + '"/>')
        xml.append('  </TileSets>')
        xml.append('</TileMap>')
        return HttpResponse("\n".join(xml), content_type="text/xml")
    except:
        traceback.print_exc()
        raise

def tile(request, version, shapefile_id, zoom, x, y):
    try:
        # Parse the supplied parameters to see which area of the map to
        # generate.la
        if version != "1.0":
            raise Http404

        try:
            shapefile = Shapefile.objects.get(id=shapefile_id)
        except Shapefile.DoesNotExist:
            raise Http404

        zoom = int(zoom)
        x    = int(x)
        y    = int(y)

        # geometryField = utils.calcGeometryField(shapefile.geom_type)
        # geometryType  = utils.calcGeometryFieldType(shapefile.geom_type)

       # try:
            #feature = 4

        if zoom < 0 or zoom > MAX_ZOOM_LEVEL:
            raise Http404

        xExtent = _unitsPerPixel(zoom) * TILE_WIDTH
        yExtent = _unitsPerPixel(zoom) * TILE_HEIGHT

        minLong = x * xExtent - 180.0
        minLat  = y * yExtent - 90.0
        maxLong = minLong + xExtent
        maxLat  = minLat  + yExtent

        if (minLong < -180 or maxLong > 180 or
            minLat < -90 or maxLat > 90):
            print "Map extent out of bounds:",minLong,minLat,maxLong,maxLat
            raise Http404

        # Prepare to display the map.

        map = mapnik.Map(TILE_WIDTH, TILE_HEIGHT,
                         "+proj=longlat +datum=WGS84")
        map.background = mapnik.Color("#7391ad")  

        dbSettings = settings.DATABASES['default']

        # Setup our base layer, which displays the base map.

        datasource = mapnik.PostGIS(user=dbSettings['USER'],
                                    password=dbSettings['PASSWORD'],
                                    dbname=dbSettings['NAME'],
                                    table='tms_basemap',
                                    srid=4326,
                                    geometry_field="geometry",
                                    geometry_table='"tms_basemap"')

        baseLayer = mapnik.Layer("baseLayer")
        baseLayer.datasource = datasource
        baseLayer.styles.append("baseLayerStyle")

        rule = mapnik.Rule()

        # rule.symbols.append(
        #     mapnik.PolygonSymbolizer(mapnik.Color("#b5d19c")))
        # rule.symbols.append(
        #     mapnik.LineSymbolizer(mapnik.Color("#404040"), 0.2))

        # style = mapnik.Style()
        # style.rules.append(rule)

        # map.append_style("baseLayerStyle", style)
        # map.layers.append(baseLayer)

        # Setup our feature layer, which displays the features from the
        # shapefile.
        geometry_field = utils.calcGeometryField(shapefile.geom_type)
        query = '(select ' + geometry_field + ' from "shared_feature" where shapefile_id=' + str(shapefile.id) + ') as geom'

        ######print "QUERY: " + query +":" + geometryField+":" + geometryType

        datasource = mapnik.PostGIS(user=dbSettings['USER'],
                                    password=dbSettings['PASSWORD'],
                                    dbname=dbSettings['NAME'],
                                    table=query,
                                    srid=4326,
                                    geometry_field=geometry_field,
                                    geometry_table='shared_feature')

    #     print "DATA SOURCE IS " + str(datasource)
        featureLayer = mapnik.Layer("featureLayer")
        featureLayer.datasource = datasource
        featureLayer.styles.append("featureLayerStyle")

        #rule = mapnik.Rule()
        #if shapefile.geom_type in ["Point", "MultiPoint"]:
            #rule.symbols.append(mapnik.PointSymbolizer())
        #elif shapefile.geom_type in ["LineString", "MultiLineString"]:
            #rule.symbols.append(
                #mapnik.LineSymbolizer(mapnik.Color("#000000"), 0.5))
        #elif shapefile.geom_type in ["Polygon", "MultiPolygon"]:
        style = mapnik.Style()
        # rule = mapnik.Rule()
        # rule.filter = mapnik.Filter("[id] = '2'")
        # symbol = mapnik.PolygonSymbolizer(mapnik.Color("Yellow"))
        # rule.symbols.append(symbol)
        # style.rules.append(rule)


        rule = mapnik.Rule()
        #rule.filter = mapnik.Filter("[id] = '2'")
        rule.symbols.append(mapnik.PolygonSymbolizer(mapnik.Color("#F5F1DE")))   #f7edee
        rule.symbols.append(mapnik.LineSymbolizer(mapnik.Color("#000000"), 0.5))

        #style = mapnik.Style()
        style.rules.append(rule)




        map.append_style("featureLayerStyle", style)
        map.layers.append(featureLayer)



        


        datasource = mapnik.PostGIS(user=dbSettings['USER'],
                                    password=dbSettings['PASSWORD'],
                                    dbname=dbSettings['NAME'],
                                    table='shared_feature',
                                    # srid=4326,
                                    geometry_field=geometry_field,
                                    geometry_table='shared_feature')

        selectedLayer = mapnik.Layer("selectedLayer")
        selectedLayer.datasource = datasource
        selectedLayer.styles.append("selectedLayerStyle")

        style = mapnik.Style()
        rule = mapnik.Rule()
        rule.filter = mapnik.Filter("[id] = " + str(selected))
     
        #rule.filter = mapnik.Filter("[id] = " + "28" + "")
        rule.symbols.append(mapnik.PolygonSymbolizer(mapnik.Color("orange")))
        rule.symbols.append(mapnik.LineSymbolizer(mapnik.Color("orange"), 1))
        style.rules.append(rule)



        map.append_style("selectedLayerStyle", style)
        map.layers.append(selectedLayer)



        # Finally, render the map.
        map.zoom_to_box(mapnik.Box2d(minLong, minLat, maxLong, maxLat))
        image = mapnik.Image(TILE_WIDTH, TILE_HEIGHT)
        mapnik.render(map, image)
        imageData = image.tostring('png')
        return HttpResponse(imageData, content_type="image/png")
    except:
        traceback.print_exc()
        raise



def _unitsPerPixel(zoomLevel):
    return 0.703125/math.pow(2,zoomLevel)



def find_feature(request, version, shapefile_id, zoom, x, y):
    try:
        shapefile_id = int(request.GET['shapefile_id'])
        latitude = float(request.GET['latitude'])
        longitude = float(request.GET['longitude'])

        shapefile = Shapefile.objects.get(id=shapefile_id)
        pt = Point(longitude, latitude)
        radius = utils.calc_search_radius(latitude, longitude, 100)

        if shapefile.geom_type in ["Polygon", "MultiPolygon"]:
            query = Feature.objects.filter(geom_multipolygon__dwithin=(pt, radius))
        else:
            print "Unsupported Geometry " + shapefile.geom_type
            return HttpResponse("")
        if query.count() != 1:
            return HttpResponse("")

        feature = query[0]

        #return HttpResponse("/shape-editor/edit/" + str(shapefile_id))
        #print feature.id
        a = HttpResponseNotFound(feature.id)
        
        selected = int(a.content)
        
        return 

        

    except:
        traceback.print_exc()
        return HttpResponse("")



# def edit_shapefile(request, shapefile_id):
#     try:
#         shapefile = Shapefile.objects.get(id=shapefile_id)
#     except Shapefile.DoesNotExist:
#         return HttpResponseNotFound
#     tms_url = "http://"+request.get_host()+"/tms/"
#     #find_feature_url = "http://" + request.get_host() + "/shape-editor/find_feature"

#     find_feature_url = "http://" + request.get_host() + "/shape-editor/find_feature"
    
#     return render(request, "select_feature.html", {'shapefile': shapefile, 'find_feature_url' : find_feature_url, 'tmsss_url': tms_url})





