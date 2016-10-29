// Takes care of the main, unauthorized view. The unauthorized view is very simple, mostly showing static data.
myApp.controller('MainCtrl', ['$scope', '$http', '$uibModal', '$route', '$sce', 'auth',
                              function ($scope, $http, $uibModal, $route, $sce, auth) {
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
//    $scope.getLive = function () { return String(currentlyLiveStreams.length) }
    
    $scope.getIframeSrc = function (channel) {
        return $sce.trustAsResourceUrl('https://player.twitch.tv/?autoplay=false&muted=true&channel=' + channel);
    }
    
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