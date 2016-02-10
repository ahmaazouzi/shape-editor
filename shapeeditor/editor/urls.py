# from django.conf.urls import patterns, url
# urlpatterns = patterns('shapeeditor.editor.views', (r'^$', 'list_shapefiles'),(r'^import$', 'import_shapefile'), (r'^delete/(?P<shapefile_id>\d+)$','delete_shapefile'), (r'^edit/(?P<shapefile_id>\d+)$', 'edit_shapefile'), (r'^find_feature$','find_feature'))


from django.conf.urls import patterns, url
urlpatterns = patterns('shapeeditor.editor.views', 
	(r'^$', 'list_shapefiles'),(r'^import$', 'import_shapefile'), 
	(r'^delete/(?P<shapefile_id>\d+)$','delete_shapefile'), 
	(r'^edit/(?P<shapefile_id>\d+)$', 'edit_shapefile'), 
	(r'^find_feature$','find_feature'),
	#copy
	#(r'^edit/(?P<shapefile_id>\d+)$','find_feature'),
	#copy
	(r'^$','root'),
	(r'^(?P<version>[0-9.]+)$','service'),
	(r'^(?P<version>[0-9.]+)/' + r'(?P<shapefile_id>\d+)$','tileMap'),
	(r'^(?P<version>[0-9.]+)/' + r'(?P<shapefile_id>\d+)/(?P<zoom>\d+)/'+r'(?P<x>\d+)/(?P<y>\d+)\.png$','tile'))
	