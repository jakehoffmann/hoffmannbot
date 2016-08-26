var express = require('express');
var router = express.Router();

// my test router
router.get('/', function(req, res, next) {
   res.send('ahhh idk') 
});

module.exports = router;