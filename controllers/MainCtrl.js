// Takes care of the main, unauthorized view. The unauthorized view is very simple, 
//  mostly showing static data.
myApp.controller('MainCtrl', ['$scope', '$http', 'Auth', function ($scope, $http, Auth) {
    $scope.checkAuth = Auth.isAuthed; // Unsure if I am using this in the view
}]);