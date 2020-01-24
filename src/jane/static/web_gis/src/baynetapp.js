var module = angular.module("bayNetApp", ["mgcrea.ngStrap",
    "mgcrea.ngStrap.tooltip",
    "ngAnimate",
    "ngSanitize",
    "ui.bootstrap-slider",
    "toggle-switch"]);

// Jane server constant.
module.constant('jane_server', '../..');

// Bing API Key
module.constant(
    'bing_key',
    'Ak-dzM4wZjSqTlzveKz5u0d4IQ4bRzVI309GxmkgSVr1ewS6iPSrOvOKhA-CJlm3');

// Colors for the different event agencies. From the color brewer website.
module.constant('event_agency_colors', [
    'rgba(31, 120, 180, 0.5)',
    'rgba(51, 160, 44, 0.5)',
    'rgba(227, 26, 28, 0.5)',
    'rgba(255, 127, 0, 0.5)',
    'rgba(106, 61, 154, 0.5)',
    'rgba(177, 89, 40, 0.5)',
    'rgba(166, 206, 227, 0.5)',
    'rgba(178, 223, 138, 0.5)',
    'rgba(251, 154, 153, 0.5)',
    'rgba(253, 191, 111, 0.5)',
    'rgba(202, 178, 214, 0.5)',
    'rgba(255, 255, 153, 0.5)']);

// Colors for the different event sites. From the color brewer website.
module.constant('event_site_colors', [
    'rgba(141, 211, 199, 0.5)',
    'rgba(190, 186, 218, 0.5)',
    'rgba(251, 128, 114, 0.5)',
    'rgba(128, 177, 211, 0.5)',
    'rgba(253, 180, 98, 0.5)',
    'rgba(179, 222, 105, 0.5)',
    'rgba(252, 205, 229, 0.5)',
    'rgba(217, 217, 217, 0.5)',
    'rgba(188, 128, 189, 0.5)',
    'rgba(204, 235, 197, 0.5)',
    'rgba(255, 255, 179, 0.5)',
    'rgba(255, 237, 111, 0.5)']);


module.constant('station_colors', [
    'rgba(0, 0, 255, 1.0)',
    '#ff7f00',
    '#1f78b4',
    '#a6cee3',
    '#33a02c',
    '#ff0000',
    '#e31a1c',
    '#fb9a99',
    '#fdbf6f']);


module.factory('current_user', function ($http) {
    return $http.get('/rest/current_user');
});


// Factory dealing with arbitrary geojson objects
module.factory('geojson', function($http, $log, jane_server) {
    return {
        geojson: {
            "type": "FeatureCollection",
            "features": []
        },
        update: function() {
            var self = this;
            var url = jane_server + "/rest/document_indices/geojson?limit=20000";
            $http.get(url).success(function(data) {
                var data = _(data.results)
                    .map(function(i) {
                        var j = i.indexed_data;
                        // Now create GeoJSON
                        var geojson = {
                            "type": "Feature",
                            "properties": j,
                            "geometry": JSON.parse(j.geometry_string),
                        };
                        return geojson;
                    }).value();
                // Update the event set.
                self.geojson.features.length = 0;
                _.forEach(data, function(i) {
                    self.geojson.features.push(i);
                });
            })
        }
    }
});


// Factory dealing with events.
module.factory('events', function($http, $log, jane_server) {
    return {
        events: {
            "type": "FeatureCollection",
            "features": []
        },
        update: function() {
            var self = this;
            var url = jane_server + "/rest/document_indices/quakeml?limit=20000";
            $http.get(url).success(function(data) {
                // Filter events to only keep those with a valid origin and
                // magnitude.
                var data = _(data.results)
                    .filter(function(i) {
                        if (!i.indexed_data.latitude && !i.indexed_data.longitude) {
                            return false;
                        }
                        if (i.indexed_data.magnitude === null) {
                            // Add flag that this magnitude is fake.
                            i.indexed_data.has_no_magnitude = true;
                        }
                        return true;
                    })
                    .map(function(i) {
                        var j = i.indexed_data;
                        j.id = i.id;
                        j.url = i.url;
                        j.origin_time = new Date(j.origin_time);
                        j.attachments = i.attachments;
                        j.containing_document_data_url = i.containing_document_data_url;
                        // Now create GeoJSON
                        var geojson = {
                            "type": "Feature",
                            "properties": j,
                            "geometry": {
                                "type": "GeometryCollection",
                                "geometries": [{
                                    "type": "Point",
                                    "coordinates": [j.longitude, j.latitude]},
                                    {
                                    "type": "MultiLineString",
                                    "coordinates": i.geometry.coordinates[1]}
                                ]}
                        };
                        return geojson;
                    }).value();
                // Update the event set.
                self.events.features.length = 0;
                _.forEach(data, function(i) {
                    self.events.features.push(i);
                });
            })
        }
    }
});

// Factory dealing with stations.
module.factory('stations', function($http, $log, jane_server) {
    return {
        stations: {
            "type": "FeatureCollection",
            "features": []
        },
        update: function() {
            var self = this;
            var url = jane_server + "/rest/document_indices/stationxml?limit=10000";
            $http.get(url).success(function(data) {
                var stations = {};
                _.forEach(data.results, function(item) {
                    var j = item.indexed_data;
                    var station_id = [j.network, j.station];

                    // Start- and end dates for the current channel.
                    var n_sd = new Date(j.start_date);
                    if (!j.end_date || (j.end_date == "None")) {
                        n_ed = null;
                    }
                    else {
                        n_ed = new Date(j.end_date);
                    }

                    // Station encountered the first time.
                    if (!_.has(stations, station_id)) {
                        stations[station_id] = {
                            "type": "Feature",
                            "properties": {
                                "network": j.network,
                                "network_name": j.network_name,
                                "station": j.station,
                                "station_name": j.station_name,
                                "latitude": j.latitude,
                                "longitude": j.longitude,
                                "channels": [],
                                "min_startdate": n_sd,
                                "max_enddate": n_ed
                            },
                            "geometry": {
                                "type": "Point",
                                "coordinates": [
                                    j.longitude, j.latitude
                                ]
                            }
                        };
                    }
                    // Station already exists. Now only the times have to be
                    // adjusted.
                    else {
                        // Make sure the minimum and maximum start and end
                        // dates of the station are consistent with the data.
                        var o_sd = stations[station_id].properties.min_startdate;
                        var o_ed = stations[station_id].properties.max_enddate;

                        // There should really always be a startdate.
                        if (n_sd < o_sd) {
                            stations[station_id].properties.min_startdate = n_sd;
                        }

                        // Only adjust if the endtime is set. If it is set it
                        // is already in the future.
                        if (o_ed) {
                            if (!n_ed) {
                                stations[station_id].properties.max_enddate = null;
                            }

                            else if (n_ed > o_ed) {
                                stations[station_id].properties.max_enddate = n_ed;
                            }
                        }
                    }
                    stations[station_id].properties.channels.push(item);
                });

                // Update the stations set.
                self.stations.features.length = 0;
                _.forEach(stations, function(i) {
                    self.stations.features.push(i);
                });

                // Do one last pass and figure out if the station is active
                // today.
                var today = new Date();
                _.forEach(stations, function(i) {
                    var sd = i.properties.min_startdate;
                    var ed = i.properties.max_enddate;

                    if (ed && ed < today) {
                        i.properties.is_active = false;
                    }
                    else {
                        i.properties.is_active = true;
                    }
                });
            })
        }
    }
});


module.controller("BayNetController", function($scope, $log, stations, station_colors,
                                               events, event_agency_colors,
                                               event_site_colors, current_user, geojson) {

    current_user.success(function (data) {
        $scope.current_user = data.username;
    })

    $scope.center = {
        latitude: 48.6,
        longitude: 11.5,
        zoom: 8
    };

    $scope.rotation = 0;
    $scope.base_layer_opacity = 40.0;

    $scope.show_bavaria_outline = false;

    // XXX: This has to be in sync with the base layer that has the default
    // visibility.
    $scope.current_base_layer = "OpenTopoMap";
    // The map directive will fill this with a list of available base layers.
    $scope.base_layer_names_dropdown = [];

    $scope.popover = {
        "content": "Hello Popover<br />This is a multiline message!",
        "saved": false
    };

    events.update();
    $scope.geojson_events = events.events;

    stations.update();
    $scope.geojson_stations = stations.stations;

    geojson.update();
    $scope.geojson_geojson = geojson.geojson;

    // Flags.
    $scope.show_event_layer = true;
    $scope.show_station_layer = true;
    $scope.show_geojson_layer = true;
    $scope.event_layer_show_points = true;

    var currentDate = new Date();
    currentDate.setDate(currentDate.getDate() + 1);

    $scope.event_settings = {
        "min_date": new Date("2000-01-01"),
        "max_date": currentDate,
        "magnitude_range": [-5, 10],
        "selected_agencies": [],
        "agency_colors": {},
        "agency_icons": [],
        "available_authors": [],
        "selected_authors": [],
        "available_sites": [],
        "selected_sites": [],
        "site_colors": {},
        "site_icons": [],
        "color_coding_switch": true,
        "show_public_and_private": true,
        "show_automatic_and_manual": true,
        "show_uncertainties": true,
    };

    $scope.station_settings = {
        "min_date": new Date("2000-01-01"),
        "max_date": currentDate,
        "grey_out_inactive_stations": true
    };

    $scope.geojson_settings = {
    };

    $scope.station_colors = {};

    $scope.$watchCollection("geojson_events.features", function(f) {
        // Get all unique agencies.
        var agencies = _.uniq(_.map(f, function(i) {
            return i.properties.agency;
        }));
        agencies.sort();

        // Distribute colors to the agencies..
        $scope.event_settings.agency_colors = {};
        for (var i = 0; i < agencies.length; i++) {
            $scope.event_settings.agency_colors[agencies[i]] =
                event_agency_colors[i % event_agency_colors.length];
        }

        // Set the available choices.
        $scope.event_settings.agency_icons = _.map(agencies, function(i) {
            return {
                value: i,
                label: '<i class="fa fa-circle" style="color:' +
                    $scope.event_settings.agency_colors[i] +
                    '"></i> ' + i}
        });

        $scope.event_settings.selected_agencies = [agencies[0]];

        // Get all unique sites.
        var sites = _.uniq(_.map(f, function(i) {
            return i.properties.site;
        }));
        sites.sort();

        // Distribute colors to the sites..
        $scope.event_settings.site_colors = {};
        for (var i = 0; i < sites.length; i++) {
            $scope.event_settings.site_colors[sites[i]] =
                event_site_colors[i % event_site_colors.length];
        }

        // Set the available choices.
        $scope.event_settings.site_icons = _.map(sites, function(i) {
            return {
                value: i,
                label: '<i class="fa fa-circle" style="color:' +
                    $scope.event_settings.site_colors[i] +
                    '"></i> ' + i}
        });

        $scope.event_settings.selected_sites = sites;

        // Get all authors.
        $scope.event_settings.selected_authors = _.uniq(_.map(f, function(i) {
            return i.properties.author;
        }));

        $scope.event_settings.available_authors = _.map($scope.event_settings.selected_authors, function(i){
            return {
                value: i,
                label: '<i class="fa fa-user"></i> ' + i
            }
        });

        $scope.event_settings.selected_authors.push("UNKNOWN");
        $scope.event_settings.available_authors.push({
            value: "UNKNOWN",
            label: "<i>unbekannt</i>"
        });


        $scope.event_settings.available_sites = _.map($scope.event_settings.selected_sites, function(i){
            return {
                value: i,
                label: '<i class="fa fa-user"></i> ' + i
            }
        });

        $scope.update_event_source(
            $scope.geojson_events,
            $scope.show_event_layer,
            $scope.event_layer_show_points,
            $scope.event_settings);
    });


    $scope.$watchCollection("geojson_stations.features", function(f) {
        var networks = _(f).map(function(i) {return i.properties.network})
                           .uniq().value();
        networks.sort();
        $scope.station_colors = {};
        _.forEach(networks, function(i, d) {
            $scope.station_colors[i] = station_colors[d % station_colors.length];
        });

        $scope.update_station_source(
            $scope.geojson_stations,
            $scope.show_station_layer,
            $scope.station_colors,
            $scope.station_settings);
    });


    $scope.$watchCollection("geojson_geojson.features", function(f) {
        $scope.update_geojson_source(
            $scope.geojson_geojson,
            $scope.show_geojson_layer,
            $scope.geojson_settings);
    });

    $scope.$watch("show_station_layer", function(new_value, old_value) {
        if (new_value == old_value) {
            return;
        }
        $scope.update_station_source(
            $scope.geojson_stations,
            $scope.show_station_layer,
            $scope.station_colors,
            $scope.station_settings);
    });


    $scope.$watch("event_layer_show_points", function(new_value, old_value) {
        if (new_value == old_value) {
            return;
        }
        $scope.update_event_source(
            $scope.geojson_events,
            $scope.show_event_layer,
            $scope.event_layer_show_points,
            $scope.event_settings);
    });

    $scope.$watch("show_event_layer", function(new_value, old_value) {
        if (new_value == old_value) {
            return;
        }
        $scope.update_event_source(
            $scope.geojson_events,
            $scope.show_event_layer,
            $scope.event_layer_show_points,
            $scope.event_settings);
    });

    $scope.$watch("show_geojson_layer", function(new_value, old_value) {
        if (new_value == old_value) {
            return;
        }
        $scope.update_geojson_source(
            $scope.geojson_geojson,
            $scope.show_geojson_layer,
            $scope.geojson_settings);
    });

    $scope.$watchCollection(
        "event_settings", function() {
            $scope.update_event_source(
                $scope.geojson_events,
                $scope.show_event_layer,
                $scope.event_layer_show_points,
                $scope.event_settings);
        }
    );

    $scope.$watchCollection(
        "station_settings", function() {
            $scope.update_station_source(
                $scope.geojson_stations,
                $scope.show_station_layer,
                $scope.station_colors,
                $scope.station_settings);
        }
    );

    $scope.$watchCollection(
        "geojson_settings", function() {
            $scope.update_geojson_source(
                $scope.geojson_geojson,
                $scope.show_geojson_layer,
                $scope.geojson_settings);
        }
    );

});
