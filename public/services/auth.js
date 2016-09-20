myApp.factory('auth', ['$location', '$window', 'userState', function($location, $window, userState) {
    var code = '';
    return { 
        isAuthed: function () {
            if ($location.search().code) {
                code = $location.search().code;
                return true;
            }
            else if (userState.code !== '') {
                code = userState.code;
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
            $window.location.replace(url); 
        }
}}]);