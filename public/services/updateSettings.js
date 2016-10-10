// Sends http request to server to update the user settings 
myApp.factory('updateSettings', ['$http', 'userState', function ($http, userState) {
    var factory = {};
    
    factory.updateSettings = function() {
        return $http({
            method: 'POST',
            url: '/api/user/update/' + userState.user,
            headers: {
                'Content-Type': 'application/json'
            },
            data: { 
                settings: {
                    receives_title_updates: userState.settings.receives_title_updates,
                    alias: userState.settings.alias
                }
            }
        });
    };
    return factory;
}]);