var app = angular.module('bayNetApp');

app.directive('openlayers3', function($q, $log, bing_key, $modal) {
    return {
        restrict: 'EA',
        transclude: true,
        replace: true,
        scope: false,

        // Wrap in separate div element to gain full screen compatibility
        // without any further work.
        template: '<div><div ng-transclude style="height: 100%; width: 100%"></div></div>',

        controller: function($scope) {
            $scope.openlayers3Map = $q.defer();
            this.getMap = function() {
                return $scope.openlayers3Map.promise;
            };
        },

        link: function($scope, element, attrs) {
            var view = new ol.View({
                projection: 'EPSG:3857',
                center: __toMapCoods([$scope.center.longitude, $scope.center.latitude]),
                zoom: $scope.center.zoom,
                rotation: $scope.rotation
            });

            var map = new ol.Map({
                target: element[0].children[0],
                renderer: 'canvas',
                layers: [],
                view: view
            });

            // The base layers are treated as a group. Only one can be active
            // at any given time and they share their opacity setting.
            $scope.baseLayers = {
                "Stamen Toner-Lite": new ol.layer.Tile({
                    visible: true,
                    source: new ol.source.Stamen({layer: 'toner-lite'})
                }),
               
                "Stamen Toner": new ol.layer.Tile({
                    visible: false,
                    source: new ol.source.Stamen({layer: 'toner'})
                }),
                "Stamen Watercolor": new ol.layer.Tile({
                    visible: false,
                    source: new ol.source.Stamen({layer: 'watercolor'})
                }),
                // "MapQuest (Street)": new ol.layer.Tile({
                //     visible: false,
                //     source: new ol.source.MapQuest({layer: 'osm'})
                // }),
                // "MapQuest (Satellite)": new ol.layer.Tile({
                //     visible: false,
                //     source: new ol.source.MapQuest({layer: 'sat'})
                // }),
                "OpenTopoMap": new ol.layer.Tile({
                    visible: false,
                    source: new ol.source.OSM({
                        url: '//{a-c}.tile.opentopomap.org/{z}/{x}/{y}.png',
                        crossOrigin: null})
                }),
                "Open Street Map": new ol.layer.Tile({
                    visible: false,
                    source: new ol.source.OSM()
                }),
                "Open Street Map (Humanitarian)": new ol.layer.Tile({
                    visible: false,
                    source: new ol.source.OSM({
                        url: '//{a-c}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
                        crossOrigin: null
                    })
                }),
                "OSM EU TOPO (4umaps.eu)": new ol.layer.Tile({
                    visible: false,
                    source: new ol.source.OSM({
                        url: '//4umaps.eu/{z}/{x}/{y}.png',
                        crossOrigin: null
                    })
                // "Bing (Road)": new ol.layer.Tile({
                //     visible: false,
                //     source: new ol.source.BingMaps({
                //         key: bing_key,
                //         imagerySet: 'Road'
                //     })
                // }),
                // "Bing (Aerial)": new ol.layer.Tile({
                //     visible: false,
                //     source: new ol.source.BingMaps({
                //         key: bing_key,
                //         imagerySet: 'Aerial'
                //     })
                // }),
                // "Bing (Aerial with Labels)": new ol.layer.Tile({
                //     visible: false,
                //     source: new ol.source.BingMaps({
                //         key: bing_key,
                //         imagerySet: 'AerialWithLabels'
                //     })
                })
            };


            $scope.change_base_layer = function(layer_name) {
                $scope.current_base_layer = layer_name;
                _.forEach($scope.baseLayers, function(value, key) {
                    if (key == layer_name) {
                        value.setVisible(true);
                    }
                    else {
                        value.setVisible(false);
                    }
                })
            };

            $scope.change_station = function(station_id) {
              $scope.current_station = $scope.stations[station_id];
              $scope.event_settings.selected_station = parseInt(station_id, 10);
              $scope.station_settings.selected_station = parseInt(station_id, 10);

              // Update events based on the selected station
              $scope.update_event_source(
                  $scope.geojson_events,
                  $scope.show_event_layer,
                  $scope.event_layer_show_points,
                  $scope.event_settings);

              // Update stations based on the selected station
              $scope.update_station_source(
                  $scope.geojson_stations,
                  $scope.show_station_layer,
                  $scope.station_colors,
                  $scope.station_settings);
            };

            $scope.base_layer_names_dropdown = _($scope.baseLayers)
                .keys()
                .map(function(i) {
                    return {
                        "text": i,
                        "click": "change_base_layer('" + i + "')"}
                }).value();

            $scope.baseLayerGroup = new ol.layer.Group({
                layers: _.values($scope.baseLayers)
            });

            map.addLayer($scope.baseLayerGroup);


            // Layer showing the outline of bavaria.
            // var bavaria = new ol.layer.Vector({
            //     visible: $scope.show_bavaria_outline,
            //     source: new ol.source.Vector({
            //         url: 'bayern_topo.json',
            //         format: new ol.format.TopoJSON()
            //     }),
            //     style: function() {
            //         return [new ol.style.Style({
            //             fill: new ol.style.Fill({
            //                 color: 'rgba(255, 255, 255, 0.3)'
            //             }),
            //             stroke: new ol.style.Stroke({
            //                 color: '#319FD3',
            //                 width: 2
            //             })
            //         })];
            //     }
            // });
            // map.addLayer(bavaria);

            // $scope.$watch("show_bavaria_outline", function(new_value) {
            //     bavaria.setVisible(new_value);
            // });

            // Watch opacity and rotation value changes.
            $scope.$watch("base_layer_opacity", function(new_value) {
                // Workaround for bug with bootstrap slider.
                if (!new_value) {
                    new_value = 0.0;
                }
                new_value /= 100.0;
                $scope.baseLayerGroup.setOpacity(new_value);
            });

            $scope.$watch("rotation", function(new_value) {
                // Workaround for bug with bootstrap slider.
                if (!new_value) {
                    new_value = 0.0;
                }
                map.getView().setRotation(new_value / 180.0 * Math.PI);
            });

            var get_style_function_stations = function(colors) {
                var textStroke = new ol.style.Stroke({
                    color: '#444444',
                    width: 2.5
                });
                return function(feature, resolution) {
                    var net = feature.get('network');

                    var is_active = feature.get('is_active');

                    if (!is_active && $scope.station_settings.grey_out_inactive_stations){
                        var textFill = new ol.style.Fill({
                            color: "#999999"
                        });
                    } else {
                        var textFill = new ol.style.Fill({
                            color: "#e50000"
                        });
                    }

                    return [new ol.style.Style({
                        text: new ol.style.Text({
                            text: "▼",
                            font: '16px Calibri,sans-serif',
                            fill: textFill,
                            stroke: textStroke
                        })
                    })];
                };

            };

            var get_style_function = function(colors) {
                var styleCache = {};
                var styleFunction = function(feature, resolution) {

                    var stroke_color = "black";
                    var color;
                    var stroke_width = 1.0;
                    var magnitude;
                    var radius;
                    var tag;
                 
                    // Scale events from -3 to 8 from 1 to 30.0 pixel.
                    // Smallest possible value is 0.5.
                    // magnitude = parseFloat(feature.get('magnitude'));
                    // radius = Math.max(((magnitude + 3.0) / 11) * 29.0 + 1, 0.5);
                    // Scale events from 3 to 10 from 10 to 40.0 pixel.
                    // Smallest possible value is 5.5.
                    magnitude = parseFloat(feature.get('magnitude'));
                    radius = Math.sqrt(Math.max(((magnitude - 3.0) / 7) * 350.0, 20.0));
                    tag = radius;
                    

                    var style = styleCache[tag];
                    if (!style) {
                        // c = colors[feature.get('agency')];
                        style = [new ol.style.Style({
                            image: new ol.style.Circle({
                                radius: radius,
                                fill: new ol.style.Fill({
                                    color: "#ffb732"
                                }),
                                stroke: new ol.style.Stroke({
                                    color: stroke_color,
                                    width: stroke_width
                                })
                            })
                        })];
                        styleCache[radius] = style;
                    }
                    return style;
                };
                return styleFunction;
            };

            $scope.station_layer = {};

            $scope.update_station_source = function(feature_collection, show_layer, colors, station_settings) {
                if ($scope.station_layer) {
                    map.removeLayer($scope.station_layer);
                    $scope.station_layer = {};
                }
                if (show_layer === false) {
                    return;
                }

                // Filter events to apply the event settings.
                var stations = {
                    "type": "FeatureCollection",
                    "features": _.filter(feature_collection.features, function(i) {
                        if (i.properties.min_startdate) {
                            if (i.properties.min_startdate > station_settings.max_date) {
                                return false
                            }
                        }
                        if (i.properties.max_enddate) {
                            if (i.properties.max_enddate < station_settings.min_date) {
                                return false
                            }
                        }
                        // If selected station is a specific station, show only that station.
                        if (station_settings.selected_station !== $scope.default_station_id &&
                            (i.properties.id !== station_settings.selected_station)) {
                            return false;
                        }

                        return true
                    })
                };

                $scope.station_layer = new ol.layer.Vector({
                    source: new ol.source.Vector({
                        features: (new ol.format.GeoJSON()).readFeatures(stations, {
                            // Data is in WGS84.
                            dataProjection: "EPSG:4326",
                            // Map has a spherical mercator projection.
                            featureProjection: "EPSG:3857"
                        })
                    }),
                    style: get_style_function_stations(colors)
                });

                if (!_.isEmpty($scope.event_layer)) {
                    map.removeLayer($scope.event_layer);
                    map.addLayer($scope.event_layer);
                }
                map.addLayer($scope.station_layer);
            };

            $scope.event_layer = {};

            $scope.update_event_source = function(feature_collection, show_layer, show_points, event_settings) {
                // Filter events to apply the event settings.
                var events = {
                    "type": "FeatureCollection",
                    "features": _.filter(feature_collection.features, function(i) {
                        if ((i.properties.origin_time < event_settings.min_date) ||
                            (i.properties.origin_time > event_settings.max_date) ||
                            (i.properties.magnitude < event_settings.magnitude_range[0]) ||
                            (i.properties.magnitude > event_settings.magnitude_range[1]) ||
                            ((i.properties.depth_in_m / 1000.0) < event_settings.depth_range[0]) ||
                            ((i.properties.depth_in_m / 1000.0) > event_settings.depth_range[1])) {
                            return false;
                        }

                        // If selected station is a specific station, show only events recorded by that station.
                        if (event_settings.selected_station !== $scope.default_station_id &&
                            !_.contains(i.stations, event_settings.selected_station)) {
                            return false;
                        }

                        // Correlation is defined per station, so compare the range to the station(s) selected.
                        var min_pcc = Number.MAX_VALUE;
                        var max_pcc = Number.MIN_VALUE;

                        if (event_settings.selected_station === $scope.default_station_id) { // Any
                            // Select the most generous range based on the stations defined for this event.
                            // Thus, the event will be shown if any station falls within the selected range.
                            if (typeof i.properties.rlas_pcc !== 'undefined') {
                                min_pcc = Math.min(i.properties.rlas_pcc, min_pcc);
                                max_pcc = Math.max(i.properties.rlas_pcc, max_pcc);
                            }
                            if (typeof i.properties.romy_pcc !== 'undefined') {
                                min_pcc = Math.min(i.properties.romy_pcc, min_pcc);
                                max_pcc = Math.max(i.properties.romy_pcc, max_pcc);
                            }
                            if (typeof i.properties.bspf_pcc !== 'undefined') {
                                min_pcc = Math.min(i.properties.bspf_pcc, min_pcc);
                                max_pcc = Math.max(i.properties.bspf_pcc, max_pcc);
                            }
                        }
                        else if ($scope.stations[event_settings.selected_station].indexOf('BW.ROMY') !== -1) { // ROMY
                            min_pcc = i.properties.romy_pcc;
                            max_pcc = i.properties.romy_pcc;
                        }
                        else if ($scope.stations[event_settings.selected_station].indexOf('BW.RLAS') !== -1) { // RLAS
                            min_pcc = i.properties.rlas_pcc;
                            max_pcc = i.properties.rlas_pcc;
                        }
                        else if ($scope.stations[event_settings.selected_station].indexOf('PY.BSPF') !== -1) { // BSPF
                            min_pcc = i.properties.bspf_pcc;
                            max_pcc = i.properties.bspf_pcc;
                        }

                        // Hide events that do not fall within the selected correlation range.
                        if ((max_pcc < event_settings.correlation_range[0]) ||
                            (min_pcc > event_settings.correlation_range[1])) {
                            return false;
                        }

                        return true;
                    })
                };

                if ($scope.event_layer) {
                    map.removeLayer($scope.event_layer);
                    $scope.event_layer = {};
                }

                if (show_layer === false) {
                    return;
                }

                var event_source = new ol.source.Vector({
                    features: (new ol.format.GeoJSON()).readFeatures(events, {
                        // Data is in WGS84.
                        dataProjection: "EPSG:4326",
                        // Map has a spherical mercator projection.
                        featureProjection: "EPSG:3857"
                    })
                });

                if (show_points === false) {
                    $scope.event_layer = new ol.layer.Heatmap({
                        source: event_source
                    });
                }
                else {
                    $scope.event_layer = new ol.layer.Vector({
                        source: event_source,
                        style: get_style_function(event_settings.agency_colors)
                    });
                }

                map.addLayer($scope.event_layer);
                if (!_.isEmpty($scope.station_layer)) {
                    map.removeLayer($scope.station_layer);
                    map.addLayer($scope.station_layer);
                }
            };

            $scope.panTo = function(lng, lat, zoom) {
                var point = ol.proj.transform([lng, lat], 'EPSG:4326', 'EPSG:3857');
                var view = map.getView();

                var pan = ol.animation.pan({
                    duration: 0,
                    source: view.getCenter()
                });
                map.beforeRender(pan);
                view.setCenter(point);
                view.setZoom(zoom);
            };

            // Add controls to map.
            map.addControl(new ol.control.FullScreen({
            }));

            map.addControl(new ol.control.ScaleLine({
            }));

            map.addControl(new ol.control.ZoomSlider());



            // a DragBox interaction used to select features by drawing boxes
            var dragBox = new ol.interaction.DragBox({
                condition: ol.events.condition.shiftKeyOnly

            });

            map.addInteraction(dragBox);

            dragBox.on('boxend', function(e) {
                var extent = dragBox.getGeometry().getExtent();

                var events_to_download = [];
                $scope.event_layer.getSource().forEachFeatureIntersectingExtent(extent, function(feature) {
                    events_to_download.push(feature.get("containing_document_data_url").replace('marum.geophysik.uni-muenchen.de:8080', 'rotations-database.geophysik.uni-muenchen.de'));
                });

                if (events_to_download.length > 0) {
                    // Open modal to show download dialog.
                    var modal = $modal({
                        title: "Downloading " + events_to_download.length + " events ...",
                        template: "./templates/download_events_modal.tpl.html",
                        persist: false,
                        show: true});
                    // Set scope of modal.
                    modal.$scope.events_to_download = events_to_download;
                }
            });

            var detectFeatureType = function(feature) {
                if (feature.get('network')) {
                    return "station"
                }
                return "event"
            };

            var displayFeatureInfo = function(map_pixel, browser_pixel) {
                var event_info = $('#event_tooltip');

                event_info.tooltip({
                    animation: false,
                    title: 'Event',
                    trigger: 'manual'
                });

                event_info.css({
                    left: browser_pixel[0] + 'px',
                    top: (browser_pixel[1] - 15) + 'px'
                });

                var feature = map.forEachFeatureAtPixel(map_pixel, function(feature, layer) {
                    return feature;
                });

                if (feature) {
                    if (detectFeatureType(feature) == "event") {
                        var tooltip_title = feature.get("region") + "\n";
                        var catalog = feature.get('catalog');
                        if (catalog == null) {
                            catalog = "not specified";
                        }
                        tooltip_title += 'Catalog: ' + catalog;

                        // var author = feature.get("author");
                        // if (author == null) {
                        //     author = "not specified"
                        // }

                        // var evaluation_mode = feature.get("evaluation_mode");
                        // if (evaluation_mode == null) {
                        //     evaluation_mode = "not specified"
                        // }

                        // var public = feature.get("public");
                        // if (public == null) {
                        //     public = "not specified"
                        // }

                        // tooltip_title += "\nAgency: " + feature.get("agency") +
                        //     " | Author: " + author + " | Evaluation mode: " + evaluation_mode +
                        //     " | Public: " + public;

                        if (feature.get('magnitude')) {

                            if (feature.get('has_no_magnitude')) {
                                tooltip_title += '\nMagnitude: not available';
                            }
                            else {
                                tooltip_title += '\nMagnitude: ' + feature.get('magnitude').toFixed(1);
                            }

                            if (feature.get('magnitude_type')) {
                                tooltip_title += " " + feature.get('magnitude_type');
                            }
                        }

                        tooltip_title += "\n" + feature.get('origin_time');

                        tooltip_title += "\nLat: " + feature.get('latitude').toFixed(4) +
                            " | Lng: " + feature.get('longitude').toFixed(4) +
                            " | Depth: " + (feature.get('depth_in_m') / 1000).toFixed(1) + " km";
                    }
                    else {
                        tooltip_title = 'Station ' + feature.get('network') +
                            '.' + feature.get('station') +
                            '\n' + feature.get('station_name') + ', ' + feature.get('network_name') +
                            '\n' + 'Lat: ' + feature.get('latitude') + ' | Lng: ' + feature.get('longitude') + 
                            '\n'
                            // + feature.get('channels').length +
                            // ' channels across timespans';
                    }

                    event_info.tooltip('hide')
                        .attr('data-original-title', tooltip_title)
                        .tooltip('fixTitle')
                        .tooltip('show');
                }
                else {
                    event_info.tooltip('hide');
                }
            };

            $(map.getViewport()).on('mousemove', function(evt) {
                displayFeatureInfo(
                    map.getEventPixel(evt.originalEvent),
                    [evt.pageX, evt.pageY]
                );
            });

            $scope.show_info = function(pixel) {
                var event_info = $('#event_tooltip');
                event_info.tooltip('hide');

                var feature = map.forEachFeatureAtPixel(pixel, function(feature, layer) {
                    return feature;
                });

                if (feature) {
                    if (detectFeatureType(feature) == "event") {
                        var modal = $modal({
                            title: feature.get("region"),
                            template: "./templates/event_modal.tpl.html",
                            persist: false,
                            show: true});

                        // Set scope of modal.
                        modal.$scope.attachments_url = feature.get("attachments_url").replace('marum.geophysik.uni-muenchen.de:8080', 'rotations-database.geophysik.uni-muenchen.de');
                        modal.$scope.attachments_count = feature.get("attachments_count");
						modal.$scope.containing_document_data_url = feature.get("containing_document_data_url").replace('marum.geophysik.uni-muenchen.de:8080', 'rotations-database.geophysik.uni-muenchen.de');
                        modal.$scope.url = feature.get("url").replace('marum.geophysik.uni-muenchen.de:8080', 'rotations-database.geophysik.uni-muenchen.de');
                        modal.$scope.agency = feature.get("agency");
                        modal.$scope.author = feature.get("author");
                        modal.$scope.depth_in_m = feature.get("depth_in_m");
                        modal.$scope.evaluation_mode = feature.get("evaluation_mode");
                        modal.$scope.event_type = feature.get("event_type");
                        modal.$scope.catalog = feature.get("catalog");
                        modal.$scope.region = feature.get("region");
                        modal.$scope.latitude = feature.get("latitude");
                        modal.$scope.longitude = feature.get("longitude");
                        modal.$scope.magnitude = feature.get("magnitude");
                        modal.$scope.magnitude_type = feature.get("magnitude_type");
                        modal.$scope.origin_time = feature.get("origin_time");
                        modal.$scope.public = feature.get("public");
                        modal.$scope.quakeml_id = feature.get("quakeml_id");


                    }
                    else {
                        net = feature.get('network');
                        sta = feature.get('station');
                        var modal = $modal({
                            title: "Station " + net + "." + sta,
                            template: "./templates/station_modal.tpl.html",
                            persist: false,
                            show: true});
                        // Set scope of modal.
                        modal.$scope.network = net;
                        modal.$scope.station = sta;
                    }
                }
            };

            map.on('click', function(evt) {
                $scope.show_info(evt.pixel);
            });

        }
    };
});
