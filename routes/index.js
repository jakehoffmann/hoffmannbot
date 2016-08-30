var express = require('express');
var router = express.Router();

/* GET home page. */
router.get('/', function(req, res, next) {
  res.render('index', { title: 'Express' });
});

router.post('/api/add/:user', function(req, res, next) {
    console.log('here 1');

    pool.connect(function(err, client, done) {
        if (err) {
            return console.error('error fetching client from pool' , err);
        }
        client.query('INSERT INTO users (twitch_username) VALUES (?)', [req.params.user], function(err, result) {
            done();
            if(err) {
                return console.error('error running query');
            }
            console.log('inserted twitch username ', req.params.user);
        });
    });
});

router.post('/api/summoner/:action/:user/:summoner', function(req, res, next) {
    console.log('here 2');

    pool.connect(function(err, client, done) {
        if (err) {
            return console.error('error fetching client from pool', err);
        } 
        if ( req.params.action == 'add' ) {
            client.query('INSERT INTO summoners (twitch_username,summoner) VALUES (?,?)', [req.params.user, req.params.summoner], function(err, result) {
                done();
                if(err) {
                    return console.error('error running query');
                }
            });
            res.send(200);
        }
        else if ( req.params.action == 'remove' ) {
            client.query('DELETE FROM summoners WHERE twitch_username=? AND summoner=?', [req.params.user, req.params.summoner], function(err, result) {
                done();
                if(err) {
                    return console.error('error running query');
                }
            });
            res.send(200);
        }
    })
});

router.get('/api/read/:user', function(req, res, next) {
    console.log('here 3');
    
    response = {"summoners":[]};
    pool.connect(function(err, client, done) {
        if (err) {
            return console.error('error fetching client from pool', err);
        }
        query = client.query('SELECT summoner FROM summoners WHERE twitch_username=?', [req.params.user]);
        query.on('row', function(row) {
            response["summoners"].push(row.summoner);
        })
        done();
    })
    
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

module.exports = router;
