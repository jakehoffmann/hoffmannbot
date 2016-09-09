var myApp = angular.module('myApp', ['ngRoute', 'ui.bootstrap']);

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
        controller: 'authController',
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
        controller: 'authController'
    })
});

myApp.controller('mainController', ['$scope', '$http', 'Auth', function ($scope, $http, Auth) {
    $scope.checkAuth = Auth.isAuthed;
}]);

myApp.controller('authController', ["$scope", "$http", "$location", "Auth", "state", 'addSummoner', function ($scope, $http, $location, Auth, state, addSummoner) {
    $scope.code = $location.search().code;
    $scope.code = state.code;
    $scope.summoners = state.summoners;
    $scope.user = state.user;
    $scope.auth = Auth.auth;
    $scope.inputSummoner = "new summoner name";

    $scope.add = function (twitch_username, summonerName) {
        addSummoner.addSummoner(twitch_username, summonerName)
        .then(
        function (response) {
            $scope.summoners.push(response.addedSummoner);
            console.log('added summoner: ', response.addedSummoner);
        },
        function (error) {
            console.error('Error response while trying to add summoner', error);
        });    
    };
    
    $scope.$watch('state', function() {
        state.code = $scope.code;
        state.summoners = $scope.summoners;
        state.user = $scope.user;
    });
       
    // if the user is returning from agreeing to give us access (ie. code is in query strings) ...
    if ($scope.code) {
        state.code = $scope.code;
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
            console.log('response: ', response.data);
            $scope.summoners = response.data.summoners;
            $scope.user = response.data.twitch_username;
        }, function errorCallback(response) {
            console.log('error sending request to server in authController')
        });
    }
    if (!Auth.isAuthed()) {
        $location.url('/login');
    } 
    console.log($scope.summoners);
}]);

myApp.factory('Auth', ['$location', 'state', function($location, state) {
    var code = '';
    return { 
        isAuthed: function () {
            if ($location.search().code) {
                code = $location.search().code;
                return true;
            }
            else if (state.code !== '') {
                code = state.code;
                return true;
            }
            else {
                return false;
            }
        },
        auth: function () {
                var client_id='49mrp5ljn2nj44sx1czezi44ql151h2',
                force_verify='true',
                scope='channel_editor+user_read',
                redirect_uri='http%3A%2F%2Fhoffmannbot.herokuapp.com%2F%23%2Fhoffmannbot%2Fget%2F',
                response_type='code',
                url='https://api.twitch.tv/kraken/oauth2/authorize?response_type='+response_type+'&force_verify='+force_verify+'&client_id='+client_id+'&redirect_uri='+redirect_uri+'&scope='+scope;
            window.location.replace(url); 
        }
}}]);

myApp.factory('state', function () {
    return {
        user: '',
        code: '',
        summoners: []
    }
});

myApp.factory('codeToServer', function () {
   return {
       
   } 
});

/*
myApp.directive('subnav', function () {
   return {
       template: ,
       replace: true
   } 
});
*/

// Sends http request to server to add a summoner for a user
myApp.factory('addSummoner', ['$http', 'state', function ($http, state) {
    var factory = {};
    
    factory.addSummoner = function(twitch_username, summonerName) {
        return  $http({
                method: 'POST',
                url: '/api/summoner/add/'+twitch_username+'/'+summonerName,
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                data: 'code='+state.code
            });
    };
    return factory;
}]);








