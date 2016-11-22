import json
import logging
import time
import requests
import psycopg2
import urllib.parse
import hexchat
import sys
import os

# When loading via Hexchat, the file path of the loaded script isn't included in the paths
#  that modules are loaded from. I include it explicitly in the following line(s).
sys.path.append(os.getcwd() + '\\..')

from static_data_shortened import RUNES, CHAMPIONS
import Riot_API_consts as Riot_Consts
import Twitch_API_consts as Twitch_Consts

__module_name__ = "hoffmannbot updater"
__module_version__ = "1.0"
__module_description__ = "Heroku Postgres database updater for hoffmannbot"

logging.basicConfig(filename=r'D:\hoffmannbot\logs\updater_log.txt',
                    datefmt='%m-%d %H:%M',
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    level=logging.DEBUG)

url = urllib.parse.urlparse(
    'postgres://suyfcwqppnenub:gajpaa6AMbZjd51zoT6swolqcx@ec2-23-23-225-81.compute-1.amazonaws.com:5432/d5731e9r3ilceu')
conn = psycopg2.connect(
    database=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port
)
c = conn.cursor()


class TwitchAPI(object):
    last_twitch_api_query = 0

    def __init__(self, client_id):
        self.client_id = client_id

    def _request(self, api_url, action, token='', params=None, data=None):
        """
        Launches request to Twitch API
        :param api_url: the api url of the appropriate endpoint (from Twitch_API_constants.py)
        :param params: html request params
        :return: response code if error, otherwise json response
        """
        if params is None:
            params = {}
        if data is None:
            data = {}

        diff = time.time() - TwitchAPI.last_twitch_api_query
        # TODO: put some exponential back-off when the API call fails

        args = {}
        for key, value in params.items():
            if key not in args:
                args[key] = value

        if action == 'get':
            headers = {
                'Accept': 'application/vnd.twitchtv.v3+json',
                'Authorization': 'OAuth {token}'.format(token=token) if token != '' else '',
                'Client-ID': '{client_id}'.format(client_id=self.client_id),
            }
            response = requests.get(
                Twitch_Consts.URL['base'].format(
                    url=api_url
                ),
                params=args,
                headers=headers
            )
            TwitchAPI.last_twitch_api_query = time.time()
            if response.status_code != 200:
                logging.debug('twitch API json response: ')
                logging.debug(response.url)
                # logging.debug(response.json())  # I believe this line is causing issue.
                return response.status_code

            logging.debug(response.url)
            return response.json()
        elif action == 'put':
            headers = {
                'Accept': 'application/vnd.twitchtv.v3+json',
                'Authorization': 'OAuth {token}'.format(token=token) if token != '' else '',
                'Client-ID': '{client_id}'.format(client_id=self.client_id),
                'content-type': 'application/json'
            }
            logging.debug('here is all the shit: ')
            logging.debug(Twitch_Consts.URL['base'].format(url=api_url))
            logging.debug(args)
            logging.debug(headers)
            logging.debug(data)
            response = requests.put(
                Twitch_Consts.URL['base'].format(
                    url=api_url
                ),
                params=args,
                headers=headers,
                data=json.dumps(data)
            )
            TwitchAPI.last_twitch_api_query = time.time()
            if response.status_code != 200:
                logging.debug('twitch API json response: ')
                logging.debug(response.json())
                return response.status_code

            logging.debug(response.url)
            return response.json()

    def update_title(self, token, user, title):
        api_url = Twitch_Consts.URL['channels'].format(
            user=user
        )
        data = {'channel': {'status': title[:139]}}
        return self._request(api_url, 'put', token=token, data=data)

    def get_live_streams(self, users):
        """The response will be a collection of stream objects corresponding to the subset of 'users' which are live
        :param users: dictionary of twitch users
        :return: the Twitch API JSON response
        """
        api_url = Twitch_Consts.URL['streams']
        return self._request(api_url, 'get', params=users)


class RiotAPI(object):
    last_riot_api_query = 0

    def __init__(self, api_key):
        # region=REGIONS['north_america'], platform=PLATFORMS['north_america']):
        self.api_key = api_key
        # self.region = region
        # self.platform = platform
        self.lastRequestTime = 0

    def _request(self, api_url, region, spectator=0, params=None):
        """
        Launches request to the Riot API
        :param api_url: API key
        :param region: the region where the request is being made, eg. NA, EUW, EUNE
        :param spectator: whether this is a request for current game info (spectator server)
        :param params: URL query strings
        :return: returns an integer on failure, json response on success
        """

        if params is None:
            params = {}

        diff = time.time() - RiotAPI.last_riot_api_query
        # 180,000 requests every 10 minutes and 3000 requests every 10 seconds (production key)
        # 500 requests every 10 minutes and 10 requests every 10 seconds (development key)
        if diff <= 0.005:
            return 1
        args = {'api_key': self.api_key}
        for key, value in params.items():
            if key not in args:
                args[key] = value
        if not spectator:
            response = requests.get(
                Riot_Consts.URL['base'].format(
                    proxy=Riot_Consts.REGIONS[region],  # proxy and region are the same at this time
                    region=Riot_Consts.REGIONS[region],
                    url=api_url
                ),
                params=args
            )
        else:
            response = requests.get(
                Riot_Consts.URL['spectator_base'].format(
                    proxy=Riot_Consts.REGIONS[region],  # proxy and region are the same at this time
                    platform=Riot_Consts.PLATFORMS[region],
                    url=api_url
                ),
                params=args
            )
        RiotAPI.last_riot_api_query = time.time()
        logging.debug('riot API status code: ')
        logging.debug(response.status_code)
        if response.status_code != 200:
            logging.debug('riot API headers: ')
            logging.debug(response.headers)
            return response.status_code

        logging.debug(response.url)
        return response.json()

    # get info about a summoner
    def get_summoner_by_name(self, name, region):
        api_url = Riot_Consts.URL['summoner_by_name'].format(
            version=Riot_Consts.API_VERSIONS['summoner'],
            names=name
        )
        return self._request(api_url, region)

    # get match history. hardcoded in to be only the last X=endIndex games.
    def get_matchlist(self, summonerid, region):
        api_url = Riot_Consts.URL['matchlist'].format(
            version=Riot_Consts.API_VERSIONS['matchlist'],
            id=summonerid
        )
        return self._request(api_url, region,
                             params={'rankedQueues': ['TEAM_BUILDER_DRAFT_RANKED_5x5', 'RANKED_FLEX_SR'],
                                     'beginIndex': '0', 'endIndex': '5'})

    # get current game info. uses special request due to the base Riot_Consts.URL being unique in Riot API
    def get_current_game(self, summoner_id, region):
        api_url = Riot_Consts.URL['currentgame'].format(
            id=summoner_id
        )
        return self._request(api_url, region, spectator=1)

    def get_match_info(self, matchId, region):
        api_url = Riot_Consts.URL['match'].format(
            version=Riot_Consts.API_VERSIONS['match'],
            matchId=matchId
        )
        return self._request(api_url, region)

    def get_league_data(self, summoner_id, region):
        api_url = Riot_Consts.URL['league'].format(
            version=Riot_Consts.API_VERSIONS['league'],
            id=summoner_id
        )
        return self._request(api_url, region)


# might want to hide this in a file. easy locally but need a heroku solution
#  the solution: put it in heroku ENV variables
def fetch_riot_key():
    """Returns the Riot API key"""

    # production key
    key = 'RGAPI-476c21b9-3346-4022-8036-2af99fea7c47'

    # development key
    # key = '50992d27-0c22-4d2d-b529-903be10b4e64'
    return key


def fetch_twitch_client_id():
    """Returns the Twitch client ID (like an API key)"""

    client_id = '49mrp5ljn2nj44sx1czezi44ql151h2'
    return client_id


def update_database_cb(userdata):
    """Function that updates Heroku postgres database with fresh data from the Riot API.
    """
    # print('recaching API data')
    logging.debug('Recaching API data')

    # TODO: RE performance: perhaps insert a line here that will return if the Riot API has been called too recently

    api = RiotAPI(fetch_riot_key())

    # base delay in seconds before querying Riot API again (before exponential back-off)
    summoner_info_query_base = 90000000  # TODO: how often to re-query this, if ever?
    match_list_query_base = 60
    current_game_query_base = 60
    league_query_base = 60

    siq_cap = 3600  # summoner info query exponential back-off cap
    ml_cap = 180  # match list query exponential back-off cap
    cg_cap = 60  # current game query exponential back-off cap
    league_cap = 600  # league info query exponential back-off cap

    c.execute('SELECT summoner, twitch_username, info_cache_time, match_list_cache_time, '
              'current_game_cache_time, region, league_cache_time FROM summoners')
    summoners = c.fetchall()

    for index in range(len(summoners)):
        c.execute('SELECT summonerId FROM summonerInfo' + '_' + summoners[index][5] + ' WHERE summoner=%s',
                  [summoners[index][0]])
        summoner_info = c.fetchone()
        c.execute('SELECT last_command_use FROM users WHERE twitch_username=%s', [summoners[index][1]])
        last_command_use = c.fetchone()[0]

        # summoner_info_query_wait = random.randint(0, min(siq_cap, summoner_info_query_base * 2 ** last_command_use))
        summoner_info_query_wait = summoner_info_query_base
        if summoner_info is None or (time.time() - summoners[index][2]) > summoner_info_query_wait:
            result = api.get_summoner_by_name(summoners[index][0], summoners[index][5])
            if not isinstance(result, int):
                temp_summoner_name = ''.join(summoners[index][0].split()).lower()
                temp_cache_time = time.time()
                # logging.debug('summoner info for ' + temp_summoner_name + ' cached')
                c.execute('INSERT INTO summonerInfo' + '_' + summoners[index][5] + ' (summoner, summonerId) '
                                                                                   'VALUES (%s, %s) '
                                                                                   'ON CONFLICT (summonerId) '
                                                                                   'DO UPDATE SET summoner=EXCLUDED.summoner, summonerId=EXCLUDED.summonerId',
                          [temp_summoner_name, result[temp_summoner_name]['id']])
                c.execute('UPDATE summoners SET info_cache_time=%s WHERE summoner=%s AND region=%s',
                          [temp_cache_time, temp_summoner_name, summoners[index][5]])
                conn.commit()
            else:
                continue

        # TODO: Is this database query necessary? could manually set summoner_info using the info obtained above
        c.execute('SELECT summonerId FROM summonerInfo' + '_' + summoners[index][5] +
                  ' WHERE summoner=%s',
                  [summoners[index][0]])
        summoner_info = c.fetchone()

        # match_list_query_wait = random.randint(0, min(ml_cap, match_list_query_base * 2 ** last_command_use))
        match_list_query_wait = match_list_query_base
        if summoners[index][3] == 0 or (time.time() - summoners[index][3] > match_list_query_wait):
            result = api.get_matchlist(summoner_info[0], summoners[index][5])
            if not isinstance(result, int):
                c.execute('UPDATE summoners SET match_list_cache_time=%s WHERE summoner=%s AND region=%s',
                          [time.time(), summoners[index][0], summoners[index][5]])
                if result['totalGames'] != 0:
                    for match in result['matches']:
                        # c.execute('INSERT OR REPLACE INTO matchList (matchId, timestamp, summonerId, lane) '
                        #           'VALUES (%s,%s,%s,%s)',
                        #           [match['matchId'], match['timestamp'], summoner_info[0], match['lane']])
                        c.execute('INSERT INTO matchList' + '_' + summoners[index][5] +
                                  ' (matchId, timestamp, summonerId, lane) '
                                  'VALUES (%s, %s, %s, %s) '
                                  'ON CONFLICT DO NOTHING',  # is it correct to do nothing here? I think so.
                                  [match['matchId'], match['timestamp'], summoner_info[0], match['lane']])
                conn.commit()
                # logging.debug('match list cached for ' + summoners[index][0])
            else:
                continue

        # current_game_query_wait = random.randint(0, min(cg_cap, current_game_query_base * 2 ** last_command_use))
        current_game_query_wait = current_game_query_base
        if summoners[index][4] == 0 or (time.time() - summoners[index][4] > current_game_query_wait):
            result = api.get_current_game(summoner_info[0], summoners[index][5])
            if result == 404:
                # logging.debug('current game for ' + summoners[index][0] + ' not found')
                c.execute('UPDATE summoners SET current_game_exists=%s, current_game_cache_time=%s '
                          'WHERE summoner=%s AND region=%s',
                          ['false', time.time(), summoners[index][0], summoners[index][5]])
                c.execute('DELETE from currentRunes' + '_' + summoners[index][5] +
                          ' WHERE summoner=%s', [summoners[index][0]])
                c.execute('DELETE from currentBans' + '_' + summoners[index][5] +
                          ' WHERE summoner=%s', [summoners[index][0]])
                conn.commit()
                # TODO: update title if necessary
            elif not isinstance(result, int):
                # logging.debug('current game info for ' + summoners[index][0] + ' cached')
                active_game_length = result['gameLength']
                for participants in result['participants']:
                    if ''.join(participants['summonerName'].split()).lower() == summoners[index][0]:
                        active_game_champId = participants['championId']
                        active_game_runes = participants['runes']
                c.execute('UPDATE summoners SET current_game_exists=%s, current_game_cache_time=%s, gameLength=%s,'
                          ' championId=%s, gameId=%s WHERE summoner=%s AND region=%s',
                          ['true', time.time(), active_game_length, active_game_champId, result['gameId'],
                           summoners[index][0], summoners[index][5]])
                for rune in active_game_runes:
                    # c.execute('INSERT OR REPLACE INTO currentRunes (count, runeId, summoner, gameId) '
                    #           'VALUES (%s,%s,%s,%s)',
                    #           [rune['count'], rune['runeId'], summoners[index][0], result['gameId']])
                    c.execute('INSERT INTO currentRunes' + '_' + summoners[index][5] +
                              ' (count, runeId, summoner, gameId) '
                              'VALUES (%s,%s,%s,%s) '
                              'ON CONFLICT DO NOTHING',
                              [rune['count'], rune['runeId'], summoners[index][0], result['gameId']])
                for ban in result['bannedChampions']:
                    # c.execute('INSERT OR REPLACE INTO currentBans (championId, summoner, gameId) VALUES (%s,%s,%s)',
                    #           [ban['championId'], summoners[index][0], result['gameId']])
                    c.execute('INSERT INTO currentBans' + '_' + summoners[index][5] +
                              ' (championId, summoner, gameId) '
                              'VALUES (%s,%s,%s) '
                              'ON CONFLICT DO NOTHING',
                              [ban['championId'], summoners[index][0], result['gameId']])
                conn.commit()

        # TODO: is it necessary to execute this every time? maybe have a global list of unstored matches?
        c.execute('SELECT matchId, timestamp FROM matchList' + '_' + summoners[index][5] +
                  ' WHERE matchId NOT IN (SELECT matchId FROM match' + '_' + summoners[index][5] + ') '
                                                                                                   'ORDER BY timestamp DESC')
        unstored_matches = c.fetchall()  # list of 1-tuples
        if len(unstored_matches) != 0:
            result = api.get_match_info((unstored_matches.pop(0))[0], summoners[index][5])
            if not isinstance(result, int):
                logging.debug('Updating matches from match list')
                logging.debug(result['matchId'])
                logging.debug(result['matchCreation'])
                logging.debug(result['matchDuration'])
                c.execute('INSERT INTO match' + '_' + summoners[index][5] + ' (matchId,matchCreation,matchDuration) '
                                                                            'VALUES (%s,%s,%s)',
                          [result['matchId'], result['matchCreation'], result['matchDuration']])
                for participantIdentity in result['participantIdentities']:
                    c.execute('INSERT INTO participantIdentities' + '_' + summoners[index][5] +
                              ' (matchId,participantId,summonerId) '
                              'VALUES (%s,%s,%s)',
                              [result['matchId'],
                               participantIdentity['participantId'],
                               participantIdentity['player']['summonerId']])

                # The following 'for' loop is used when each rune type gets its own row in a separate rune table. To be
                #  row-economical, we may store runes as a JSON row in the participants table.

                # for participant in result['participants']:
                #     c.execute('INSERT INTO participants '
                #               '(matchId,championId,participantId,kills,deaths,assists,winner) '
                #               'VALUES (%s,%s,%s,%s,%s,%s,%s)',
                #               [result['matchId'], participant['championId'], participant['participantId'],
                #                participant['stats']['kills'], participant['stats']['deaths'],
                #                participant['stats']['assists'], int(participant['stats']['winner'])])
                #     for rune in participant['runes']:
                #         c.execute('INSERT INTO runes (participantId,matchId,rank,runeId) VALUES (%s,%s,%s,%s)',
                #                   [participant['participantId'],
                #                    result['matchId'],
                #                    rune['rank'],
                #                    rune['runeId']
                #                    ])

                # The following 'for' loop is the alternative to the above. This will store runes as a JSON row in
                #  the participant table. Again, this is to be conservative with the amount of rows we create (rather
                #  than only being concerned with disk space). This is due to Heroku PostgreSQL row-restriction on
                #  hobby plans.
                for participant in result['participants']:
                    c.execute('INSERT INTO participants' + '_' + summoners[index][5] +
                              ' (matchId,championId,participantId,kills,deaths,assists,winner,runes) '
                              'VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                              [result['matchId'], participant['championId'], participant['participantId'],
                               participant['stats']['kills'], participant['stats']['deaths'],
                               participant['stats']['assists'], int(participant['stats']['winner']),
                               json.dumps(participant['runes'])])

                conn.commit()
                logging.debug('cached a match. match id: ' + str(result['matchId']))

        # league_query_wait = random.randint(0, min(league_cap, league_query_base * 2 ** last_command_use))
        league_query_wait = league_query_base
        if summoners[index][6] == 0 or ((time.time() - summoners[index][6]) > league_query_wait):
            result = api.get_league_data(summoner_info[0], summoners[index][5])
            if not isinstance(result, int):
                in_series = None
                for mode in result[str(summoner_info[0])]:
                    if mode['queue'] == 'RANKED_SOLO_5x5':
                        league = mode['tier']
                        division = mode['entries'][0]['division']
                        league_points = mode['entries'][0]['leaguePoints']
                        if "miniSeries" in mode['entries'][0]:
                            in_series = True
                            series_wins = mode['entries'][0]['miniSeries']['wins']
                            series_losses = mode['entries'][0]['miniSeries']['losses']
                        else:
                            in_series = False
                        break
                if in_series is None:
                    pass
                elif not in_series:
                    c.execute('UPDATE summoners SET league_cache_time=%s, league=%s, division=%s, league_points=%s, '
                              'in_series=%s '
                              'WHERE summoner=%s AND region=%s',
                              [time.time(), league, division, league_points, 'false', summoners[index][0],
                               summoners[index][5]])

                elif in_series:
                    c.execute('UPDATE summoners SET league_cache_time=%s, league=%s, division=%s, league_points=%s, '
                              'in_series=%s, series_wins=%s, series_losses=%s '
                              'WHERE summoner=%s AND region=%s',
                              [time.time(), league, division, league_points, 'true', series_wins, series_losses,
                               summoners[index][0], summoners[index][5]])
                conn.commit()
                # logging.debug('league data for ' + summoners[index][0] + ' cached')
            else:
                continue
    return hexchat.EAT_ALL


def refresh_live_streams(userdata):
    """Updates the channel_live column in the database"""

    # print('refreshing live streams')
    logging.debug('Checking if streams are live. ')
    c.execute("SELECT twitch_username, status_cache_time FROM users "
              "WHERE %s - status_cache_time > 300 "
              "ORDER BY status_cache_time "
              "LIMIT 100", [time.time()])
    rows = c.fetchall()
    if not rows:
        logging.debug('No users need channel status update.')
        return hexchat.EAT_ALL
    logging.debug('')
    users = ''
    logging.debug('users: ')
    for row in rows:
        logging.debug(row[0] + ', ')
        users += row[0] + ','
    logging.debug('')

    channels = {'channel': users[:-1]}

    api = TwitchAPI(fetch_twitch_client_id())
    result = api.get_live_streams(channels)
    if not isinstance(result, int):
        live_streams = []
        logging.debug('live channels: ')
        for stream in result['streams']:
            logging.debug(stream['channel']['name'] + ', ')
            live_streams.append(stream['channel']['name'])
        logging.debug('')
        for row in rows:
            if row[0] in live_streams:
                logging.debug('Following user set to LIVE: ' + str(row[0]))
                c.execute('UPDATE users SET channel_live=%s, status_cache_time=%s '
                          'WHERE twitch_username=%s', ['true', time.time(), row[0]])
                conn.commit()
            else:
                logging.debug('Following user set to NOT LIVE: ' + str(row[0]))
                c.execute('UPDATE users SET channel_live=%s, status_cache_time=%s '
                          'WHERE twitch_username=%s', ['false', time.time(), row[0]])
                conn.commit()
    else:
        logging.debug('twitch api call failed, result: ')
        logging.debug(result)
    return hexchat.EAT_ALL


def update_twitch_title(userdata):
    """This updates the title of a currently streaming twitch user who last had their title updated more than 60
     seconds ago. If a twitch_username is specified, it updates that specific users title
    """
    # print('updating titles')
    logging.debug('updating titles')
    c.execute("SELECT twitch_username, token, title_base FROM users "
              "WHERE receives_title_updates='true' AND channel_live='true' AND %s - last_title_update > 60 "
              "ORDER BY last_title_update DESC "
              "LIMIT 1", [time.time()])
    row = c.fetchone()
    if row is None:
        return hexchat.EAT_ALL
    user = row[0]
    token = row[1]
    title_base = row[2]

    c.execute("SELECT summoner,gameId,gameLength,championId,region,league,league_points FROM summoners "
              "WHERE twitch_username=%s AND current_game_exists='true'", [user])
    current_game = c.fetchone()
    if current_game is None:
        title_dynamic = ''
    else:
        summoner = current_game[0]
        game_length = current_game[2]
        champ_id = current_game[3]
        region = current_game[4]

        # maybe add this into the updated title information at some point
        league = current_game[5]
        league_points = current_game[6]

        minutes = (game_length // 60) + 3  # game length in minutes (+3 minutes due to spectator delay)
        champ = CHAMPIONS.get(champ_id, str(champ_id))

        if game_length == 0:
            title_dynamic = '[Going into game as {champ}]'.format(champ=champ)
        else:
            title_dynamic = '[In game as {champ} for {length}m]'.format(champ=champ, length=minutes)

    title = (title_dynamic + ' ' + title_base) if title_dynamic != '' else title_base
    data = {'channel': {'status': title[:139]}}
    logging.debug('Setting channel to:')
    logging.debug(data)

    api = TwitchAPI(fetch_twitch_client_id())
    result = api.update_title(token, user, title)
    if not isinstance(result, int):
        logging.debug('twitch API result: ')
        logging.debug(result)
        c.execute('UPDATE users SET last_title_update=%s WHERE twitch_username=%s', [time.time(), user])
        return hexchat.EAT_ALL
    else:
        logging.debug('say Twitch API call failed :(.')
        logging.debug('status code: ' + str(result))
        return hexchat.EAT_ALL

        # TODO: again we may want to put this into a function/class especially if we start using other endpoints
        #     url = 'https://api.twitch.tv/kraken/channels/{user}'.format(user=user)
        # headers = {'Accept': 'application/vnd.twitchtv.v3+json',
        #            'Authorization': 'OAuth {token}'.format(token=token),
        #            'Client-ID': '49mrp5ljn2nj44sx1czezi44ql151h2',
        #            'content-type': 'application/json'
        #            }
        # response = requests.put(url, data=json.dumps(data), headers=headers)
        # if response.status_code != 200:
        #     logging.debug('say Twitch API call failed :(.')
        #     return hexchat.EAT_ALL
        # logging.debug('twitch API status code: ')
        # logging.debug(response.status_code)
        # c.execute('UPDATE users SET last_title_update=%s WHERE twitch_username=%s', [time.time(), user])
        # return hexchat.EAT_ALL


def unload_cb(userdata):
    conn.commit()
    c.close()
    conn.close()
    print('==========Hoffmannbot Updater unloaded==========')

print('==========Hoffmannbot Updater loaded==========')

hook_1 = hexchat.hook_timer(5 * 1000, refresh_live_streams)  # update which streams are currently live
hook_2 = hexchat.hook_timer(5 * 1000, update_twitch_title)  # update twitch titles
hook_3 = hexchat.hook_timer(5 * 1000, update_database_cb)  # update the database with new Riot API info

hexchat.hook_unload(unload_cb)
