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

myApp.controller('authController', ["$scope", "$http", "$location", "$routeParams", "Auth", function ($scope, $http, $location, $routeParams, Auth) {
    console.log('code = ', $location.search().code);
    console.log('code = ', $routeParams.code);
    if ($location.search().code) {
        localStorage.setItem('code', $location.search().code);
        // POST code to server so a token can be retrieved from Twitch
        
    }
    if (!Auth.isAuthed()) {
        $location.url('/login');
    } 
    $scope.auth = Auth.auth;
}]);

myApp.factory('Auth', function() {
    var code;
    return { 
        isAuthed: function () {
            code = localStorage.getItem('code') || '';
            if ( code === '' ) {
                return false;
            }
            else {
                return true;
            }
        },
        auth: function () {
            var client_id='49mrp5ljn2nj44sx1czezi44ql151h2',
                force_verify='true',
                scope='channel_editor',
                redirect_uri='http://hoffmannbot.herokuapp.com/#/hoffmannbot/get',
                response_type='code',
                url='https://api.twitch.tv/kraken/oauth2/authorize?response_type='+response_type+'&force_verify='+force_verify+'&client_id='+client_id+'&redirect_uri='+redirect_uri+'&scope='+scope;
            window.location.replace(url); 
        }
}});
