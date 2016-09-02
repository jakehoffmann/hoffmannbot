var express = require('express');
var router = express.Router();

/* GET home page. */
router.get('/', function(req, res, next) {
  res.render('index', { title: 'Express' });
});

router.post('/auth', function(req, res, next) {
    console.log('authorizing...');
    console.log('node code: ', req.body.code);
    
    var response = { 'twitch_username': '', 'summoners':[] };
    pool.connect(function(err, client, done) {
        if (err) {
            return console.error('error fetching client from pool', err);
        }
/*      client.query('SELECT twitch_username FROM users WHERE code=$1',
                     [req.body.code],
                     function(err, row) {
                        // done(); // maybe don't release client yet
                        if(err) {
                            return console.error('errur running query');
                        }
        }); */
        query = client.query('SELECT twitch_username, summoner, code FROM users INNER JOIN summoners ON (users.twitch_username = summoners.twitch_username) WHERE code=$1', [req.body.code]);
        query.on('row', function(row) {
            response['summoners'].push(row.summoner);
            response['twitch_username'] = row.twitch_username;
        });
        query.on('end', function(result) {
            if (result.rowCount === 0) {
                console.log('')
                // No such user found with this code. POST to Twitch for token and possibly make a new user
   
                /*
                request.post('https://api.twitch.tv/kraken/oauth2/token', function(error, response, body) {
                    if (!error && response.statusCode == 200) {
                        console.log(body);
                    }
                })
                */
                
               // I might have to send the redirect_uri unencoded
                request.post( { url:'https://api.twitch.tv/kraken/oauth2/token',
                                form: {client_id: '49mrp5ljn2nj44sx1czezi44ql151h2',
                                       client_secret: 'mz513m1xu5ga9mhrxuvb9sbwjgjw2ys',
                                       grant_type: 'authorization-code',
                                       redirect_uri: 'http://hoffmannbot.herokuapp.com/#/hoffmannbot/get/',
                                      //redirect_uri: 'http%3A%2F%2Fhoffmannbot.herokuapp.com%2F%23%2Fhoffmannbot%2Fget%2F',
                                       code: req.body.code}},
                                function(err,httpResponse,body){
                    if (err) {
                        console.log('error here 313');
                    }
                    console.log('BODY: ', body); // either this or the response should be the JSON token
                    console.log('response: ', httpResponse);
                    res.send(200); // need another response here, testing!
                });

                          
            }
            else {
                res.json(response);
            }
        });
    });
    
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
            res.send(200);
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
    res.json(response);

/*
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
*/
    
});

module.exports = router;
