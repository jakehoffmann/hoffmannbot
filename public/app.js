var myApp = angular.module('myApp', ['ngRoute']);

myApp.config(function ($routeProvider) {
    
    $routeProvider
    .when('/', {
        templateUrl: 'pages/home.html',
        controller: 'mainController'
    })
    .when('/hoffmannbot/', {
        templateUrl: 'pages/hoffmannbot.html',
        controller: 'mainController'
    })
    .when('/contact/', {
        templateUrl: 'pages/contact.html',
        controller: 'mainController'
    })
    .when('/hoffmannbot/get/', {
        templateUrl: 'pages/get.html',
        controller: 'authController'
    })
    .when('/hoffmannbot/commands', {
        templateUrl: 'pages/commands.html',
        controller: 'mainController'
    })
    .when('/hoffmannbot/about', {
        templateUrl: 'pages/about.html',
        controller: 'mainController'
    })
    .when('/login', {
        templateUrl: 'pages/login.html',
        controller: 'mainController'
    })
});

myApp.controller('mainController', ["$scope", "$http", function ($scope, $http) {
    
}]);

myApp.controller('authController', ["$scope", "$http", "$location", "Auth", function ($scope, $http, $location, Auth) {
    $scope.code = $location.search().code;
    console.log('code = ', $scope.code);
    console.log($location.url());
    if ($scope.code) {
        localStorage.setItem('code', $scope.code);
        // POST code to server so a token can be retrieved from Twitch and used to access authed users data
        $http({
            method: 'POST',
            url: '/auth',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            data: 'code='+$scope.code
        }).then(function successCallback(response) {
            console.log('success response');
        }, function errorCallback(response) {
            console.log('error sending request to server in authController')
        });
    }
    if (!Auth.isAuthed()) {
        $location.url('/login');
    } 
    $scope.auth = Auth.auth;
}]);

myApp.factory('Auth', ['$location', function($location) {
    var code = '';
    return { 
        isAuthed: function () {
            if ($location.search().code) {
                code = $location.search().code;
                return true;
            }
            else if (localStorage.getItem('code')) {
                code = localStorage.getItem('code');
                return true;
            }
            else {
                return false;
            }
        },
        auth: function () {
                var client_id='49mrp5ljn2nj44sx1czezi44ql151h2',
                force_verify='true',
                scope='channel_editor',
                redirect_uri='http%3A%2F%2Fhoffmannbot.herokuapp.com%2F%23%2Fhoffmannbot%2Fget%2F',
                response_type='code',
                url='https://api.twitch.tv/kraken/oauth2/authorize?response_type='+response_type+'&force_verify='+force_verify+'&client_id='+client_id+'&redirect_uri='+redirect_uri+'&scope='+scope;
            window.location.replace(url); 
        }
}}]);
