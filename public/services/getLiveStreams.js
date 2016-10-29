// Gets live streams that are using HoffmannBot
myApp.factory('getLiveStreams', ['$http', function ($http) {
    var factory = {};
    
//    factory.currentlyLiveStreams = []
//    factory.getLiveStreams = function() {
//        console.log('Getting live streams...')
//        return $http({
//               method: 'GET',
//               url: '/livestreams'
//        });
//    };
    
    factory.getLiveStreams = function() {
        console.log('getting live streams #2');
        $http({
            method: 'GET',
            url: '/livestreams'
        }).then(
            function(response) {
                console.log('response.data:', response.data);
                return response.data;
            },
            function(err) {
                console.error('error retrieving livestreams in angular', err);
            }
        );
    }
    
    return factory;
}]);