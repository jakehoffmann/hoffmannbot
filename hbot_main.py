import hexchat
import requests
import time
import calendar
import json
import psycopg2
import urllib.parse
import logging
import random
import sys
import os

# When loading via Hexchat, the file path of the loaded script isn't included in the paths
#  that modules are loaded from. I include it explicitly in the following line(s).
# sys.path.append(r'D:\hoffmannbot')
sys.path.append(os.getcwd() + '\\..')

from static_data_shortened import RUNES, CHAMPIONS
import Riot_API_consts as Riot_Consts
import Twitch_API_consts as Twitch_Consts

# from Riot_API_consts import URL, API_VERSIONS, REGIONS, PLATFORMS

logging.basicConfig(filename='D:\hoffmannbot\logs\log.txt', level=logging.DEBUG)
# logging.basicConfig(level=logging.DEBUG)

logging.debug('Directory added to sys.path: ' + os.getcwd() + '\\..')

__module_name__ = "hoffmannbot"
__module_version__ = "1.0"
__module_description__ = "Twitch Chat Bot with Jake's custom commands"

# connecting to postgres database
urllib.parse.uses_netloc.append("postgres")

# url = urllib.parse.urlparse(os.environ["DATABASE_URL"])
url = urllib.parse.urlparse(
    'postgres://apujurenpledps:I8ReS0Zp3289k4V-HTeEDkSLf_@ec2-54-243-217-22.compute-1.amazonaws.com:5432/d4kg1tud3ujhui')

# TODO: Remove the above line for production, OBVIOUSLY

conn = psycopg2.connect(
    database=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port
)
c = conn.cursor()

# variables to make sure I don't spam Twitch chat
last_request_time = 0
currentgame_timeout = 0
lastgame_timeout = 0

# TODO: remove this once I clean up its instances
SUMMONERS = {}


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
                logging.debug(response.json())
                return response.status_code

            logging.debug(response.url)
            print(response.url)
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
            print(response.url)
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

        global last_request_time
        logging.debug('class timer variable: ' + str(RiotAPI.last_riot_api_query))
        logging.debug('global timer variable: ' + str(last_request_time))
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
        last_request_time = RiotAPI.last_riot_api_query = time.time()
        logging.debug('riot API status code: ')
        logging.debug(response.status_code)
        if response.status_code != 200:
            logging.debug('riot API headers: ')
            logging.debug(response.headers)
            return response.status_code

        logging.debug(response.url)
        print(response.url)
        return response.json()

    # get info about a summoner
    def get_summoner_by_name(self, name, region):
        api_url = Riot_Consts.URL['summoner_by_name'].format(
            version=Riot_Consts.API_VERSIONS['summoner'],
            names=name
        )
        return self._request(api_url, region)

    # get match history. hardcoded in to be only last 10 games. Edit the endIndex to change this
    def get_matchlist(self, summonerid, region):
        api_url = Riot_Consts.URL['matchlist'].format(
            version=Riot_Consts.API_VERSIONS['matchlist'],
            id=summonerid
        )
        return self._request(api_url, region, params={'rankedQueues': 'TEAM_BUILDER_DRAFT_RANKED_5x5',
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


def refresh_channels():
    """checks for IRC channels to /join and /part

    Retrieves the list of twitch users that are using the bot and /join's new ones and /part's ones that have decided
     not to use the bot anymore.
    """

    c.execute('SELECT twitch_username FROM users')
    updated_channels = c.fetchall()
    current_channels = hexchat.get_list("channels")

    for channel in current_channels[:]:
        print('looking at ' + channel.channel)
        print(type(channel.channel))
        if channel.channel == 'Twitch':
            current_channels.remove(channel)
        elif channel.channel == '':
            current_channels.remove(channel)
        elif (channel.channel[1:],) in updated_channels:
            print('remove from channels to join and channels to part lists: ' + channel.channel)
            current_channels.remove(channel)
            updated_channels.remove((channel.channel[1:],))

    for channel in current_channels:
        print('Executed command: part ' + channel.channel)
        hexchat.command('part ' + channel.channel)

    for channel in updated_channels:
        print('Executed command: join #' + channel[0])
        hexchat.command('join #' + channel[0])


# not in use anymore
# this gets called automatically every X minutes (via hook_timer at bottom of script)
# updates the database with information from Riot API
def update_cb(userdata):
    logging.debug('Recaching API data')
    #
    # global r
    # global matchList
    # global matchInfo
    # global current_game_info
    #
    # api = RiotAPI('50992d27-0c22-4d2d-b529-903be10b4e64')
    # for index in range(len(SUMMONERS)):
    #     if not r[index] or (time.time() - r[index].get('cacheTime', 0)) > 300:
    #         result = api.get_summoner_by_name(SUMMONERS[index])
    #         if not isinstance(result, int):
    #             logging.debug('summoner info for '+SUMMONERS[index]+' cached')
    #             r[index] = result
    #             r[index]['cacheTime'] = time.time()
    #         else:
    #             continue
    #     if not matchList[index] or (time.time() - matchList[index].get('cacheTime', 0)) > 300:
    #         summ_id = r[index][SUMMONERS[index]]['id']
    #         result = api.get_matchlist(summ_id)
    #         if not isinstance(result, int):
    #             logging.debug('summoner matchlist for ' + SUMMONERS[index] + ' cached')
    #             matchList[index] = result
    #             matchList[index]['cacheTime'] = time.time()
    #         else:
    #             continue
    #     if not matchInfo[index] or (time.time() - matchInfo[index].get('cacheTime', 0)) > 300:
    #         matchId = matchList[index]['matches'][0]['matchId']
    #         result = api.get_match_info(matchId)
    #         if not isinstance(result, int):
    #             logging.debug('summoner matchinfo for ' + SUMMONERS[index] + ' cached')
    #             matchInfo[index] = result
    #             matchInfo[index]['cacheTime'] = time.time()
    #     if not current_game_info[index] or (time.time() - current_game_info[index].get('cacheTime', 0)) > 60:
    #         summ_id = r[index][SUMMONERS[index]]['id']
    #         result = api.get_current_game(summ_id)
    #         if result == 404:
    #             logging.debug('current game for ' + SUMMONERS[index] + ' not found!')
    #             current_game_info[index] = {}
    #             current_game_info[index]['cacheTime'] = time.time()
    #             if index == len(SUMMONERS)-1:
    #                 update_title()
    #         elif not isinstance(result, int):
    #             logging.debug('current game info for ' + SUMMONERS[index] + ' cached')
    #             current_game_info[index] = result
    #             current_game_info[index]['cacheTime'] = time.time()
    #             update_title(index)
    #
    # return 1


# new version of update_cb that uses database instead of memory
def update_database_cb(userdata):
    """Function that updates Heroku postgres database.
    """
    print('Recaching API data')

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
                print('summoner info for ' + temp_summoner_name + ' cached')
                # c.execute('INSERT OR REPLACE INTO summonerInfo (summoner, summonerId)'
                #           'VALUES (%s,%s)', [temp_summoner_name, result[temp_summoner_name]['id']])
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
                print('match list cached for ' + summoners[index][0])
            else:
                continue

        # current_game_query_wait = random.randint(0, min(cg_cap, current_game_query_base * 2 ** last_command_use))
        current_game_query_wait = current_game_query_base
        if summoners[index][4] == 0 or (time.time() - summoners[index][4] > current_game_query_wait):
            result = api.get_current_game(summoner_info[0], summoners[index][5])
            if result == 404:
                print('current game for ' + summoners[index][0] + ' not found')
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
                print('current game info for ' + summoners[index][0] + ' cached')
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
                print('Updating matches from match list')
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
                print('league data for ' + summoners[index][0] + ' cached')
            else:
                continue
    return hexchat.EAT_ALL


# TODO: finish this sucker (perhaps turn it into a TwitchAPI class)
# def twitch_request(data={}):
#     url = 'https://api.twitch.tv/kraken/channels/jakehoffmann'
#     headers = {'Accept': 'application/vnd.twitchtv.v3+json',
#                'Authorization': 'OAuth 6rlublf96ewjbb4psc2gg0hxkp8hy0',
#                'Client-ID': '49mrp5ljn2nj44sx1czezi44ql151h2',
#                'content-type': 'application/json'
#                }
#     response = requests.put(url, data=json.dumps(data), headers=headers)
#     if response.status_code != 200:
#         print('Twitch API call failed :( status code: '+str(response.status_code))


# ---- OLD VERSION ---- #
# ----             ---- #
# calls twitch API to update the title of the stream
def update_title(active_summoner=-1):
    global current_game_info
    global title_dynamic
    global title_base
    # if there is an active summoner in SUMMONERS, update title with current game info
    if active_summoner != -1:
        active_game_length = current_game_info[active_summoner]['gameLength']
        for participants in current_game_info[active_summoner]['participants']:
            if participants['summonerName'].lower() == SUMMONERS[active_summoner].lower():
                active_game_champId = participants['championId']
        static_data_response = requests.get(
            'https://global.api.pvp.net/api/lol/static-data/na/v1.2/champion/{champId}\
            ?api_key=50992d27-0c22-4d2d-b529-903be10b4e64'.format(
                champId=active_game_champId
            )
        )
        active_game_champ = static_data_response.json()['name']
        logging.debug(active_game_champ)
        logging.debug('active game length: ' + str(active_game_length))
        # note that the game length is minutes+3 due to spectator delay
        minutes = (active_game_length // 60) + 3
        if active_game_length == 0:
            title_dynamic = '[Going into game as {champ}]'.format(champ=active_game_champ)
        else:
            title_dynamic = '[In game as {champ} for {length}m]'.format(champ=active_game_champ, length=minutes)
        # otherwise if no active games, set the dynamic title to empty string
    elif all(len(current_game_info[index]) == 1 for index in range(len(SUMMONERS))):
        logging.debug('No games found.')
        title_dynamic = ''
    else:
        'Neither title update condition met'
        return 0
    # TODO: wrap twitch API stuff up into a function call
    url = 'https://api.twitch.tv/kraken/channels/jakehoffmann'
    data = {'channel': {'status': title_dynamic + ' ' + title_base if title_dynamic != '' else title_base}}
    logging.debug('Setting title to:')
    logging.debug(data)
    headers = {'Accept': 'application/vnd.twitchtv.v3+json',
               'Authorization': 'OAuth 6rlublf96ewjbb4psc2gg0hxkp8hy0',
               'Client-ID': '49mrp5ljn2nj44sx1czezi44ql151h2',
               'content-type': 'application/json'
               }
    response = requests.put(url, data=json.dumps(data), headers=headers)
    if response.status_code != 200:
        hexchat.command('say Twitch API call failed :(.')
    logging.debug('twitch API status code: ')
    logging.debug(response.status_code)


def refresh_live_streams(userdata):
    """Updates the channel_live column in the database"""

    print('Checking if streams are live. ', end="")
    c.execute("SELECT twitch_username, status_cache_time FROM users "
              "WHERE %s - status_cache_time > 1800 "
              "ORDER BY status_cache_time "
              "LIMIT 100", [time.time()])
    rows = c.fetchall()
    if not rows:
        print('No users need channel status update.')
        return hexchat.EAT_ALL
    print('')
    users = ''
    print('users: ', end="")
    for row in rows:
        print(row[0] + ', ', end="")
        users += row[0] + ','
    print('')

    channels = {'channel': users[:-1]}

    api = TwitchAPI(fetch_twitch_client_id())
    result = api.get_live_streams(channels)
    live_streams = []
    print('live channels: ', end="")
    for stream in result['streams']:
        print(stream['channel']['name'] + ', ', end="")
        live_streams.append(stream['channel']['name'])
    print('')
    for row in rows:
        if row[0] in live_streams:
            print('Following user set to LIVE: ' + str(row[0]))
            c.execute('UPDATE users SET channel_live=%s, status_cache_time=%s '
                      'WHERE twitch_username=%s', ['true', time.time(), row[0]])
            conn.commit()
        else:
            print('Following user set to NOT LIVE: ' + str(row[0]))
            c.execute('UPDATE users SET channel_live=%s, status_cache_time=%s '
                      'WHERE twitch_username=%s', ['false', time.time(), row[0]])
            conn.commit()
    return hexchat.EAT_ALL



def update_twitch_title(userdata):
    """This updates the title of a currently streaming twitch user who last had their title updated more than 60
     seconds ago. If a twitch_username is specified, it updates that specific users title
    """
    print('updating titles')
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
    print('Setting channel to:')
    print(data)

    api = TwitchAPI(fetch_twitch_client_id())
    result = api.update_title(token, user, title)
    if not isinstance(result, int):
        print('twitch API result: ')
        print(result)
        c.execute('UPDATE users SET last_title_update=%s WHERE twitch_username=%s', [time.time(), user])
        return hexchat.EAT_ALL
    else:
        print('say Twitch API call failed :(.')
        print('status code: ' + str(result))
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
        #     print('say Twitch API call failed :(.')
        #     return hexchat.EAT_ALL
        # print('twitch API status code: ')
        # print(response.status_code)
        # c.execute('UPDATE users SET last_title_update=%s WHERE twitch_username=%s', [time.time(), user])
        # return hexchat.EAT_ALL


def channel_message_cb(word, word_eol, userdata):
    """Is called whenever a message is received in HexChat. After a message is detected, we check if it is a valid
    command. If it is, we handle it appropriately. See HexChat Python documentation for information about this
    functions arguments and what it returns.
    """
    # TODO: FIRST THING TO DO in this function is check if it's a valid command. Otherwise we can drop it and move on!

    command = word[1].split()[0]  # the first word of a Twitch chat message, possibly a command
    user = word[0]
    channel = hexchat.get_info('channel')[1:]  # the channel in which the command was used
    c.execute('SELECT alias,lcu_last,lcu_current,lcu_hi,lcu_rank FROM users WHERE twitch_username=%s', [channel])
    is_valid_user = c.fetchone()
    if is_valid_user is None:
        hexchat.command('say I\'m not supposed to be in this channel, goodbye!')
        hexchat.command('part ' + '#' + channel)
        return hexchat.EAT_ALL
    alias = is_valid_user[0] if is_valid_user[0] != 'noalias' else channel
    lcu_last = is_valid_user[1]  # last command usage for command '!last'
    lcu_current = is_valid_user[2]
    lcu_hi = is_valid_user[3]
    lcu_rank = is_valid_user[4]

    if command == '!lastgame' or command == '!last':
        command_use_time = time.time()
        if (command_use_time - lcu_last) <= 5:
            return hexchat.EAT_ALL
        c.execute('UPDATE users SET lcu_last=%s,last_command_use=%s '
                  'WHERE twitch_username=%s', [command_use_time, command_use_time, channel])
        logging.debug('lastgame')

        # The next lines put the command in jake-only mode
        # username = word[0]
        # if username != 'jakehoffmann':
        #     hexchat.command('say ' + command[1:] + ' is Jake-only for testing at the moment :)')
        #     return hexchat.EAT_ALL

        # c.execute('SELECT kills,deaths,assists,matchCreation,matchDuration,participants.championId,winner,lane,'
        #           'summoners.summoner, participants.matchId '
        #           'FROM summoners '
        #           'INNER JOIN summonerInfo ON summoners.summoner = summonerInfo.summoner '
        #           'INNER JOIN participantIdentities '
        #           'ON participantIdentities.summonerId = summonerInfo.summonerId '
        #           'INNER JOIN participants ON participantIdentities.participantId = participants.participantId '
        #           'AND participantIdentities.matchId = participants.matchId '
        #           'INNER JOIN match ON participants.matchId = match.matchId '
        #           'INNER JOIN matchList ON participants.matchId = matchList.matchId '
        #           'WHERE summoners.twitch_username = %s '
        #           'ORDER BY matchCreation DESC '
        #           'LIMIT 1', [channel])
        #############################

        # This query selects all the summoners related to the current twitch user, orders them by when they last
        #  played a match, and then selects the most recent one.
        c.execute('SELECT kills, deaths, assists, matchCreation, matchDuration, championId, winner, lane, '
                  'summoner, matchId, region '
                  'FROM '
                  '('
                  'SELECT kills,deaths,assists,matchCreation,matchDuration,participants_BR.championId,winner,lane,'
                  'summoners.summoner, participants_BR.matchId, region '
                  'FROM summoners '
                  'INNER JOIN summonerInfo_BR ON summoners.summoner = summonerInfo_BR.summoner '
                  'INNER JOIN participantIdentities_BR '
                  'ON participantIdentities_BR.summonerId = summonerInfo_BR.summonerId '
                  'INNER JOIN participants_BR '
                  'ON participantIdentities_BR.participantId = participants_BR.participantId '
                  'AND participantIdentities_BR.matchId = participants_BR.matchId '
                  'INNER JOIN match_BR ON participants_BR.matchId = match_BR.matchId '
                  'INNER JOIN matchList_BR ON participants_BR.matchId = matchList_BR.matchId '
                  'WHERE summoners.twitch_username = %s '
                  'UNION '
                  'SELECT kills,deaths,assists,matchCreation,matchDuration,participants_EUNE.championId,winner,lane,'
                  'summoners.summoner, participants_EUNE.matchId, region '
                  'FROM summoners '
                  'INNER JOIN summonerInfo_EUNE ON summoners.summoner = summonerInfo_EUNE.summoner '
                  'INNER JOIN participantIdentities_EUNE '
                  'ON participantIdentities_EUNE.summonerId = summonerInfo_EUNE.summonerId '
                  'INNER JOIN participants_EUNE '
                  'ON participantIdentities_EUNE.participantId = participants_EUNE.participantId '
                  'AND participantIdentities_EUNE.matchId = participants_EUNE.matchId '
                  'INNER JOIN match_EUNE ON participants_EUNE.matchId = match_EUNE.matchId '
                  'INNER JOIN matchList_EUNE ON participants_EUNE.matchId = matchList_EUNE.matchId '
                  'WHERE summoners.twitch_username = %s '
                  'UNION '
                  'SELECT kills,deaths,assists,matchCreation,matchDuration,participants_EUW.championId,winner,lane,'
                  'summoners.summoner, participants_EUW.matchId, region '
                  'FROM summoners '
                  'INNER JOIN summonerInfo_EUW ON summoners.summoner = summonerInfo_EUW.summoner '
                  'INNER JOIN participantIdentities_EUW '
                  'ON participantIdentities_EUW.summonerId = summonerInfo_EUW.summonerId '
                  'INNER JOIN participants_EUW '
                  'ON participantIdentities_EUW.participantId = participants_EUW.participantId '
                  'AND participantIdentities_EUW.matchId = participants_EUW.matchId '
                  'INNER JOIN match_EUW ON participants_EUW.matchId = match_EUW.matchId '
                  'INNER JOIN matchList_EUW ON participants_EUW.matchId = matchList_EUW.matchId '
                  'WHERE summoners.twitch_username = %s '
                  'UNION '
                  'SELECT kills,deaths,assists,matchCreation,matchDuration,participants_JP.championId,winner,lane,'
                  'summoners.summoner, participants_JP.matchId, region '
                  'FROM summoners '
                  'INNER JOIN summonerInfo_JP ON summoners.summoner = summonerInfo_JP.summoner '
                  'INNER JOIN participantIdentities_JP '
                  'ON participantIdentities_JP.summonerId = summonerInfo_JP.summonerId '
                  'INNER JOIN participants_JP '
                  'ON participantIdentities_JP.participantId = participants_JP.participantId '
                  'AND participantIdentities_JP.matchId = participants_JP.matchId '
                  'INNER JOIN match_JP ON participants_JP.matchId = match_JP.matchId '
                  'INNER JOIN matchList_JP ON participants_JP.matchId = matchList_JP.matchId '
                  'WHERE summoners.twitch_username = %s '
                  'UNION '
                  'SELECT kills,deaths,assists,matchCreation,matchDuration,participants_KR.championId,winner,lane,'
                  'summoners.summoner, participants_KR.matchId, region '
                  'FROM summoners '
                  'INNER JOIN summonerInfo_KR ON summoners.summoner = summonerInfo_KR.summoner '
                  'INNER JOIN participantIdentities_KR '
                  'ON participantIdentities_KR.summonerId = summonerInfo_KR.summonerId '
                  'INNER JOIN participants_KR '
                  'ON participantIdentities_KR.participantId = participants_KR.participantId '
                  'AND participantIdentities_KR.matchId = participants_KR.matchId '
                  'INNER JOIN match_KR ON participants_KR.matchId = match_KR.matchId '
                  'INNER JOIN matchList_KR ON participants_KR.matchId = matchList_KR.matchId '
                  'WHERE summoners.twitch_username = %s '
                  'UNION '
                  'SELECT kills,deaths,assists,matchCreation,matchDuration,participants_LAN.championId,winner,lane,'
                  'summoners.summoner, participants_LAN.matchId, region '
                  'FROM summoners '
                  'INNER JOIN summonerInfo_LAN ON summoners.summoner = summonerInfo_LAN.summoner '
                  'INNER JOIN participantIdentities_LAN '
                  'ON participantIdentities_LAN.summonerId = summonerInfo_LAN.summonerId '
                  'INNER JOIN participants_LAN '
                  'ON participantIdentities_LAN.participantId = participants_LAN.participantId '
                  'AND participantIdentities_LAN.matchId = participants_LAN.matchId '
                  'INNER JOIN match_LAN ON participants_LAN.matchId = match_LAN.matchId '
                  'INNER JOIN matchList_LAN ON participants_LAN.matchId = matchList_LAN.matchId '
                  'WHERE summoners.twitch_username = %s '
                  'UNION '
                  'SELECT kills,deaths,assists,matchCreation,matchDuration,participants_LAS.championId,winner,lane,'
                  'summoners.summoner, participants_LAS.matchId, region '
                  'FROM summoners '
                  'INNER JOIN summonerInfo_LAS ON summoners.summoner = summonerInfo_LAS.summoner '
                  'INNER JOIN participantIdentities_LAS '
                  'ON participantIdentities_LAS.summonerId = summonerInfo_LAS.summonerId '
                  'INNER JOIN participants_LAS '
                  'ON participantIdentities_LAS.participantId = participants_LAS.participantId '
                  'AND participantIdentities_LAS.matchId = participants_LAS.matchId '
                  'INNER JOIN match_LAS ON participants_LAS.matchId = match_LAS.matchId '
                  'INNER JOIN matchList_LAS ON participants_LAS.matchId = matchList_LAS.matchId '
                  'WHERE summoners.twitch_username = %s '
                  'UNION '
                  'SELECT kills,deaths,assists,matchCreation,matchDuration,participants_OCE.championId,winner,lane,'
                  'summoners.summoner, participants_OCE.matchId, region '
                  'FROM summoners '
                  'INNER JOIN summonerInfo_OCE ON summoners.summoner = summonerInfo_OCE.summoner '
                  'INNER JOIN participantIdentities_OCE '
                  'ON participantIdentities_OCE.summonerId = summonerInfo_OCE.summonerId '
                  'INNER JOIN participants_OCE '
                  'ON participantIdentities_OCE.participantId = participants_OCE.participantId '
                  'AND participantIdentities_OCE.matchId = participants_OCE.matchId '
                  'INNER JOIN match_OCE ON participants_OCE.matchId = match_OCE.matchId '
                  'INNER JOIN matchList_OCE ON participants_OCE.matchId = matchList_OCE.matchId '
                  'WHERE summoners.twitch_username = %s '
                  'UNION '
                  'SELECT kills,deaths,assists,matchCreation,matchDuration,participants_TR.championId,winner,lane,'
                  'summoners.summoner, participants_TR.matchId, region '
                  'FROM summoners '
                  'INNER JOIN summonerInfo_TR ON summoners.summoner = summonerInfo_TR.summoner '
                  'INNER JOIN participantIdentities_TR '
                  'ON participantIdentities_TR.summonerId = summonerInfo_TR.summonerId '
                  'INNER JOIN participants_TR '
                  'ON participantIdentities_TR.participantId = participants_TR.participantId '
                  'AND participantIdentities_TR.matchId = participants_TR.matchId '
                  'INNER JOIN match_TR ON participants_TR.matchId = match_TR.matchId '
                  'INNER JOIN matchList_TR ON participants_TR.matchId = matchList_TR.matchId '
                  'WHERE summoners.twitch_username = %s '
                  'UNION '
                  'SELECT kills,deaths,assists,matchCreation,matchDuration,participants_RU.championId,winner,lane,'
                  'summoners.summoner, participants_RU.matchId, region '
                  'FROM summoners '
                  'INNER JOIN summonerInfo_RU ON summoners.summoner = summonerInfo_RU.summoner '
                  'INNER JOIN participantIdentities_RU '
                  'ON participantIdentities_RU.summonerId = summonerInfo_RU.summonerId '
                  'INNER JOIN participants_RU '
                  'ON participantIdentities_RU.participantId = participants_RU.participantId '
                  'AND participantIdentities_RU.matchId = participants_RU.matchId '
                  'INNER JOIN match_RU ON participants_RU.matchId = match_RU.matchId '
                  'INNER JOIN matchList_RU ON participants_RU.matchId = matchList_RU.matchId '
                  'WHERE summoners.twitch_username = %s '
                  'UNION '
                  'SELECT kills,deaths,assists,matchCreation,matchDuration,participants_NA.championId,winner,lane,'
                  'summoners.summoner, participants_NA.matchId, region '
                  'FROM summoners '
                  'INNER JOIN summonerInfo_NA ON summoners.summoner = summonerInfo_NA.summoner '
                  'INNER JOIN participantIdentities_NA '
                  'ON participantIdentities_NA.summonerId = summonerInfo_NA.summonerId '
                  'INNER JOIN participants_NA '
                  'ON participantIdentities_NA.participantId = participants_NA.participantId '
                  'AND participantIdentities_NA.matchId = participants_NA.matchId '
                  'INNER JOIN match_NA ON participants_NA.matchId = match_NA.matchId '
                  'INNER JOIN matchList_NA ON participants_NA.matchId = matchList_NA.matchId '
                  'WHERE summoners.twitch_username = %s '
                  ') AS unitedNations '  # this is a joke. it's the union of all the regions
                  'ORDER BY matchCreation DESC '
                  'LIMIT 1', [channel, channel, channel, channel, channel, channel, channel, channel, channel,
                              channel, channel])

        row = c.fetchone()
        if row is None:
            logging.debug('no games found for twitch username: ' + channel)
            hexchat.command('say No games found for {user}.'
                            ' (Have you registered your summoners at hoffmannbot.com?)'.format(
                                user=alias
                            ))
            return hexchat.EAT_ALL

        gameEndTime = int((row[3] / 1000) + row[4])
        etimeSinceGame = calendar.timegm(time.gmtime()) - gameEndTime  # current time - start time
        conversion = etimeSinceGame
        minutes, seconds = divmod(conversion, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        if 'champId' not in CHAMPIONS:
            static_data_response = requests.get(
                'https://global.api.pvp.net/api/lol/static-data/na/v1.2/champion/{champId}?api_key=50992d27-0c22-4d2d-b529-903be10b4e64'.format(
                    champId=int(row[5])
                )
            )
            champ = static_data_response.json()['name']
            logging.info('<==========> ADD TO CONSTS {champId}:{champ} <==========>'.format(
                champId=str(row[5]),
                champ=champ
            ))
        else:
            champ = CHAMPIONS['champId']

        # lastgame = '{user} went {kills}/{deaths}/{assists} on {champ} {lane} and {result} ' \
        #            '[{days}{hours}{minutes} ago, account: {account} ({region})' \
        #            ', <match history link>' \
        #            ']'\
        lastgame = '{user} went {kills}/{deaths}/{assists} on {champ} {lane} and {result} ' \
                   '[{days}{hours}{minutes} ago, account: {account} ({region})' \
                   ', http://matchhistory.{region}.leagueoflegends.com/en/#match-details/{platform}/{matchId}' \
                   ']' \
            .format(
            user=alias,
            kills=row[0],
            deaths=row[1],
            assists=row[2],
            days=str(days) + 'd' if days != 0 else '',
            hours=str(hours) + 'h' if hours != 0 else '',
            minutes=str(minutes) + 'm',
            champ=champ,
            result='won' if row[6] else 'lost',
            lane=row[7].lower(),
            account=row[8],
            region=(Riot_Consts.REGIONS[row[10]]).upper(),
            platform=Riot_Consts.PLATFORMS[row[10]],
            matchId=row[9]
        ) \
            if not (row[4] < 300 and row[0] == row[1] == row[2] == 0) \
            else '{user}\'s last game was a remake [{days}{hours}{minutes} ago, account: {account}]' \
            .format(user=alias, days=str(days) + 'd' if days != 0 else '', hours=str(hours) + 'h' if hours != 0 else '',
                    minutes=str(minutes) + 'm', account=row[8])

        hexchat.command('say ' + lastgame)
        return hexchat.EAT_ALL

    elif command == '!debug':
        # The next lines put the command in jake-only mode
        username = word[0]
        if username != 'jakehoffmann':
            hexchat.command('say ' + command + ' is Jake-only')
            return hexchat.EAT_ALL
        refresh_live_streams()
        return hexchat.EAT_ALL

    elif command == '!rank':
        command_use_time = time.time()
        if (command_use_time - lcu_rank) <= 10:
            return hexchat.EAT_ALL
        c.execute('UPDATE users SET lcu_rank=%s,last_command_use=%s '
                  'WHERE twitch_username=%s', [command_use_time, command_use_time, channel])

        c.execute("SELECT summoner,league,division,league_points,in_series,series_wins,series_losses "
                  "FROM summoners WHERE twitch_username=%s", [channel])
        summoners = c.fetchall()
        ranks_list = ''
        if not summoners:
            hexchat.command('say No summoners found!')
            return hexchat.EAT_ALL
        for summoner in summoners:
            ranks_list += (summoner[0] + ': ' + summoner[1].title() + ' ' + summoner[2] + ', ' + str(summoner[3]) +
                           'LP')
            if summoner[4]:
                ranks_list += ' (Series, ' + str(summoner[5]) + '-' + str(summoner[6]) + '), '
            else:
                ranks_list += ', '
        hexchat.command('say ' + ranks_list[:-2])
        return hexchat.EAT_ALL

    elif command == '!hi':
        command_use_time = time.time()
        if (command_use_time - lcu_hi) <= 10:
            return hexchat.EAT_ALL
        c.execute('UPDATE users SET lcu_hi=%s,last_command_use=%s '
                  'WHERE twitch_username=%s', [command_use_time, command_use_time, channel])
        hexchat.command('say Hello, I\'m here!')

    elif command == '!currentgame' or command == '!current':
        command_use_time = time.time()
        if (command_use_time - lcu_current) <= 5:
            return hexchat.EAT_ALL
        c.execute('UPDATE users SET lcu_current=%s,last_command_use=%s '
                  'WHERE twitch_username=%s', [command_use_time, command_use_time, channel])

        logging.debug('currentgame')
        c.execute("SELECT summoner,gameId,gameLength,championId,region FROM summoners "
                  "WHERE twitch_username=%s AND current_game_exists='true'", [channel])
        current_game = c.fetchone()
        if current_game is None:
            logging.debug('no current game found for twitch username: ' + channel)
            hexchat.command('say {user} is not in a game.'.format(
                user=alias
            ))
            return hexchat.EAT_ALL
        logging.debug('active summoner: {}'.format(current_game[0]))
        active_game_length = current_game[2]
        active_game_champ = CHAMPIONS[current_game[3]]

        rune_list = ''
        c.execute('SELECT count,runeId FROM currentRunes' + '_' + current_game[4] + ' '
                                                                                    'WHERE summoner=%s AND gameId=%s',
                  [current_game[0], current_game[1]])
        for row in c:
            rune_list += str(row[0]) + 'x ' + RUNES[row[1]] + ', '
        rune_list = rune_list[:-2]

        banned_champ_list = ''
        c.execute('SELECT championId FROM currentBans' + '_' + current_game[4] + ' '
                                                                                 'WHERE summoner=%s AND gameId=%s',
                  [current_game[0], current_game[1]])
        for row in c:
            banned_champ_list += CHAMPIONS[row[0]] + '/'

        minutes = (active_game_length // 60) + 3
        hexchat.command('say {beginning} as {champ}{length}.{runes}{bans}'.format(
            beginning='Going into game' if active_game_length == 0 else 'In game',
            champ=active_game_champ,
            length=' for ' + str(minutes) + 'm' if active_game_length != 0 else '',
            runes=' ' + rune_list + '.' if 'runes' in word[1].split() else '',
            bans=' Bans: ' + banned_champ_list[:-1] + '.' if 'bans' in word[1].split() else ''
        ))
        return hexchat.EAT_ALL

    elif command == "!title":
        print('user: ', user)
        print('channel: ', channel)
        print('title: ', word[1][7:139])
        if user != channel:
            return hexchat.EAT_ALL
        c.execute('UPDATE users SET title_base=%s WHERE twitch_username=%s', [word[1][7:139], channel])
        conn.commit()
        hexchat.command('say Submitted! Your title will reflect the change shortly.')
        return hexchat.EAT_ALL


# ---- OLD VERSION ---- #
# ----             ---- #
# this function is called every time somebody types in chat
def channelmessage_cb(word, word_eol, userdata):
    global r
    global matchList
    global matchInfo
    global lastgame_timeout
    global currentgame_timeout
    global title_base
    global title_dynamic
    global current_game_info
    command = word[1].split()[0]

    if command == '!lastgame' or command == '!last':
        if (time.time() - lastgame_timeout) <= 5:
            return hexchat.EAT_ALL
        lastgame_timeout = time.time()

        # The next 4 lines put !lastgame in jake-only mode
        # username = word[0]
        # if username != 'jakehoffmann':
        #     hexchat.command('say hoffmannbot commands are Jake-only at the moment :)')
        #     return hexchat.EAT_ALL

        logging.debug('lastgame')

        endTimeTemp = 0
        mostRecent = 0  # index of most recent game
        for index in range(len(SUMMONERS)):
            if endTimeTemp < matchInfo[index]['matchCreation']:
                endTimeTemp = matchInfo[index]['matchCreation']
                mostRecent = index

        summ_id = r[mostRecent][SUMMONERS[mostRecent]]['id']
        lane = matchList[mostRecent]['matches'][0]['lane']
        participantId = None  # are these necessary?
        champId = None
        kills = None
        deaths = None
        assists = None
        gameResult = None

        # get the participantId from the summonerId
        for players in matchInfo[mostRecent]['participantIdentities']:
            if players['player']['summonerId'] == id:  # can I do this in a nicer way?
                participantId = players['participantId']

        for players in matchInfo[mostRecent]['participants']:
            if players['participantId'] == participantId:
                champId = players['championId']
                kills = players['stats']['kills']
                deaths = players['stats']['deaths']
                assists = players['stats']['assists']
                if players['stats']['winner']:
                    gameResult = 'won'
                else:
                    gameResult = 'lost'

                logging.debug('champId: ' + str(champId))
        # maybe make champId:champ constants
        response = requests.get(
            'https://global.api.pvp.net/api/lol/static-data/na/v1.2/champion/{champId}\
            ?api_key=50992d27-0c22-4d2d-b529-903be10b4e64'.format(
                champId=champId
            )
        )
        logging.debug('global data champ: \n')
        logging.debug(response.json())
        champ = response.json()['name']
        logging.debug(champ)

        gameEndTime = int((matchInfo[mostRecent]['matchCreation'] / 1000) + matchInfo[mostRecent]['matchDuration'])
        etimeSinceGame = calendar.timegm(time.gmtime()) - gameEndTime  # current time - start time
        conversion = etimeSinceGame
        minutes, seconds = divmod(conversion, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        lastgame = 'Jake went {kills}/{deaths}/{assists} on {champ} {lane} and {result} [{days}{hours}{minutes} ago,\
         account: {account}, http://matchhistory.na.leagueoflegends.com/en/#match-details/NA1/{matchId}]'.format(
            kills=kills,
            deaths=deaths,
            assists=assists,
            days=str(days) + 'd' if days != 0 else '',
            hours=str(hours) + 'h' if hours != 0 else '',
            minutes=str(minutes) + 'm',
            champ=champ,
            result=gameResult,
            lane=lane.lower(),
            account=SUMMONERS[mostRecent],
            matchId=matchList[mostRecent]['matches'][0]['matchId']
        )
        hexchat.command('say ' + lastgame)
        return hexchat.EAT_ALL
    elif command == '!currentgame' or command == '!current':
        if (time.time() - currentgame_timeout) <= 5:
            return hexchat.EAT_ALL
        currentgame_timeout = time.time()
        logging.debug('currentgame')
        active_summoner = -1
        for index in range(len(SUMMONERS)):
            if len(current_game_info[index]) > 1:
                active_summoner = index
        if active_summoner == -1:
            hexchat.command('say Jake is not in a game.')
            return hexchat.EAT_ALL
        logging.debug('active summoner index ' + str(active_summoner))
        logging.debug('active summoner ' + SUMMONERS[active_summoner])
        logging.debug(current_game_info)
        active_game_length = current_game_info[active_summoner]['gameLength']

        for participants in current_game_info[active_summoner]['participants']:
            if participants['summonerName'].lower() == SUMMONERS[active_summoner].lower():
                active_game_champId = participants['championId']
                active_game_runes = participants['runes']
                logging.debug(active_game_runes)
                logging.debug(type(active_game_runes))
        static_data_response = requests.get(
            'https://global.api.pvp.net/api/lol/static-data/na/v1.2/champion/{champId}\
            ?api_key=50992d27-0c22-4d2d-b529-903be10b4e64'.format(
                champId=active_game_champId
            )
        )
        rune_list = ''
        for rune in active_game_runes:
            if rune['runeId'] not in RUNES:
                RUNES['runeId'] = requests.get(
                    'https://global.api.pvp.net/api/lol/static-data/na/v1.2/rune/{runeId}\
                    ?api_key=50992d27-0c22-4d2d-b529-903be10b4e64'.format(
                        runeId=rune['runeId'])).json()['name'][8:]
            rune_list += str(rune['count']) + 'x ' + RUNES['runeId'] + ', '
            logging.debug('runeId: ' + str(rune['runeId']) + ' name: ' + RUNES['runeId'])

        rune_list = rune_list[:-2]
        active_game_champ = static_data_response.json()['name']
        banned_champ_list = ''
        for champs in current_game_info[active_summoner]['bannedChampions']:
            banned_champ_list += requests.get(
                'https://global.api.pvp.net/api/lol/static-data/na/v1.2/champion/{champId}\
                ?api_key=50992d27-0c22-4d2d-b529-903be10b4e64'.format(
                    champId=champs['championId'])).json()['name'] + ','
        banned_champ_list = banned_champ_list[:-1]
        # note that the game length is minutes+3 due to spectator delay
        minutes = (active_game_length // 60) + 3
        if active_game_length == 0:
            hexchat.command('say ' + 'Going into game as {champ}.{runes}{bans}'.format(
                champ=active_game_champ,
                runes=' ' + rune_list + '.' if 'runes' in word[1].split() else '',
                bans=' ' + banned_champ_list + '.' if 'bans' in word[1].split() else ''
            ))
        else:
            hexchat.command('say ' + 'In game as {champ} for {length}m.{runes}{bans}'.format(
                champ=active_game_champ,
                length=minutes,
                runes=' ' + rune_list + '.' if 'runes' in word[1].split() else '',
                bans=' Bans: ' + banned_champ_list + '.' if 'bans' in word[1].split() else ''
            ))
        # if bans argument was used

        # if runes argument was used
        return hexchat.EAT_ALL
    elif command == '!time' or command == '!now':
        # TODO: write this function to display the time in my timezone
        return hexchat.EAT_ALL
    elif command == '!title':
        username = word[0]
        print('username: ' + username + ' channel: ' + hexchat.get_info('channel')[1:])
        if username != hexchat.get_info('channel')[1:]:
            # hexchat.command('say No! Not for you!')
            return hexchat.EAT_ALL
        c.execute('UPDATE users SET title_base=%s', [word[1][7:]])
        # title_base = word[1][7:]
        update_title()
        return hexchat.EAT_ALL
    elif command == '!hi':
        hexchat.command('say Hello, I\'m here!')
    elif command == "!test":
        print(hexchat.get_info('channel'))
        hexchat.command('say hello ' + hexchat.get_info('channel'))
    else:
        return hexchat.EAT_ALL


def loaded_cb(userdata):
    print('Hoffmannbot loaded...')
    return 1


def unload_cb(userdata):
    conn.commit()
    c.close()
    conn.close()
    print('==========Hoffmannbot unloaded==========')


print('==========Hoffmannbot loaded============')
refresh_channels()

# load_data()

### champion static data
# response = requests.get('https://global.api.pvp.net/api/lol/static-data/na/v1.2/champion?api_key=50992d27-0c22-4d2d-b529-903be10b4e64')
# champion_data = response.json()
# print(champion_data['data'])
# for champ in champion_data['data']:
#     CHAMPIONS[champion_data['data'][champ]['id']] = champion_data['data'][champ]['name']
#     print(str(champion_data['data'][champ]['id'])+':\''+champion_data['data'][champ]['name']+'\',')

### runes static data
# response = requests.get('https://global.api.pvp.net/api/lol/static-data/na/v1.2/rune?api_key=50992d27-0c22-4d2d-b529-903be10b4e64')
# runes_data = response.json()
# for rune in runes_data['data']:
#     RUNES[runes_data['data'][rune]['id']] = runes_data['data'][rune]['name']
# logging.debug(RUNES)

### database versions
hexchat.hook_timer(5000, refresh_live_streams)             # update which streams are currently live
hexchat.hook_timer(5000, update_twitch_title)              # update twitch titles
hexchat.hook_timer(5000, update_database_cb)               # update the database with new Riot API info
hexchat.hook_print('Channel Message', channel_message_cb)  # respond to Twitch chat messages
hexchat.hook_timer(300000, refresh_channels)               # refresh the channel list every 5 mins (300k milliseconds)

### local only versions
# update_cb('')
# hexchat.hook_timer(3000, update_cb)
# hexchat.hook_print('Channel Message', channelmessage_cb)


# hexchat.hook_timer(5000, loaded_cb)
hexchat.hook_unload(unload_cb)
