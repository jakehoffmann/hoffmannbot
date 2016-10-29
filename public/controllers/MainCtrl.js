// Takes care of the main, unauthorized view. The unauthorized view is very simple, mostly showing static data.
myApp.controller('MainCtrl', ['$scope', '$http', '$uibModal', '$route', '$sce', 'auth', 'getLiveStreams',
                              function ($scope, $http, $uibModal, $route, $sce, auth, getLiveStreams) {
    $scope.checkAuth = auth.isAuthed; // Unsure if I am using this in the view
    $scope.$route = $route; 
    $scope.screenshots = [{
                              src: '/images/lastcommand.png',
                              desc: 'Displays stats from your last game in chat'
                          }, 
                          {
                              src: '/images/titleupdate.png',
                              desc: 'Updates your title with your in-game info'
                          },
                          {
                              src: '/images/rankcommand.png',
                              desc: 'Displays the ranks of all your registered accounts'
                          },
                          {
                              src: '/images/currentcommand.png',
                              desc: 'Shows what you are currently playing, as well as (optionally) your runes and the bans for the game'
                          }
                          ] 
 
    $scope.currentlyLiveStreams = []//{name: 'jakehoffmann'}, {name: 'tsm_dyrus'}]
    
    $scope.getIframeSrc = function (channel) {
        return $sce.trustAsResourceUrl('https://player.twitch.tv/?autoplay=false&muted=true&channel=' + channel);
    }
    
    $scope.getStreams = function() {
        getLiveStreams.getLiveStreams()
        .then(
        function(response) {
            $scope.currentlyLiveStreams = response.data;
            console.log('response: ', response);
            console.log('how many live streams?: ', $scope.currentlyLiveStreams.length);
            return $scope.currentlyLiveStreams.length;
        },
        function(err) {
            console.error('Error in angular while trying to get live streams.', err);
            return false;
        });
    };
    
    $scope.openModal = function(src) {
        $uibModal.open({
            templateUrl: 'modals/modalImage.html',
//            size: 'lg',
            controller: ["$scope", "imgSrc", function($scope, imgSrc) {
                $scope.imgSrc = imgSrc;
            }],
            resolve: {
                imgSrc: function () {
                    return src;
                }
            }
        });  
    }
}]);