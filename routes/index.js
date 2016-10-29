var express = require('express');
var router = express.Router();
var url = require('url');
var request = require('request');
var pg = require('pg');
// postgres config, parse the heroku-provided env variable DATABASE_URL
var params = url.parse(process.env.DATABASE_URL);
var auth = params.auth.split(':');

var config = {
  user: auth[0],
  password: auth[1],
  host: params.hostname,
  port: params.port,
  database: params.pathname.split('/')[1],
  ssl: true
};
var pool = new pg.Pool(config);
pool.on('error', function (err, client) {
  // if an error is encountered by a client while it sits idle in the pool
  // the pool itself will emit an error event with both the error and
  // the client which emitted the original error
  // this is a rare occurrence but can happen if there is a network partition
  // between your application and the database, the database restarts, etc.
  // and so you might want to handle it and at least log it out
    console.error('idle client error', err.message, err.stack);
})

/* GET home page. */
router.get('/', function(req, res, next) {
  res.render('index', { title: 'Express' });
});

router.get('/riot.txt', function(req, res, next) {
   res.send('public/riot.txt')
});

// This endpoint takes care of server side oauth and responds with the twitch 
//   username, corresponding summoner names, [app settings, etc.]
router.post('/auth', function(req, res, next) {
    console.log('authorizing...');
    console.log('node code: ', req.body.code);
    
    var response = { 'twitch_username': '', 'summoners':[], 'settings':{} };
   
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
        
        query = client.query('SELECT twitch_username, receives_title_updates, alias, code FROM users WHERE code=$1', [req.body.code]);
//        query = client.query('SELECT users.twitch_username, summoner, region, code FROM users INNER JOIN summoners ON (users.twitch_username = summoners.twitch_username) WHERE code=$1', [req.body.code]);
        query.on('error', function(err) {
            console.error('error with query (312)', err); 
        });
        query.on('row', function(row) {
//            response['summoners'].push({'summoner': row.summoner, 'region': row.region});
            response['twitch_username'] = row.twitch_username;
            response['settings'] = {
                title_updates: row.receives_title_updates,
                alias: row.alias    
            }
        });
        query.on('end', function(result) {
            // this if will be the result when a new user/log-in session is occurring
            if (result.rowCount === 0) {
                console.log('No such user found with this code.');
                // No such user found with this code. POST to Twitch for token and possibly make a new user
   
                var token;
                // this request goes to twitch kraken and gets the access token for the auth'd user
                request.post( { url:'https://api.twitch.tv/kraken/oauth2/token',
                                form: { client_id: '49mrp5ljn2nj44sx1czezi44ql151h2',
                                        client_secret: 'mz513m1xu5ga9mhrxuvb9sbwjgjw2ys',
                                        grant_type: 'authorization_code',
                                        redirect_uri: 'http://hoffmannbot.com/#/hoffmannbot/get/',
                                        code: req.body.code}},
                                function(err, httpResponse, body) {
                    if (err) {
                        console.error('error here (313)', err);
                    }
                    console.log('BODY: ', body);
                    token = JSON.parse(body).access_token;
                    console.log('token: ', token);
                    
                    // now GET the user info. In particular, we're looking for the twitch username 
                    request.get( { url:'https://api.twitch.tv/kraken/user',
                                   headers: {
                                       'Accept': 'application/vnd.twitchtv.v3+json',
                                       'Authorization': 'OAuth ' + token
                                   }
                                 },
                                function(err, httpResponse, body) {
                                    if (err) {
                                        console.error('error (314)');
                                    }
                                    twitch_username = JSON.parse(body).name;
                                    response.twitch_username = twitch_username;
                                    console.log('Username: ', twitch_username);
                                    query = client.query('INSERT INTO users (twitch_username, code, token) VALUES ($1, $2, $3) ON CONFLICT (twitch_username) DO UPDATE SET code = EXCLUDED.code, token = EXCLUDED.token',
                                                         [twitch_username, req.body.code, token]);
                                    query.on('error', function(err) {
                                       console.error('There was an error inserting/updating a (user,code,token)', err); 
                                    });
                                    query = client.query('SELECT twitch_username, receives_title_updates, alias FROM users WHERE twitch_username=$1', [twitch_username]);
                                    query.on('error', function(err) {
                                       console.error('error finding user settings'); 
                                    });
                                    query.on('row', function(row) {
                                        response['settings'] = {
                title_updates: row.receives_title_updates,
                alias: row.alias    
                                        }
                                    });
                                    query = client.query('SELECT users.twitch_username, summoner, region FROM users INNER JOIN summoners ON (users.twitch_username = summoners.twitch_username) WHERE users.twitch_username=$1', [twitch_username]);
                                    query.on('error', function(err) {
                                       console.error('error finding summoners for user', err); 
                                    });
                                    query.on('row', function(row) {
                                        response.summoners.push({'summoner': row.summoner, 'region': row.region});
                                    });
                                    query.on('end', function(result) {
                                        console.log(response);
                                        res.json(response);
                                    });
                                });
                });
                                   
            }
            // this is for a page refresh (same code appears again)
            else {
                query = client.query('SELECT users.twitch_username, summoner, region FROM users INNER JOIN summoners ON (users.twitch_username = summoners.twitch_username) WHERE users.twitch_username=$1', [twitch_username]);
                query.on('error', function(err) { 
                    console.error('Node, page refresh, database query error ', err);
                });
                query.on('row', function(row) {
                    response['summoners'].push({'summoner': row.summoner, 'region': row.region});
                });
                query.on('end', function() {
                    res.json(response);
                });
                
            }
        });
    });
    
});


// Don't believe this endpoint is needed
/*
router.post('/api/add/:user', function(req, res, next) {
    console.log('here 1');

    pool.connect(function(err, client, done) {
        if (err) {
            return console.error('error fetching client from pool' , err);
        }
        client.query('INSERT INTO users (twitch_username) VALUES (?)', [req.params.user], function(err, result) {
            done();
            if(err) {
                return console.error('error running query', err);
            }
            res.send(200);
            console.log('inserted twitch username ', req.params.user);
        });
    });
});
*/

router.post('/api/summoner/:action/:user/:summoner/:region', function(req, res, next) {
    console.log('here 2');

    pool.connect(function(err, client, done) {
        if (err) {
            return console.error('error fetching client from pool', err);
        }
        
        console.log('code: ', req.body.code);
        
        // The following query is for validating the code submitted with the username
        query = client.query('SELECT twitch_username, code FROM users WHERE code=$1 and twitch_username=$2', [req.body.code, req.params.user]);

        query.on('error', function(err) {
            console.error('Error while validating code.', err);
        });
        
        query.on('end', function(result) {
            if (result.rowCount === 0) {
                console.log('Incorrect code.');
                res.status(401).send('Incorrect code.');
            }
            else {
                query = client.query('SELECT users.twitch_username, summoner, region, code FROM users INNER JOIN summoners ON (users.twitch_username = summoners.twitch_username) WHERE code=$1 AND users.twitch_username=$2', 
                             [req.body.code, req.params.user]);
        
                query.on('error', function(err) {
                    console.log('error with query (312)', err); 
                });

                // Do not need a query.on('row') as the data is not important, only its existence
                /*
                query.on('row', function(row) {
                    if (req.params.action === 'remove' && 
                    row.summoner !== req.params.summoner) {
                        response['summoners'].push(row.summoner);
                    }
                    response['twitch_username'] = row.twitch_username;
                });
                */
        
       
                query.on('end', function(result) {
                    req.params.summoner = req.params.summoner.toLowerCase().replace(/\s+/g, '');
                    if ( req.params.action == 'add' ) {
                        if (result.rowCount === 7) {
                            console.log('Have reached maximum summoners for this user.');
                            res.status(409).send('Maximum number of summoners reached for this user.');
                        }
                        client.query('INSERT INTO summoners (twitch_username, summoner, region) VALUES ($1, $2, $3)', [req.params.user, req.params.summoner, req.params.region],
                          function(err, result) {
                              done();
                              if(err) {
                                  return console.error('error running query', err);
                              }
                        });
                        res.json({'user': req.params.user, 'addedSummoner': req.params.summoner, 'region': req.params.region});

                    }
                    else if ( req.params.action == 'remove' ) {
                        client.query('DELETE FROM summoners WHERE twitch_username=$1 AND summoner=$2 AND region=$3', [req.params.user, req.params.summoner, req.params.region], 
                          function(err, result) {
                              done();
                              if(err) {
                                  return console.error('error running query', err);
                              }
                          });
                        res.json({'user': req.params.user, 'removedSummoner':  req.params.summoner, 'region': req.params.region});

                    }
                });
            }
        
        });
    });
});
    
// endpoint for updating a user object
router.post('/api/user/update/:user', function(req, res, next) {
    
    pool.connect(function(err, client, done) {
        if (err) {
            return console.error('error fetching client from pool', err);
        }
        
        // The following query is for validating the code submitted with the username
        query = client.query('SELECT twitch_username, code FROM users WHERE code=$1 and twitch_username=$2', [req.body.code, req.params.user]);
        
        console.log('UPDATE, code: ', req.body.code, ' user: ', req.params.user);
        
        query.on('error', function(err) {
            console.error('Error while validating code.', err);
        });
        
        query.on('end', function(result) {
            if (result.rowCount === 0) {
                console.log('Incorrect code.');
                res.status(401).send('Incorrect code.');
            }
            else {
                query = client.query('UPDATE users SET receives_title_updates=$1, alias=$2 WHERE twitch_username=$3', [req.body.settings.receives_title_updates, req.body.settings.alias, req.params.user]);
                query.on('error', function(err) {
                    console.error('Node, User update query error ', err);    
                });
                query.on('end', function(result) {
                    res.status(200).send('User updated.');
                });
            }
        });
        done();
    });
    
});

// endpoint for retrieving currently LIVE streams that are using hoffmannbot 
router.get('/livestreams', function(req, res, next) {
    
    pool.connect(function(err, client, done) {
        if (err) {
            return console.error('error fetching client from pool', err);
        }
        
        console.log('livestreams endpoint entered');
        response = [];
        
        // maybe order this by viewership later on. Would need to store viewer stats in 'users' table 
        query = client.query('SELECT twitch_username FROM users WHERE channel_live=$1 LIMIT 10', ['true']);
        
        query.on('error', function(err) {
            console.error('Error while selecting live channels', err); 
        });
        
        query.on('row', function(row) {
            response.push({name: row.twitch_username});    
        });
        
        query.on('end', function() {
            console.log('livestreams endpoint query ended');
            res.json(response);    
        });
        
    });
    
});

module.exports = router;
