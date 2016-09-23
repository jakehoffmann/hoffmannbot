var myApp = angular.module('myApp', ['ngRoute', 'ui.bootstrap']);

myApp.config(function ($routeProvider) {
    
    $routeProvider
    .when('/', {
        templateUrl: 'pages/home.html',
        controller: 'MainCtrl'
    })
    .when('/hoffmannbot/', {  // removed this route as it was not useful!
        templateUrl: 'pages/hoffmannbot.html',
        controller: 'MainCtrl'
    })
    .when('/contact/', {
        templateUrl: 'pages/contact.html',
        controller: 'MainCtrl'
    })
    .when('/hoffmannbot/get/', {
        templateUrl: 'pages/get.html',
        controller: 'AuthCtrl',
    })
    .when('/hoffmannbot/commands', {
        templateUrl: 'pages/commands.html',
        controller: 'MainCtrl'
    })
    .when('/hoffmannbot/about', {
        templateUrl: 'pages/about.html',
        controller: 'MainCtrl'
    })
    .when('/login', {
        templateUrl: 'pages/login.html',
        controller: 'AuthCtrl'
    })
//    .when('/support/', {
//        templateUrl: 'pages/support.html',
//        controller: 'MainCtrl'
//    })
});

// sends oauth code to server (this is a work in progress, will replace the analogous 
//   http call in AuthCtrl)

/*
myApp.factory('sendCode', ['$http', function ($http) {
    var factory = {};
    
    factory.sendCode = function(code) {
        return $http({
            method: 'POST',
            url: '/auth',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            data: 'code='+$scope.code
        });
    };
    return factory;
}]);
*/
