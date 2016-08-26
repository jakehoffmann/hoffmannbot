var express = require('express');
var router = express.Router();

var sqlite3 = require('sqlite3').verbose();

/* GET home page. */
router.get('/', function(req, res, next) {
  res.render('index', { title: 'Express' });
});

router.post('/api/add/:user', function(req, res, next) {
    console.log('here 1');
    var db = new sqlite3.Database('testdb.db');  
    db.serialize(function() { 
        db.run("INSERT INTO users (twitch_username) VALUES (?)", req.params.user);
        res.send(200);
    });
    db.close();
});

router.post('/api/:action/:user/:summoner', function(req, res, next) {
    console.log('here 2');
    var db = new sqlite3.Database('testdb.db');
    if ( req.params.action == 'add' ) {
        db.serialize(function() {
            db.run("INSERT INTO summoners (twitch_username,summoner) VALUES (?,?)", req.params.user,
                   req.params.summoner); 
        });
        res.send(200);
    }
    else if ( req.params.action == 'remove' ) {
        db.serialize(function() {
            db.run("DELETE FROM summoners WHERE twitch_username=? AND summoner=?", req.params.user, req.params.summoner);  
        });      
        res.send(200);
    }
    else {
        next();
    }
    db.close();
});

router.get('/api/read/:user', function(req, res, next) {
    console.log('here 3');
    response = {"summoners":[]};
    var db = new sqlite3.Database('testdb.db');
    db.serialize(function() { 
        db.each("SELECT summoner FROM summoners WHERE twitch_username=?", 
                req.params.user, 
                function(err, row) {
                    response["summoners"].push(row.summoner);  
                },
                function() {
                    res.json(response);
                })
    });
    db.close();
    
});

router.get('/test', function(req, res, next) {
    console.log('got to test');
    res.send('you are on the test page. congrats idiot!');
});

module.exports = router;
