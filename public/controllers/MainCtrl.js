// Takes care of the main, unauthorized view. The unauthorized view is very simple, 
//  mostly showing static data.
myApp.controller('MainCtrl', ['$scope', '$http', 'auth', function ($scope, $http, auth) {
    $scope.checkAuth = auth.isAuthed; // Unsure if I am using this in the view
}]);