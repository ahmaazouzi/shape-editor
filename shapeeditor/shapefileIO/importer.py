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

import shapeeditor.shared.utils


def import_data(shapefile, character_encoding):
    fd,fname = tempfile.mkstemp(suffix=".zip")
    os.close(fd)

    f = open(fname, "wb")
    for chunk in shapefile.chunks():
        f.write(chunk)
    f.close()
    ######################################

    if not zipfile.is_zipfile(fname):
        os.remove(fname)
        return "Not a valid zip archive."

    zip = zipfile.ZipFile(fname)

    required_suffixes = [".shp", ".shx", ".dbf", ".prj"]
    hasSuffix = {}
    for suffix in required_suffixes:
        hasSuffix[suffix] = False

    for info in zip.infolist():
        extension = os.path.splitext(info.filename)[1].lower()
        if extension in required_suffixes:
            hasSuffix[extension] = True
        else:
            print "Extraneous file: " + info.filename

    for suffix in required_suffixes:
        if not hasSuffix[suffix]:
            zip.close()
            os.remove(fname)
            return "Archive missing required " + suffix + " file."


    zip = zipfile.ZipFile(fname)
    shapefileName = None
    dirname = tempfile.mkdtemp()
    for info in zip.infolist():
        if info.filename.endswith(".shp"):
            shapefileName = info.filename

        dstFile = os.path.join(dirname, info.filename)
        f = open(dstFile, "wb")
        f.write(zip.read(info.filename))
        f.close()
    zip.close()

    try:
        datasource  = ogr.Open(os.path.join(dirname, shapefileName))
        layer       = datasource.GetLayer(0)
        shapefileOK = True
    except:
        traceback.print_exc()
        shapefileOK = False

    if not shapefileOK:
        os.remove(fname)
        shutil.rmtree(dirname)
        return "Not a valid shapefile."



    geometryType  = layer.GetLayerDefn().GetGeomType()
    geometryName  = shapeeditor.shared.utils.ogrTypeToGeometryName(geometryType)
    srcSpatialRef = layer.GetSpatialRef()
    dstSpatialRef = osr.SpatialReference()
    dstSpatialRef.ImportFromEPSG(4326)

    shapefile = Shapefile(filename=shapefileName,
                          srs_wkt=srcSpatialRef.ExportToWkt(),
                          geom_type=geometryName,
                          encoding=character_encoding)
    shapefile.save()

    attributes = []
    layerDef = layer.GetLayerDefn()
    for i in range(layerDef.GetFieldCount()):
        fieldDef = layerDef.GetFieldDefn(i)
        attr = Attribute(shapefile=shapefile,
                         name=fieldDef.GetName(),
                         type=fieldDef.GetType(),
                         width=fieldDef.GetWidth(),
                         precision=fieldDef.GetPrecision())
        attr.save()
        attributes.append(attr)

    coordTransform = osr.CoordinateTransformation(srcSpatialRef,
                                                  dstSpatialRef)

    for i in range(layer.GetFeatureCount()):
        srcFeature = layer.GetFeature(i)
        srcGeometry = srcFeature.GetGeometryRef()
        srcGeometry.Transform(coordTransform)
        geometry = GEOSGeometry(srcGeometry.ExportToWkt())
        geometry = shapeeditor.shared.utils.wrapGEOSGeometry(geometry)
        geometryField = shapeeditor.shared.utils.calcGeometryField(geometryName)
        args = {}
        args['shapefile'] = shapefile
        args[geometryField] = geometry
        feature = Feature(**args)
        feature.save()

        for attr in attributes:
            success,result = \
                    shapeeditor.shared.utils.getOGRFeatureAttribute(attr, srcFeature,
                                                 character_encoding)
            if not success:
                os.remove(fname)
                shutil.rmtree(dirname)
                shapefile.delete()
                return result

            attrValue = AttributeValue(feature=feature,
                                       attribute=attr,
                                       value=result)
            attrValue.save()

    # Finally, clean everything up.

    os.remove(fname)
    shutil.rmtree(dirname)
