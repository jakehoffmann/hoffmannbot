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

myApp.controller('authController', ["$scope", "$http", "$location", "Auth", "state", 'editSummoners', function ($scope, $http, $location, Auth, state, editSummoners) {
    $scope.code = $location.search().code;
    $scope.code = state.code;
    $scope.summoners = state.summoners;
    $scope.user = state.user;
    $scope.auth = Auth.auth;
    $scope.inputSummoner = "new summoner";
    $scope.region = 'BR';

    $scope.add = function(twitch_username, summonerName) {
        editSummoners.editSummoners('add', twitch_username, summonerName)
        .then(
        function(response) {
            $scope.summoners.push(response.data.addedSummoner);
            console.log('response: ', response);
            console.log('added summoner: ', response.data.addedSummoner);
        },
        function(err) {
            console.error('Error response while trying to add summoner', err);
        });    
    };
    
    $scope.remove = function(twitch_username, summonerName) {
        editSummoners.editSummoners('remove', twitch_username, summonerName)
        .then(
        function(response) {    
            var index = $scope.summoners.indexOf(summonerName);
            $scope.summoners.splice(index, 1);
            console.log('response: ', response);
            console.log('removed summoner: ', response.data.removedSummoner);
        },
        function(err) {
           console.error('Error response while trying to remove summoner', err); 
        });
    };

    // is there a more compact way to do these?
    $scope.$watch('code', function() {
        state.code = $scope.code;
    });
    $scope.$watch('summoners', function() {
        state.summoners = $scope.summoners;
    });
    $scope.$watch('user', function() {
        state.user = $scope.user;
    });
       
    // if the user is returning from agreeing to give us access (ie. code is in query strings) ...
    if ($location.search().code) {
        $scope.code = $location.search().code;
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

/*
myApp.directive('subnav', function () {
   return {
       template: ,
       replace: true
   } 
});
*/

// Sends http request to server to add a summoner for a user
myApp.factory('editSummoners', ['$http', 'state', function ($http, state) {
    var factory = {};
    
    factory.editSummoners = function(action, twitch_username, summonerName) {
        return  $http({
                method: 'POST',
                url: '/api/summoner/'+action+'/'+twitch_username+'/'+summonerName,
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                data: 'code='+state.code
            });
    };
    return factory;
}]);

// sends oauth code to server (this is a work in progress, will replace the analogous 
//   http call in authController)

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






