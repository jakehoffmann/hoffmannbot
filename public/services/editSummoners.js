// Sends http request to server to add a summoner for a user
myApp.factory('editSummoners', ['$http', 'userState', function ($http, userState) {
    var factory = {};
    
    factory.editSummoners = function(action, twitch_username, summonerName, region) {
        return  $http({
                method: 'POST',
                url: '/api/summoner/'+action+'/'+twitch_username+'/'+summonerName+'/'+region,
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                data: 'code='+userState.code
            });
    };
    return factory;
}]);