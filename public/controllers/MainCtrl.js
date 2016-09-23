// Takes care of the main, unauthorized view. The unauthorized view is very simple, mostly showing static data.
myApp.controller('MainCtrl', ['$scope', '$http', '$uibModal', 'auth',
                              function ($scope, $http, $uibModal, auth) {
    $scope.checkAuth = auth.isAuthed; // Unsure if I am using this in the view
    $scope.screenshots = ['/images/lastcommand.png', '/images/test.png']                                  
    $scope.openModal = function(src) {
        $uibModal.open({
            templateUrl: 'modals/modalImage.html',
            size: 'lg',
            controller: ["$scope", "imgSrc", function($scope, imgSrc) {
                $scope.imgSrc = imgSrc;
            }],
            resolve: {
                imgSrc: function () {
                    return src;
                }
            }
        });  
    }
}]);