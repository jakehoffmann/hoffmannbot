// Gets live streams that are using HoffmannBot
myApp.factory('getLiveStreams', ['$http', function ($http) {
    var factory = {};
    
    factory.getLiveStreams = function() {
        console.log('Getting live streams...')
        return $http({
               method: 'GET',
               url: '/livestreams',
        });
    };
    
    return factory;
}]);