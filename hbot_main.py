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

logging.basicConfig(filename='D:\hoffmannbot\logs\log.txt',
                    datefmt='%m-%d %H:%M',
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    level=logging.DEBUG)
# logging.basicConfig(level=logging.DEBUG)

logging.debug('Directory added to sys.path: ' + os.getcwd() + '\\..')

__module_name__ = "hoffmannbot"
__module_version__ = "1.0"
__module_description__ = "Twitch Chat Bot with Jake's custom commands"

# connecting to postgres database
urllib.parse.uses_netloc.append("postgres")

f = open('d:/hoffmannbot/apikey.txt', 'r')
riot_api_key = f.readline()
f.close()
f = open('d:/hoffmannbot/clientid.txt', 'r')
client_id = f.readline()
f.close()
f = open('d:/hoffmannbot/postgresurl.txt', 'r')
postgres_url = f.readline()[:-1]
f.close()

url = urllib.parse.urlparse(postgres_url)

conn = psycopg2.connect(
    database=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port
)
c = conn.cursor()

# variables to make sure I don't spam Twitch chat
currentgame_timeout = 0
lastgame_timeout = 0

issues_exist = False


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
                logging.debug('twitch API call failed, status code: ')
                logging.debug(response.status_code)
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
                logging.debug('twitch API call failed, status code: ')
                logging.debug(response.status_code)
                # logging.debug(response.json())  # This may cause issue
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

    # get match history. hardcoded in to be only last 10 games. Edit the endIndex to change this
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


def fetch_riot_key():
    """Returns the Riot API key"""

    global riot_api_key
    return riot_api_key[:-1]


def fetch_twitch_client_id():
    """Returns the Twitch client ID (like an API key)"""

    global client_id
    return client_id[:-1]


def refresh_channels(userdata):
    """checks for IRC channels to /join and /part

    Retrieves the list of twitch users that are using the bot and /join's new ones and /part's ones that have decided
     not to use the bot anymore.
    """

    c.execute('SELECT twitch_username FROM users')
    updated_channels = c.fetchall()
    current_channels = hexchat.get_list("channels")

    for channel in current_channels[:]:
        logging.debug('looking at ' + channel.channel)
        if channel.channel == 'Twitch':
            current_channels.remove(channel)
        elif channel.channel == '':
            current_channels.remove(channel)
        elif (channel.channel[1:],) in updated_channels:
            logging.debug('remove from channels to join and channels to part lists: ' + channel.channel)
            current_channels.remove(channel)
            updated_channels.remove((channel.channel[1:],))

    for channel in current_channels:
        logging.debug('Executed command: part ' + channel.channel)
        hexchat.command('part ' + channel.channel)

    for channel in updated_channels:
        logging.debug('Executed command: join #' + channel[0])
        hexchat.command('join #' + channel[0])
    return hexchat.EAT_ALL


def channel_message_cb(word, word_eol, userdata):
    """Is called whenever a message is received in HexChat. After a message is detected, we check if it is a valid
    command. If it is, we handle it appropriately. See HexChat Python documentation for information about this
    functions arguments and what it returns.
    """

    global issues_exist
    announcement = "(11/16) There are some issues retrieving Flex queue data. "

    command = word[1].split()[0]  # the first word of a Twitch chat message, possibly a command
    user = word[0]
    channel = hexchat.get_info('channel')[1:]  # the channel in which the command was used
    c.execute('SELECT alias,lcu_last,lcu_current,lcu_hi,lcu_rank,lcu_commands FROM users WHERE twitch_username=%s', [channel])
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
    lcu_commands = is_valid_user[5]

    if command == '!lastgame' or command == '!last':
        command_use_time = time.time()
        if (command_use_time - lcu_last) <= 5:
            return hexchat.EAT_ALL
        c.execute('UPDATE users SET lcu_last=%s,last_command_use=%s '
                  'WHERE twitch_username=%s', [command_use_time, command_use_time, channel])
        conn.commit()
        logging.debug('lastgame')

        # The next lines put the command in jake-only mode
        # username = word[0]
        # if username != 'jakehoffmann':
        #     hexchat.command('say ' + command[1:] + ' is Jake-only for testing at the moment :)')
        #     return hexchat.EAT_ALL

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
                'https://global.api.pvp.net/api/lol/static-data/na/v1.2/champion/{champId}?api_key={api_key}'.format(
                    champId=int(row[5]),
                    api_key=fetch_riot_key()
                )
            )
            logging.debug(static_data_response.url)
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
        lastgame = '{issues}{user} went {kills}/{deaths}/{assists} on {champ} {lane} and {result} ' \
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
            matchId=row[9],
            issues=announcement if issues_exist else ''

        ) \
            if not (row[4] < 300 and row[0] == row[1] == row[2] == 0) \
            else '{user}\'s last game was a remake [{days}{hours}{minutes} ago, account: {account}]' \
            .format(user=alias, days=str(days) + 'd' if days != 0 else '', hours=str(hours) + 'h' if hours != 0 else '',
                    minutes=str(minutes) + 'm', account=row[8])

        hexchat.command('say ' + lastgame)
        return hexchat.EAT_ALL

    elif command == '!rank':
        command_use_time = time.time()
        if (command_use_time - lcu_rank) <= 10:
            return hexchat.EAT_ALL
        c.execute('UPDATE users SET lcu_rank=%s,last_command_use=%s '
                  'WHERE twitch_username=%s', [command_use_time, command_use_time, channel])
        conn.commit()
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
        hexchat.command('say {issues}'.format(
            issues=announcement if issues_exist else ''
                        ) + ranks_list[:-2]
                        )
        return hexchat.EAT_ALL

    elif command == '!hi':
        command_use_time = time.time()
        if (command_use_time - lcu_hi) <= 10:
            return hexchat.EAT_ALL
        c.execute('UPDATE users SET lcu_hi=%s,last_command_use=%s '
                  'WHERE twitch_username=%s', [command_use_time, command_use_time, channel])
        conn.commit()
        hexchat.command('say Hello, I\'m here!')

    elif command == '!commands':
        command_use_time = time.time()
        if (command_use_time - lcu_commands) <= 10:
            return hexchat.EAT_ALL
        c.execute('UPDATE users SET lcu_commands=%s, last_command_use=%s '
                  'WHERE twitch_username=%s', [command_use_time, command_use_time, channel])
        conn.commit()
        hexchat.command('say Find the commands here: http://www.hoffmannbot.com/#/hoffmannbot/commands')
        return hexchat.EAT_ALL

    elif command == '!currentgame' or command == '!current' or command == '!runes' or command == '!bans':
        command_use_time = time.time()
        if (command_use_time - lcu_current) <= 5:
            return hexchat.EAT_ALL
        c.execute('UPDATE users SET lcu_current=%s,last_command_use=%s '
                  'WHERE twitch_username=%s', [command_use_time, command_use_time, channel])
        conn.commit()
        logging.debug('currentgame')
        c.execute("SELECT summoner,gameId,gameLength,championId,region,gameStartTime FROM summoners "
                  "WHERE twitch_username=%s AND current_game_exists='true'", [channel])
        current_game = c.fetchone()
        if current_game is None:
            logging.debug('no current game found for twitch username: ' + channel)
            hexchat.command('say {issues}{user} is not in a game.'.format(
                user=alias,
                issues=announcement if issues_exist else ''
            ))
            return hexchat.EAT_ALL
        logging.debug('active summoner: {}'.format(current_game[0]))
        active_game_length = current_game[2]
        active_game_champ = CHAMPIONS[current_game[3]]
        active_game_start_time = current_game[5]

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

        # This was my original (flawed?) method for displaying time elapsed
        # minutes = (active_game_length // 60) + 3

        # Here is the new way for doing the above
        minutes = int((time.time() - active_game_start_time/1000) // 60)
        hexchat.command('say {issues}{beginning} as {champ}{length}.{runes}{bans}'.format(
            beginning='Going into game' if active_game_length == 0 else 'In game',
            champ=active_game_champ,
            length=' for ' + str(minutes) + 'm' if active_game_length != 0 else '',
            runes=' ' + rune_list + '.' if 'runes' in word[1].split() or command == '!runes' else '',
            bans=' Bans: ' + banned_champ_list[:-1] + '.' if 'bans' in word[1].split() or command == '!bans' else '',
            issues=announcement if issues_exist else ''
        ))
        return hexchat.EAT_ALL

    elif command == "!title":
        logging.debug('user: ', user)
        logging.debug('channel: ', channel)
        logging.debug('title: ', word[1][7:139])
        if user != channel:
            return hexchat.EAT_ALL
        c.execute('SELECT receives_title_updates FROM users WHERE twitch_username=%s', [channel])
        row = c.fetchone()
        if not row[0]:
            return hexchat.EAT_ALL
        c.execute('UPDATE users SET title_base=%s WHERE twitch_username=%s', [word[1][7:139], channel])
        conn.commit()
        hexchat.command('say Submitted! Your title will reflect the change shortly.')
        return hexchat.EAT_ALL

# The following are admin commands

    elif command == '!debug':
        # The next lines put the command in jake-only mode
        username = word[0]
        if username != 'jakehoffmann':
            hexchat.command('say ' + command + ' is Jake-only')
            return hexchat.EAT_ALL
        hexchat.command('say Refreshing channels...')
        refresh_channels(None)
        return hexchat.EAT_ALL

    elif command == "!reflive":
        # The next lines put the command in jake-only mode
        username = word[0]
        if username != 'jakehoffmann':
            hexchat.command('say ' + command + ' is Jake-only')
            return hexchat.EAT_ALL
        hexchat.command('say Updating live channels...')
        refresh_live_streams(None)

    elif command == '!pause':
        # The next lines put the command in jake-only mode
        username = word[0]
        if username != 'jakehoffmann':
            hexchat.command('say ' + command + ' is Jake-only')
            return hexchat.EAT_ALL
        hexchat.command('say Pausing updates.')
        configure('off')
        return hexchat.EAT_ALL

    elif command == '!resume':
        # The next lines put the command in jake-only mode
        username = word[0]
        if username != 'jakehoffmann':
            hexchat.command('say ' + command + ' is Jake-only')
            return hexchat.EAT_ALL
        hexchat.command('say Resuming updates.')
        configure('on')
        return hexchat.EAT_ALL

    elif command == '!issueson':
        # The next lines put the command in jake-only mode
        username = word[0]
        if username != 'jakehoffmann':
            hexchat.command('say ' + command + ' is Jake-only')
            return hexchat.EAT_ALL
        hexchat.command('say Issues noted...')
        global issues_exist
        issues_exist = True
        return hexchat.EAT_ALL

    elif command == '!issuesoff':
        # The next lines put the command in jake-only mode
        username = word[0]
        if username != 'jakehoffmann':
            hexchat.command('say ' + command + ' is Jake-only')
            return hexchat.EAT_ALL
        hexchat.command('say No more issues...')
        global issues_exist
        issues_exist = False
        return hexchat.EAT_ALL


def unload_cb(userdata):
    conn.commit()
    c.close()
    conn.close()
    print('==========Hoffmannbot unloaded==========')

refresh_live_streams_timer = 5*1000
update_twitch_title_timer = 5*1000
update_database_timer = 5*1000
refresh_channels_timer = 60*1000

print('==========Hoffmannbot loaded============')


def configure(mode):
    global hook_1
    global hook_2
    global hook_3
    global hook_4
    if mode == 'off':
        hexchat.unhook(hook_1)
        hexchat.unhook(hook_2)
        hexchat.unhook(hook_3)
        hexchat.unhook(hook_4)
    if mode == 'on':
        hook_1 = None
        hook_2 = None
        hook_3 = None
        hook_4 = hexchat.hook_timer(60 * 1000, refresh_channels)  # refresh the channel list every minute

# load_data()

# champion static data
# response = requests.get('https://global.api.pvp.net/api/lol/static-data/na/v1.2/champion?api_key={api_key}'.format(api_key=fetch_riot_key()))
# champion_data = response.json()
# logging.debug(champion_data['data'])
# for champ in champion_data['data']:
#     CHAMPIONS[champion_data['data'][champ]['id']] = champion_data['data'][champ]['name']
#     logging.debug(str(champion_data['data'][champ]['id'])+':\''+champion_data['data'][champ]['name']+'\',')

# runes static data
# response = requests.get('https://global.api.pvp.net/api/lol/static-data/na/v1.2/rune?api_key={api_key}'.format(api_key=fetch_riot_key()))
# runes_data = response.json()
# for rune in runes_data['data']:
#     RUNES[runes_data['data'][rune]['id']] = runes_data['data'][rune]['name']
# logging.debug(RUNES)

hook_4 = hexchat.hook_timer(300 * 1000, refresh_channels)
hexchat.hook_print('Channel Message', channel_message_cb)    # respond to Twitch chat messages

# local only versions
# update_cb('')
# hexchat.hook_timer(3000, update_cb)
# hexchat.hook_print('Channel Message', channelmessage_cb)


# hexchat.hook_timer(5000, loaded_cb)
hexchat.hook_unload(unload_cb)
