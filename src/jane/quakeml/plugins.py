# -*- coding: utf-8 -*-
"""
QuakeML Plug-in for Jane's Document Database.

This file also serves as a template/tutorial to create new plug-ins and is
thus extensively commented.
"""
# In the interest of quick import/startup times, please try to import within
# the functions and not at the file level.
from jane.documents.plugins import (ValidatorPluginPoint, IndexerPluginPoint,
                                    DocumentPluginPoint,
                                    RetrievePermissionPluginPoint)
from jane.local_settings import GEOTHERMIE_SITES


class QuakeMLPlugin(DocumentPluginPoint):
    """
    Each document type for Jane's Document Database must have a
    DocumentPluginPoint with some basic meta information.
    """
    # Each plug-in for a certain document type must share the same name.
    # That's how the plug-ins are grouped per document type.
    name = 'quakeml'
    # The title is only for this particular plug-in point and is used in
    # places where a pretty name is desired.
    title = "QuakeML Plugin for Jane's Document Database"

    # Each document must have a content type. If not specified during the
    # initial upload of the document, this value will be used.
    default_content_type = 'text/xml'


class QuakeMLValidatorPlugin(ValidatorPluginPoint):
    """
    Any number of validators can be defined for each document type.

    Each validator must have a validate() method that returns True or False
    depending on weather or not the particular validation has passed or not.
    Only documents that pass all validations can be stored in the database.
    """
    name = 'quakeml'
    title = 'QuakeML XMLSchema Validator'

    def validate(self, document):
        from obspy.io.quakeml.core import _validate as validate_quakeml  # NOQA
        try:
            is_valid = validate_quakeml(document)
        except:
            is_valid = False
        return is_valid


def _site_magnitude_threshold_retrieve_permission(
        class_name, magnitude_threshold, site=None):
    """
    Class factory that returns a quakeml retrieve permission based on a
    magnitude threshold, optionally only working on a specific site.
    If multiple of these restrictions are defined, all of them apply separately
    and the user must have all of them set, down to the lowest threshold
    restriction that is supposed to apply.
    """
    class _SiteMagnitudeThresholdRetrievePermissionPlugin(
            RetrievePermissionPluginPoint):
        """
        If user does not have this permission, any events below given magnitude
        threshold are filtered out (optionally only for a specific site).
        """
        name = 'quakeml'

        # Permission codename and name according to Django's nomenclature.
        # XXX no idea if dots are allowed in codename, so replace them
        permission_codename = 'can_see_mag_lessthan_{}_site_{}_events'.format(
            magnitude_threshold, site or "any").replace(".", "_")
        permission_name = 'Can See Magnitude <{} Events{}'.format(
            magnitude_threshold, site and " At site='{}'".format(site) or "")
        title = permission_name + ' Permission'

        def filter_queryset_user_has_permission(self, queryset, model_type,
                                                user):
            # If the user has the permission: don't restrict queryset.
            return queryset

        def filter_queryset_user_does_not_have_permission(self, queryset,
                                                          model_type, user):
            # model_type can be document or document index.
            if model_type in ["document", "index"]:
                # filter out any events without a magnitude given
                #queryset = queryset.exclude(json__magnitude__isnull=True)
                # Modify the queryset to only contain indices that are above
                # given magnitude threshold.
                # if no site is specified, just exclude any events below that
                # threshold
                if site is None:
                    queryset = queryset.exclude(
                        json__magnitude__lt=magnitude_threshold)
                # if site is specified, we need to search for events below the
                # given magnitude threshold that are associated to that site,
                # and then exclude them from the queryset
                else:
                    queryset = queryset.exclude(
                        json__site=site,
                        json__magnitude__lt=magnitude_threshold)
            else:
                raise NotImplementedError()
            return queryset

    new_class = _SiteMagnitudeThresholdRetrievePermissionPlugin
    # Set the class type name.
    setattr(new_class, "__name__", class_name)
    return new_class


# Retrieve permissions for small events, if users don't have these permissions
# small events are not accessible to them
MagnitudeLessThanOneRetrievePermissionPlugin = \
    _site_magnitude_threshold_retrieve_permission(
        "MagnitudeLessThanOneRetrievePermissionPlugin",
        magnitude_threshold=0.95)
MagnitudeLessThanTwoRetrievePermissionPlugin = \
    _site_magnitude_threshold_retrieve_permission(
        "MagnitudeLessThanTwoRetrievePermissionPlugin", magnitude_threshold=1.95)

# Retrieve permissions for small events attributed to a specific site (e.g. a
# specific deep geothermal project), if users don't have these permissions
# small events that are attributed to that site are not accessible to them

# add all site/magnitude-threshold permission plugins
local = locals()
for site_ in GEOTHERMIE_SITES:
    # ignore special "site" for "open" geojson data
    if site_ == 'PUBLIC':
        continue
    for mag_threshold, mag_string in zip(
            (0.95, 1.95),
            ('One', 'Two')):
        permission_plugin_name = '{}LessThan{}RetrievePermissionPlugin'.format(
            site_, mag_string)
        local[permission_plugin_name] = \
            _site_magnitude_threshold_retrieve_permission(
                permission_plugin_name, magnitude_threshold=mag_threshold,
                site=site_)


class QuakeMLIndexerPlugin(IndexerPluginPoint):
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
    name = 'quakeml'
    title = 'QuakeML Indexer'

    # The meta property defines what keys from the indices can be searched
    # on. For this to work it has to know the type for each key. Possible
    # values for the type are "str", "int", "float", "bool", and "UTCDateTime".
    meta = {
        "quakeml_id": "str",
        "latitude": "float",
        "longitude": "float",
        "depth_in_m": "float",
        "origin_time": "UTCDateTime",
        "magnitude": "float",
        "magnitude_type": "str",
        "agency": "str",
        "author": "str",
        "public": "bool",
        "evaluation_mode": "str",
        "event_type": "str",
        "has_focal_mechanism": "bool",
        "has_moment_tensor": "bool",
        "site": "str",
        "horizontal_uncertainty_max": "float",
        "horizontal_uncertainty_min": "float",
        "horizontal_uncertainty_max_azimuth": "float",
    }

    def index(self, document):
        """
        The method that actually performs the indexing.

        :param document: The document as a memory file.
        """
        from django.contrib.gis.geos import (
            Point, LineString, MultiLineString)
        from obspy import read_events

        # Collect all indices in a list. Each index has to be a dictionary.
        indices = []

        inv = read_events(document, format="quakeml")

        for event in inv:
            if event.origins:
                org = event.preferred_origin() or event.origins[0]
            else:
                org = None

            if event.magnitudes:
                mag = event.preferred_magnitude() or event.magnitudes[0]
            else:
                mag = None

            has_focal_mechanism = False
            has_moment_tensor = False
            if event.focal_mechanisms:
                has_focal_mechanism = True
                if any(mt for mt in event.focal_mechanisms):
                    has_moment_tensor = True

            # Parse attributes in the baynet namespace.
            # The public attribute defaults to True, it can only be set to
            # False by utilizing the baynet namespace as of now.
            extra = event.get("extra", {})
            if "public" in extra:
                public = extra["public"]["value"]
                if public.lower() in ["false", "f"]:
                    public = False
                elif public.lower() in ["true", "t"]:
                    public = True
                else:
                    public = None
            else:
                public = True
            if "evaluationMode" in extra:
                evaluation_mode = extra["evaluationMode"]["value"]
            else:
                evaluation_mode = None
            if "site" in extra:
                site = extra["site"]["value"]
            else:
                site = None
            # parse horizontal uncertainties
            if org and org.origin_uncertainty:
                org_unc = org.origin_uncertainty
                if org_unc.preferred_description == 'horizontal uncertainty':
                    horizontal_uncertainty_max = org_unc.horizontal_uncertainty
                    horizontal_uncertainty_min = org_unc.horizontal_uncertainty
                    horizontal_uncertainty_max_azimuth = 0
                elif org_unc.preferred_description == 'uncertainty ellipse':
                    horizontal_uncertainty_max = \
                        org_unc.max_horizontal_uncertainty
                    horizontal_uncertainty_min = \
                        org_unc.min_horizontal_uncertainty
                    horizontal_uncertainty_max_azimuth = \
                        org_unc.azimuth_max_horizontal_uncertainty
                else:
                    horizontal_uncertainty_max = None
                    horizontal_uncertainty_min = None
                    horizontal_uncertainty_max_azimuth = None
            else:
                horizontal_uncertainty_max = None
                horizontal_uncertainty_min = None
                horizontal_uncertainty_max_azimuth = None

            geometry = None
            if org:
                geometry = [Point(org.longitude, org.latitude)]
                if all(value is not None for value in (
                        horizontal_uncertainty_max, horizontal_uncertainty_min,
                        horizontal_uncertainty_max_azimuth)):
                    import geopy
                    import geopy.distance
                    start = geopy.Point(latitude=org.latitude,
                                        longitude=org.longitude)
                    lines = []
                    for distance, azimuth in (
                            (horizontal_uncertainty_max,
                             horizontal_uncertainty_max_azimuth),
                            (horizontal_uncertainty_min,
                             horizontal_uncertainty_max_azimuth + 90)):
                        azimuth = azimuth % 180
                        distance = geopy.distance.geodesic(
                            kilometers=distance / 1e3)
                        end1 = distance.destination(
                            point=start, bearing=azimuth)
                        end2 = distance.destination(
                            point=start, bearing=azimuth + 180)
                        line = LineString((end1.longitude, end1.latitude),
                                          (org.longitude, org.latitude),
                                          (end2.longitude, end2.latitude))
                        lines.append(line)
                    geometry.append(MultiLineString(lines))
                else:
                    geometry.append(MultiLineString([]))

            indices.append({
                "quakeml_id": str(event.resource_id),
                "latitude": org.latitude if org else None,
                "longitude": org.longitude if org else None,
                "depth_in_m": org.depth if org else None,
                "origin_time": str(org.time) if org else None,
                "magnitude": mag.mag if mag else None,
                "magnitude_type": mag.magnitude_type if mag else None,
                "agency":
                event.creation_info and event.creation_info.agency_id or None,
                "author":
                event.creation_info and event.creation_info.author or None,
                "public": public,
                "evaluation_mode": evaluation_mode,
                "event_type": event.event_type,
                "has_focal_mechanism": has_focal_mechanism,
                "has_moment_tensor": has_moment_tensor,
                # The special key geometry can be used to store geographic
                # information about the indexes geometry. Useful for very
                # fast queries using PostGIS.
                "geometry": geometry,
                "site": site,
                "horizontal_uncertainty_max": horizontal_uncertainty_max,
                "horizontal_uncertainty_min": horizontal_uncertainty_min,
                "horizontal_uncertainty_max_azimuth":
                    horizontal_uncertainty_max_azimuth,
            })

        return indices
