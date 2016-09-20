// maintains the user state
myApp.factory('userState', function () {
    return {
        user: '',
        code: '',
        summoners: [] // array of objects with properties 'summoner', and 'region'
    }
});