var baynetApp = angular.module("bayNetApp");


baynetApp.controller('eventDownloadController', function($scope, $log) {
    $scope.total_count = $scope.events_to_download.length;
    $scope.progress = 0;
    $scope.width = 0;

    var zip = new JSZip();

    function aj(url) {
        return $.ajax({
            url: url.replace('marum.geophysik.uni-muenchen.de', 'erde.geophysik.uni-muenchen.de:8088'),
            success: function(data) {
                var filename = url.split("/");
                filename = filename[filename.length - 2];
                zip.file(filename, new XMLSerializer().serializeToString(data));
                $scope.progress += 1;
                $scope.width = $scope.progress/ $scope.total_count * 100.0;
                $scope.$apply();

                if ($scope.progress == $scope.total_count) {
                    var blob = zip.generate({type: "blob"});
                    saveAs(blob, "event_collection.zip");
                }
            }
        });
    }

    $scope.download = function() {
        //Create call $.when( url1, url2, url3 )
        var defer = $.when.apply($, $.map($scope.events_to_download, aj));

        defer.pipe(function() {
            //Return data instead of success arguments
            // (data,status,browser ajax obj)
            return $.map(arguments, function(n, i) {
                return n[0];
            });
        });
    }
});
