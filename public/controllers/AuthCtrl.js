// Provides functionality for the login/authorized view.
myApp.controller('AuthCtrl', ["$scope", "$http", "$location", "$route", "auth", "userState", 'editSummoners', 'updateSettings', function ($scope, $http, $location, $route, auth, userState, editSummoners, updateSettings) {
    // sort out this code thing!
    $scope.code = $location.search().code;
    $scope.code = userState.code;
    
    $scope.summoners = userState.summoners;
    $scope.user = userState.user;
    $scope.settings = userState.settings;

    $scope.auth = auth.auth;

    $scope.inputSummoner = "new summoner";
    $scope.region = 'NA';
    $scope.inputAlias = "Your alias"
    
    $scope.currentlyLiveStreams = [{name: 'jakehoffmann'}]
    $scope.getLive = function () { return String(currentlyLiveStreams.length) }
    
    $scope.$route = $route; 

    $scope.alerts = [
        {type: 'danger', msg: 'Please remember to type /mod hoffmannbot in your twitch chat!'}
    ];
    
    $scope.closeAlert = function(index) {
        $scope.alerts.splice(index, 1);
    };
    
    $scope.repeatEntry = function () {
        var filteredSummoner = $scope.inputSummoner.toLowerCase().replace(/\s+/g, '');
        for (var i = 0; i < $scope.summoners.length; i++) {
            if ($scope.summoners[i].summoner == filteredSummoner &&
                $scope.summoners[i].region == $scope.region) {
                return true;
            }
        }
    }

    $scope.add = function(twitch_username, summonerName, region) {
        editSummoners.editSummoners('add', twitch_username, summonerName, region)
        .then(
        function(response) {
            $scope.summoners.push({'summoner': response.data.addedSummoner,
                                   'region': response.data.region
                                  });
            console.log('response: ', response);
            console.log('added summoner, region: ',
                        response.data.addedSummoner, ', ', response.data.region);
        },
        function(err) {
            console.error('Error response while trying to add summoner', err);
        });    
    };
    
    $scope.remove = function(twitch_username, summonerName, region) {
        editSummoners.editSummoners('remove', twitch_username, summonerName, region)
        .then(
        function(response) {    
//            var index = $scope.summoners.indexOf({'summoner': response.data.removedSummoner, 'region': response.data.region});
            var index;
            for (var i = 0; i < $scope.summoners.length; i++) {
                if ( $scope.summoners[i].summoner == response.data.removedSummoner && $scope.summoners[i].region == response.data.region ) {
                    index = i;
                    break;
                }
            }
            $scope.summoners.splice(index, 1);
            console.log('response: ', response);
            console.log('removed summoner: ', response.data.removedSummoner, ', ', response.data.region);
        },
        function(err) {
           console.error('Error response while trying to remove summoner', err); 
        });
    };
    
    $scope.getAlias = function() {
        console.log('user state: ', userState);
        if (userState.settings.alias === 'noalias' || !userState.settings.alias) {
            return userState.user;
        }
        else {
            return userState.settings.alias;
        }
    };
    
    $scope.updateSettings = updateSettings.updateSettings;

    // is there a more compact way to do these?
    $scope.$watch('code', function() {
        userState.code = $scope.code;
    });
    $scope.$watch('summoners', function() {
        userState.summoners = $scope.summoners;
    });
    $scope.$watch('user', function() {
        userState.user = $scope.user;
    });
    $scope.$watch('settings', function() {
        userState.settings = $scope.settings; 
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
            $scope.settings = response.data.settings;
        }, function errorCallback(response) {
            console.log('error sending request to server in AuthCtrl')
        });
    }
    if (!auth.isAuthed()) {
        $location.url('/login');
    } 
    console.log($scope.summoners);
}]);