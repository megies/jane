var baynetApp = angular.module("bayNetApp");


baynetApp.controller('eventInfoController', function($scope, $log) {
	if (!$scope.attachments_count) {
        return;
    }

    // Download attachments info at the time the modal is opened.
    jQuery.ajax({
        url: $scope.attachments_url.replace('marum.geophysik.uni-muenchen.de', 'erde.geophysik.uni-muenchen.de:8088'),
        success: function (result) {
            $scope.attachments = result.results;
        },
        async: false
    });
});
