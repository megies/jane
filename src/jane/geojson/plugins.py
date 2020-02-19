# -*- coding: utf-8 -*-
"""
GeoJSON Plug-in for Jane's Document Database.

This file also serves as a template/tutorial to create new plug-ins and is
thus extensively commented.
"""
# In the interest of quick import/startup times, please try to import within
# the functions and not at the file level.
from jane.documents.plugins import (ValidatorPluginPoint, IndexerPluginPoint,
                                    DocumentPluginPoint,
                                    RetrievePermissionPluginPoint)


class GeoJSONPlugin(DocumentPluginPoint):
    """
    Each document type for Jane's Document Database must have a
    DocumentPluginPoint with some basic meta information.
    """
    # Each plug-in for a certain document type must share the same name.
    # That's how the plug-ins are grouped per document type.
    name = 'geojson'
    # The title is only for this particular plug-in point and is used in
    # places where a pretty name is desired.
    title = "GeoJSON Plugin for Jane's Document Database"

    # Each document must have a content type. If not specified during the
    # initial upload of the document, this value will be used.
    default_content_type = 'application/geo+json'


class GeoJSONValidatorPlugin(ValidatorPluginPoint):
    """
    Any number of validators can be defined for each document type.

    Each validator must have a validate() method that returns True or False
    depending on weather or not the particular validation has passed or not.
    Only documents that pass all validations can be stored in the database.
    """
    name = 'geojson'
    title = 'GeoJSON Validator'

    def validate(self, document):
        import geojson
        # seems like we get an open bytes object here
        try:
            # it seems UTF-8 is default standard for geojson files and not sure
            # how we could find out if it is a different encoding
            data = document.read().decode('UTF-8')
        except:
            return False
        try:
            data = geojson.loads(data)
            # rely on geojson's internal checks, they seem to look at every
            # single feature and check the sanity of the geometry
            return data.is_valid
        except:
            return False


def _geojson_category_site_retrieve_permission(class_name, category, site):
    """
    Class factory that returns a geojson retrieve permission based on the
    specific site the geojson geometry object is registered for and the
    category of the geojson geometry object.
    """
    class _GeoJSONCategorySiteRetrievePermissionPlugin(
            RetrievePermissionPluginPoint):
        """
        If user does not have this permission, any geojson objects of given
        category and at given site are filtered out.
        """
        name = 'geojson'

        # Permission codename and name according to Django's nomenclature.
        # XXX no idea if dots are allowed in codename, so replace them
        permission_codename = 'can_see_geojson_category_{}_at_site_{}'.format(
            category, site).replace(".", "_")
        permission_name = 'Can See GeoJSON category {} at site {}'.format(
            category, site)
        title = permission_name + ' Permission'

        def filter_queryset_user_has_permission(self, queryset, model_type,
                                                user):
            # If the user has the permission: don't restrict queryset.
            return queryset

        def filter_queryset_user_does_not_have_permission(self, queryset,
                                                          model_type, user):
            # model_type can be document or document index.
            if model_type in ["document", "index"]:
                # filter out any documents/indices for geojson of given
                # category and at given site
                # XXX handling of null values?
                # queryset = queryset.exclude(json__site__isnull=True)
                queryset = queryset.exclude(
                    json__site=site,
                    json__category=category)
            else:
                raise NotImplementedError()
            return queryset

    new_class = _GeoJSONCategorySiteRetrievePermissionPlugin
    # Set the class type name.
    setattr(new_class, "__name__", class_name)
    return new_class


# Retrieve permissions for small events attributed to a specific site (e.g. a
# specific deep geothermal project), if users don't have these permissions
# small events that are attributed to that site are not accessible to them
sites = [
    "Altdorf",
    "Aschheim",
    "Duerrnhaar",
    "Erding",
    "Freiham",
    "Garching",
    "Hoehenrain",
    "Holzkirchen",
    "Ismaning",
    "Kirchstockach",
    "Kirchweidach",
    "Oberhaching",
    "Poing",
    "Pullach",
    "Riem",
    "Sauerlach",
    "Simbach",
    "Straubing",
    "Taufkirchen",
    "Traunreut",
    "Unterfoehring",
    "Unterhaching",
    "Unterschleissheim",
    "Waldkraiburg",
    "Weilheim",
    "UNKNOWN",
    "PUBLIC",
    ]
categories = [
    "Bohransatzpunkt",
    "Bohrpfad",
    "Stoerung",
    "Bewilligungsfeld",
    "Gemeinden",
    ]

# add all geojson site/category permission plugins
local = locals()
for category in categories:
    for site_ in sites:
        permission_plugin_name = \
            'GeoJSON{}at{}RetrievePermissionPlugin'.format(category, site_)
        local[permission_plugin_name] = \
            _geojson_category_site_retrieve_permission(
                permission_plugin_name, category=category, site=site_)


class GeoJSONUnrecognizedRetrievePermissionPlugin(
        RetrievePermissionPluginPoint):
    """
    If user does not have this permission, any geojson objects that are not of
    one of the above categories or sites are filtered out. If a site name is
    misspelled the object would otherwise be shown for all users which is not
    desired.
    """
    name = 'geojson'

    # Permission codename and name according to Django's nomenclature.
    # XXX no idea if dots are allowed in codename, so replace them
    permission_codename = 'can_see_geojson_unrecognized_objects'
    permission_name = 'Can See GeoJSON Unrecognized objects'
    title = permission_name + ' Permission'

    def filter_queryset_user_has_permission(self, queryset, model_type,
                                            user):
        # If the user has the permission: don't restrict queryset.
        return queryset

    def filter_queryset_user_does_not_have_permission(self, queryset,
                                                      model_type, user):
        # model_type can be document or document index.
        if model_type in ["document", "index"]:
            # filter out any documents/indices for geojson of given
            # category and at given site
            # XXX handling of null values?
            # queryset = queryset.exclude(json__site__isnull=True)
            recognized_sites = set()
            recognized_category = set()
            # determine ids of items with recognized sites / categories
            for site in sites:
                for item in queryset.filter(json__site=site):
                    recognized_sites.add(item.id)
            for category in categories:
                for item in queryset.filter(json__category=category):
                    recognized_category.add(item.id)
            # determine ids that have both a recognized site and a recognized
            # category
            recognized_items = recognized_sites & recognized_category
            # now filter queryset so that only recognized items remain
            queryset = queryset.filter(id__in=list(recognized_items))
        else:
            raise NotImplementedError()
        return queryset


class GeoJSONIndexerPlugin(IndexerPluginPoint):
    """
    Each document type can have one indexer.

    Upon uploading, the indexer will parse the uploaded document and extract
    information from it as a list of dictionaries. Each dictionary is the
    index for one particular logical part in the document. A document may
    have one or more indices. In this case here one index will be created
    and stored per event in the QuakeML file.

    Each index will be stored as a JSON file in the database and can be
    searched upon.
    """
    name = 'geojson'
    title = 'GeoJSON Indexer'

    # The meta property defines what keys from the indices can be searched
    # on. For this to work it has to know the type for each key. Possible
    # values for the type are "str", "int", "float", "bool", and "UTCDateTime".
    meta = {
        # type of geojson geometry of individual object
        "geometry_type": "str",
        # category of object (e.g. Bohrpfad, ...)
        "category": "str",
        # label of object
        "name": "str",
        # geothermal project site associated to object
        "site": "str",
        # extents of object
        "min_longitude": "float",
        "min_latitude": "float",
        "max_longitude": "float",
        "max_latitude": "float",
        # geometry as a json encoded string
        "geometry_string": "str",
    }

    def index(self, document):
        """
        The method that actually performs the indexing.

        :param document: The document as a memory file.
        """
        from django.contrib.gis.geos import GEOSGeometry
        import geojson

        # Collect all indices in a list. Each index has to be a dictionary.
        indices = []

        # seems like we get an open bytes object here
        # it seems UTF-8 is default standard for geojson files and not sure
        # how we could find out if it is a different encoding
        data = document.read().decode('UTF-8')
        data = geojson.loads(data)

        for feature in data.features:
            geometry_type = feature.geometry.type
            site = feature.properties.get('site', None)
            category = feature.properties.get('category', None)
            name = feature.properties.get('name', None)

            geometry = feature.get('geometry', None)
            if geometry is None:
                geometry_string = None
                geometry = []
            else:
                geometry_string = str(geometry)
                geometry = [GEOSGeometry(geometry_string)]

            try:
                min_longitude, min_latitude, max_longitude, max_latitude = \
                    geometry[0].extent
            except:
                min_longitude = None
                max_longitude = None
                min_latitude = None
                max_latitude = None

            indices.append({
                "geometry_type": geometry_type,
                "site": site,
                "category": category,
                "name": name,
                "min_longitude": min_longitude,
                "min_latitude": min_latitude,
                "max_longitude": max_longitude,
                "max_latitude": max_latitude,
                "geometry_string": geometry_string,
                # The special key geometry can be used to store geographic
                # information about the indexes geometry. Useful for very
                # fast queries using PostGIS.
                "geometry": geometry,
            })

        return indices
