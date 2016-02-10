from django.http import HttpResponse
from django.core.servers.basehttp import FileWrapper
from shapeeditor.shared.models import Shapefile, Attribute
from shapeeditor.shared.models import Feature, AttributeValue

from django.contrib.gis.geos.geometry import GEOSGeometry
from django.core.servers.basehttp import FileWrapper
from django.http import HttpResponse

from osgeo import ogr,osr

import os
import os.path
import shutil
import tempfile
import traceback
import zipfile

import shapeeditor.shared.utils as utils



def export_data(shapefile):
    """ Export the contents of the given shapefile.

        'shapefile' is the Shapefile object to export.

        We create a shapefile which holds the contents of the given shapefile,
        then copy the shapefile into a temporary zip archive.  Upon completion,
        we return a Django HttpResponse object which can be used to send the
        zipped shapefile to the user's web browser.
    """
    # Create an OGR shapefile to hold the data we're exporting.

    dstDir = tempfile.mkdtemp()
    dstFile = str(os.path.join(dstDir, shapefile.filename))

    srcSpatialRef = osr.SpatialReference()
    srcSpatialRef.ImportFromEPSG(4326)

    dstSpatialRef = osr.SpatialReference()
    dstSpatialRef.ImportFromWkt(shapefile.srs_wkt)

    coordTransform = osr.CoordinateTransformation(srcSpatialRef,
                                                  dstSpatialRef)

    driver = ogr.GetDriverByName("ESRI Shapefile")
    datasource = driver.CreateDataSource(dstFile)
    layer = datasource.CreateLayer(str(shapefile.filename),
                                   dstSpatialRef)

    # Define the various fields which will hold our attributes.

    for attr in shapefile.attribute_set.all():
        field = ogr.FieldDefn(str(attr.name), attr.type)
        field.SetWidth(attr.width)
        field.SetPrecision(attr.precision)
        layer.CreateField(field)

    # Save the feature geometries and attributes into the shapefile.

    geomField = utils.calcGeometryField(shapefile.geom_type)

    for feature in shapefile.feature_set.all():
        geometry = getattr(feature, geomField)
        geometry = utils.unwrapGEOSGeometry(geometry)
        dstGeometry = ogr.CreateGeometryFromWkt(geometry.wkt)
        dstGeometry.Transform(coordTransform)

        dstFeature = ogr.Feature(layer.GetLayerDefn())
        dstFeature.SetGeometry(dstGeometry)

        for attrValue in feature.attributevalue_set.all():
            utils.setOGRFeatureAttribute(attrValue.attribute,
                                         attrValue.value,
                                         dstFeature,
                                         shapefile.encoding)

        layer.CreateFeature(dstFeature)
        dstFeature.Destroy()

    datasource.Destroy() # Close the file, write everything to disk.

    # Compress the shapefile into a ZIP archive.

    temp = tempfile.TemporaryFile()
    zip = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)

    shapefileBase = os.path.splitext(dstFile)[0]
    shapefileName = os.path.splitext(shapefile.filename)[0]

    for fName in os.listdir(dstDir):
        zip.write(os.path.join(dstDir, fName), fName)

    zip.close()

    # Clean up our temporary files.

    shutil.rmtree(dstDir)

    # Create an HttpResponse object to send the ZIP file back to the user's web
    # browser.

    f = FileWrapper(temp)
    response = HttpResponse(f, content_type="application/zip")
    response['Content-Disposition'] = "attachment; filename=" \
                                    + shapefileName + ".zip"
    response['Content-Length'] = temp.tell()
    temp.seek(0)
    return response
