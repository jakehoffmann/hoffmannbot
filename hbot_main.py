import hexchat
import requests
import time
import calendar
import json
# import sqlite3
import psycopg2
import urllib.parse
import logging
import random
import sys
import os
# When loading via Hexchat, the file path of the loaded script isn't included in the paths
#  that modules are loaded from. I include it explicitly in the following line(s).
# sys.path.append(r'D:\hoffmannbot')
sys.path.append(os.getcwd()+'\\..')
print(os.getcwd()+'\\..')


from static_data import RUNES, CHAMPIONS
from Riot_API_consts import URL, API_VERSIONS, REGIONS, PLATFORMS

# logging.basicConfig(filename='D:\hoffmannbot\logs\log.txt', level=logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)

__module_name__ = "hoffmannbot"
__module_version__ = "1.0"
__module_description__ = "Twitch Chat Bot with Jake's custom commands"

# connecting to sqlite3 database
# conn = sqlite3.connect(r"D:\hoffmannbot\hoffmannbot_server\database.db", timeout=10)
# c = conn.cursor()

# connecting to postgres database
urllib.parse.uses_netloc.append("postgres")
url = urllib.parse.urlparse(os.environ["DATABASE_URL"])

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

class RiotAPI(object):

    def __init__(self, api_key, region=REGIONS['north_america'], platform=PLATFORMS['north_america']):
        self.api_key = api_key
        self.region = region
        self.platform = platform
        self.lastRequestTime = 0


# API request to riot server using the normal base URL for their API
    def _request(self, api_url, spectator=0, params={}):
        global last_request_time
        diff = time.time() - last_request_time
        if diff <= 5:
            return 1
        args = {'api_key': self.api_key}
        for key, value in params.items():
            if key not in args:
                args[key] = value
        if not spectator:
            response = requests.get(
                URL['base'].format(
                    proxy=self.region,
                    region=self.region,
                    url=api_url
                ),
                params=args
            )
        else:
            response = requests.get(
                URL['spectator_base'].format(
                    proxy=self.region,
                    platform=self.platform,
                    url=api_url
                ),
                params=args
            )
        last_request_time = time.time()
        logging.debug('status code: ')
        logging.debug(response.status_code)
        if response.status_code != 200:
            logging.debug('headers: ')
            logging.debug(response.headers)
            return response.status_code

        logging.debug(response.url)
        return response.json()


# get info about a summoner
    def get_summoner_by_name(self, name):
        api_url = URL['summoner_by_name'].format(
            version=API_VERSIONS['summoner'],
            names=name
        )
        return self._request(api_url)


# get match history. hardcoded in to be only last 10 games. Edit the endIndex to change this
    def get_matchlist(self, summonerid):
        api_url = URL['matchlist'].format(
            version=API_VERSIONS['matchlist'],
            id=summonerid
        )
        return self._request(api_url,  params={'rankedQueues': 'TEAM_BUILDER_DRAFT_RANKED_5x5',
                                               'beginIndex': '0', 'endIndex': '10'})


# get current game info. uses special request due to the base URL being unique in Riot API
    def get_current_game(self, summonerid):
        api_url = URL['currentgame'].format(
            id=summonerid
        )
        return self._request(api_url, spectator=1)

    def get_match_info(self, matchId):
        api_url = URL['match'].format(
            version=API_VERSIONS['match'],
            matchId=matchId
        )
        return self._request(api_url)


def load_data():
    global title_base
    url = 'https://api.twitch.tv/kraken/channels/jakehoffmann'
    headers = {'Accept': 'application/vnd.twitchtv.v3+json',
               'Authorization': 'OAuth 6rlublf96ewjbb4psc2gg0hxkp8hy0',
               'Client-ID': '49mrp5ljn2nj44sx1czezi44ql151h2',
               'content-type': 'application/json'
               }
    response = requests.get(url=url, headers=headers)
    logging.debug('twitch API status code: '+str(response.status_code))
    title_base = response.json()['status']
    logging.debug('retrieved title_base: '+title_base)


# might want to hide this in a file. easy locally but need a heroku solution
def fetch_key():
    key = '50992d27-0c22-4d2d-b529-903be10b4e64'
    return key


# this gets called automatically every X minutes (via hook_timer at bottom of script)
# updates the database with information from Riot API
def update_cb(userdata):
    logging.debug('Recaching API data')

    global r
    global matchList
    global matchInfo
    global current_game_info

    api = RiotAPI('50992d27-0c22-4d2d-b529-903be10b4e64')
    for index in range(len(SUMMONERS)):
        if not r[index] or (time.time() - r[index].get('cacheTime', 0)) > 300:
            result = api.get_summoner_by_name(SUMMONERS[index])
            if not isinstance(result, int):
                logging.debug('summoner info for '+SUMMONERS[index]+' cached')
                r[index] = result
                r[index]['cacheTime'] = time.time()
            else:
                continue
        if not matchList[index] or (time.time() - matchList[index].get('cacheTime', 0)) > 300:
            summ_id = r[index][SUMMONERS[index]]['id']
            result = api.get_matchlist(summ_id)
            if not isinstance(result, int):
                logging.debug('summoner matchlist for ' + SUMMONERS[index] + ' cached')
                matchList[index] = result
                matchList[index]['cacheTime'] = time.time()
            else:
                continue
        if not matchInfo[index] or (time.time() - matchInfo[index].get('cacheTime', 0)) > 300:
            matchId = matchList[index]['matches'][0]['matchId']
            result = api.get_match_info(matchId)
            if not isinstance(result, int):
                logging.debug('summoner matchinfo for ' + SUMMONERS[index] + ' cached')
                matchInfo[index] = result
                matchInfo[index]['cacheTime'] = time.time()
        if not current_game_info[index] or (time.time() - current_game_info[index].get('cacheTime', 0)) > 60:
            summ_id = r[index][SUMMONERS[index]]['id']
            result = api.get_current_game(summ_id)
            if result == 404:
                logging.debug('current game for ' + SUMMONERS[index] + ' not found!')
                current_game_info[index] = {}
                current_game_info[index]['cacheTime'] = time.time()
                if index == len(SUMMONERS)-1:
                    update_title()
            elif not isinstance(result, int):
                logging.debug('current game info for ' + SUMMONERS[index] + ' cached')
                current_game_info[index] = result
                current_game_info[index]['cacheTime'] = time.time()
                update_title(index)

    return 1


# new version of update_cb that uses database instead of memory
def update_database_cb(userdata):
    print('Recaching API data')

    # TODO: RE performance: perhaps insert a line here that will return if the Riot API has been called too recently

    api = RiotAPI(fetch_key())

    # base delay in seconds before querying Riot API again (before exponential back-off)
    summoner_info_query_base = 90000000  # TODO: how often to re-query this, if ever?
    match_list_query_base = 900000000000
    current_game_query_base = 60

    siq_cap = 3600                  # summoner info query exponential back-off cap
    ml_cap = 180                    # match list query exponential back-off cap
    cg_cap = 60                     # current game query exponential back-off cap

    c.execute('SELECT summoner, twitch_username, info_cache_time, match_list_cache_time, '
              'current_game_cache_time FROM summoners')
    summoners = c.fetchall()

    for index in range(len(summoners)):
        c.execute('SELECT summonerId FROM summonerInfo WHERE summoner=?',
                  [summoners[index][0]])
        summoner_info = c.fetchone()
        c.execute('SELECT last_command_use FROM users WHERE twitch_username=?', [summoners[index][1]])
        last_command_use = c.fetchone()[0]

        # summoner_info_query_wait = random.randint(0, min(siq_cap, summoner_info_query_base * 2 ** last_command_use))
        summoner_info_query_wait = summoner_info_query_base
        if summoner_info is None or (time.time() - summoners[index][2]) > summoner_info_query_wait:
            result = api.get_summoner_by_name(summoners[index][0])
            if not isinstance(result, int):
                temp_summoner_name = ''.join(summoners[index][0].split()).lower()
                temp_cache_time = time.time()
                print('summoner info for '+temp_summoner_name+' cached')
                c.execute('INSERT OR REPLACE INTO summonerInfo (summoner, summonerId)'
                          'VALUES (?,?)', [temp_summoner_name, result[temp_summoner_name]['id']])
                c.execute('UPDATE summoners SET info_cache_time=? WHERE summoner=?',
                          [temp_cache_time, temp_summoner_name])
                conn.commit()
            else:
                continue
        c.execute('SELECT summonerId FROM summonerInfo WHERE summoner=?',
                  [summoners[index][0]])
        summoner_info = c.fetchone()

        # match_list_query_wait = random.randint(0, min(ml_cap, match_list_query_base * 2 ** last_command_use))
        match_list_query_wait = match_list_query_base
        if summoners[index][3] == 0 or (time.time() - summoners[index][3] > match_list_query_wait):
            result = api.get_matchlist(summoner_info[0])
            if not isinstance(result, int):
                c.execute('UPDATE summoners SET match_list_cache_time=? WHERE summoner=?',
                          [time.time(), summoners[index][0]])
                if result['totalGames'] != 0:
                    for match in result['matches']:
                        c.execute('INSERT OR REPLACE INTO matchList (matchId, timestamp, summonerId, lane) '
                                  'VALUES (?,?,?,?)',
                                  [match['matchId'], match['timestamp'], summoner_info[0], match['lane']])
                conn.commit()
                print('match list cached for '+summoners[index][0])
            else:
                continue

        # current_game_query_wait = random.randint(0, min(cg_cap, current_game_query_base * 2 ** last_command_use))
        current_game_query_wait = current_game_query_base
        if summoners[index][4] == 0 or (time.time() - summoners[index][4] > current_game_query_wait):
            result = api.get_current_game(summoner_info[0])
            if result == 404:
                print('current game for ' + summoners[index][0] + ' not found')
                c.execute('UPDATE summoners SET current_game_exists=?, current_game_cache_time=? '
                          'WHERE summoner=?', [0, time.time(), summoners[index][0]])
                c.execute('DELETE from currentRunes where summoner=?', [summoners[index][0]])
                c.execute('DELETE from currentBans where summoner=?', [summoners[index][0]])
                conn.commit()
                # TODO: update title if necessary
            elif not isinstance(result, int):
                print('current game info for ' + summoners[index][0] + ' cached')
                active_game_length = result['gameLength']
                for participants in result['participants']:
                    if ''.join(participants['summonerName'].split()).lower() == summoners[index][0]:
                        active_game_champId = participants['championId']
                        active_game_runes = participants['runes']
                c.execute('UPDATE summoners SET current_game_exists=?, current_game_cache_time=?, gameLength=?,'
                          ' championId=?, gameId=? WHERE summoner=?',
                          [1, time.time(), active_game_length, active_game_champId, result['gameId'],
                           summoners[index][0]])
                for rune in active_game_runes:
                    c.execute('INSERT OR REPLACE INTO currentRunes (count, runeId, summoner, gameId) VALUES (?,?,?,?)',
                              [rune['count'], rune['runeId'], summoners[index][0], result['gameId']])
                for ban in result['bannedChampions']:
                    c.execute('INSERT OR REPLACE INTO currentBans (championId, summoner, gameId) VALUES (?,?,?)',
                              [ban['championId'], summoners[index][0], result['gameId']])
                conn.commit()

        # TODO: is it necessary to execute this every time? maybe have a global list of unstored matches?
        c.execute('SELECT matchId, timestamp FROM matchList WHERE matchId NOT IN (SELECT matchId FROM match) '
                  'ORDER BY timestamp DESC')
        unstored_matches = c.fetchall()  # list of 1-tuples
        if len(unstored_matches) != 0:
            result = api.get_match_info((unstored_matches.pop(0))[0])
            if not isinstance(result, int):
                print('Updating matches from match list')
                c.execute('INSERT INTO match (matchId,matchCreation,matchDuration) '
                          'VALUES (?,?,?)', [result['matchId'], result['matchCreation'], result['matchDuration']])
                for participantIdentity in result['participantIdentities']:
                    c.execute('INSERT INTO participantIdentities (matchId,participantId,summonerId) '
                              'VALUES (?,?,?)',
                              [result['matchId'],
                               participantIdentity['participantId'],
                               participantIdentity['player']['summonerId']])
                for participant in result['participants']:
                    c.execute('INSERT INTO participants '
                              '(matchId,championId,participantId,kills,deaths,assists,winner) '
                              'VALUES (?,?,?,?,?,?,?)',
                              [result['matchId'], participant['championId'], participant['participantId'],
                               participant['stats']['kills'], participant['stats']['deaths'],
                               participant['stats']['assists'], int(participant['stats']['winner'])])
                    for rune in participant['runes']:
                        c.execute('INSERT INTO runes (participantId,matchId,rank,runeId) VALUES (?,?,?,?)',
                                  [participant['participantId'],
                                   result['matchId'],
                                   rune['rank'],
                                   rune['runeId']
                                   ])
                conn.commit()
                logging.debug('cached a match. match id: ' + str(result['matchId']))

    return hexchat.EAT_ALL


# TODO: finish this sucker
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
        minutes = (active_game_length // 60)+3
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
    logging.debug('Setting title to:' )
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


def channel_message_cb(word, word_eol, userdata):
    global lastgame_timeout
    global currentgame_timeout

    command = word[1].split()[0]  # the first word of a Twitch chat message, possibly a command
    channel = hexchat.get_info('channel')[1:]  # the channel in which the command was used
    c.execute('SELECT alias FROM users WHERE twitch_username=?', [channel])
    is_valid_user = c.fetchone()
    if is_valid_user is None:
        hexchat.command('say I\'m not supposed to be in this channel!')
        return hexchat.EAT_ALL
    alias = is_valid_user[0]

    if command == '!lastgame' or command == '!last':
        if (time.time() - lastgame_timeout) <= 5:
            return hexchat.EAT_ALL
        lastgame_timeout = time.time()
        logging.debug('lastgame')

        # The next 4 lines put !lastgame in jake-only mode
        username = word[0]
        if username != 'jakehoffmann':
            hexchat.command('say !lastgame is Jake-only for testing at the moment :)')
            return hexchat.EAT_ALL

        # channel = hexchat.get_info('channel')[1:]  # the channel in which the command was used
        c.execute('SELECT kills,deaths,assists,matchCreation,matchDuration,participants.championId,winner,lane,'
                  'summoners.summoner, participants.matchId '
                  'FROM summoners '
                  'INNER JOIN summonerInfo ON summoners.summoner = summonerInfo.summoner '
                  'INNER JOIN participantIdentities '
                  'ON participantIdentities.summonerId = summonerInfo.summonerId '
                  'INNER JOIN participants ON participantIdentities.participantId = participants.participantId '
                  'AND participantIdentities.matchId = participants.matchId '
                  'INNER JOIN match ON participants.matchId = match.matchId '
                  'INNER JOIN matchList ON participants.matchId = matchList.matchId '
                  'WHERE summoners.twitch_username = ? '
                  'ORDER BY matchCreation DESC '
                  'LIMIT 1', [channel])
        row = c.fetchone()
        if row is None:
            logging.debug('no games found for twitch username: ' + channel)
            hexchat.command('say No games found for {user}.'.format(
                user=alias if alias != 'noalias' else channel
            ))
            return hexchat.EAT_ALL

        print(row)
        gameEndTime = int((row[3]/1000)+row[4])
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

        lastgame = '{user} went {kills}/{deaths}/{assists} on {champ} {lane} and {result} [{days}{hours}{minutes} ago,\
         account: {account}, http://matchhistory.na.leagueoflegends.com/en/#match-details/NA1/{matchId}]'.format(
            user=alias if alias != 'noalias' else channel,
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
            matchId=row[9]
        )
        hexchat.command('say ' + lastgame)
        return hexchat.EAT_ALL

    elif command == '!currentgame' or command == '!current':
        if (time.time() - currentgame_timeout) <= 5:
            return hexchat.EAT_ALL
        currentgame_timeout = time.time()

        logging.debug('currentgame')
        c.execute('SELECT summoner,gameId,gameLength,championId FROM summoners '
                  'WHERE twitch_username=? AND current_game_exists=1', [channel])
        current_game = c.fetchone()
        if current_game is None:
            logging.debug('no current game found for twitch username: ' + channel)
            hexchat.command('say {user} is not in a game.'.format(
                user=alias if alias != 'noalias' else channel
            ))
            return hexchat.EAT_ALL
        logging.debug('active summoner: {}'.format(current_game[0]))
        active_game_length = current_game[2]
        active_game_champ = CHAMPIONS[current_game[3]]

        rune_list = ''
        for row in c.execute('SELECT count,runeId FROM currentRunes '
                             'WHERE summoner=? AND gameId=?', [current_game[0], current_game[1]]):
            rune_list += str(row[0])+'x '+RUNES[row[1]]+', '
        rune_list = rune_list[:-2]

        banned_champ_list = ''
        for row in c.execute('SELECT championId FROM currentBans '
                             'WHERE summoner=? AND gameId=?', [current_game[0], current_game[1]]):
            banned_champ_list += CHAMPIONS[row[0]]

        minutes = (active_game_length // 60) + 3
        hexchat.command('say {beginning} as {champ}{length}.{runes}{bans}'.format(
            beginning='Going into game' if active_game_length == 0 else 'In game',
            champ=active_game_champ,
            length=' for '+str(minutes)+'m' if active_game_length != 0 else '',
            runes=' ' + rune_list + '.' if 'runes' in word[1].split() else '',
            bans=' Bans: ' + banned_champ_list + '.' if 'bans' in word[1].split() else ''
        ))
        return hexchat.EAT_ALL


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
        mostRecent = 0      # index of most recent game
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

                logging.debug('champId: '+str(champId))
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

        gameEndTime = int((matchInfo[mostRecent]['matchCreation']/1000)+matchInfo[mostRecent]['matchDuration'])
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
            days=str(days)+'d' if days != 0 else '',
            hours=str(hours)+'h' if hours != 0 else '',
            minutes=str(minutes)+'m',
            champ=champ,
            result=gameResult,
            lane=lane.lower(),
            account=SUMMONERS[mostRecent],
            matchId=matchList[mostRecent]['matches'][0]['matchId']
        )
        hexchat.command('say '+lastgame)
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
        logging.debug('active summoner index '+str(active_summoner))
        logging.debug('active summoner '+SUMMONERS[active_summoner])
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
            rune_list += str(rune['count'])+'x '+RUNES['runeId']+', '
            logging.debug('runeId: '+str(rune['runeId'])+' name: '+RUNES['runeId'])

        rune_list = rune_list[:-2]
        active_game_champ = static_data_response.json()['name']
        banned_champ_list = ''
        for champs in current_game_info[active_summoner]['bannedChampions']:
            banned_champ_list += requests.get(
                'https://global.api.pvp.net/api/lol/static-data/na/v1.2/champion/{champId}\
                ?api_key=50992d27-0c22-4d2d-b529-903be10b4e64'.format(
                    champId=champs['championId'])).json()['name']+','
        banned_champ_list = banned_champ_list[:-1]
        # note that the game length is minutes+3 due to spectator delay
        minutes = (active_game_length // 60) + 3
        if active_game_length == 0:
            hexchat.command('say '+'Going into game as {champ}.{runes}{bans}'.format(
                champ=active_game_champ,
                runes=' '+rune_list+'.' if 'runes' in word[1].split() else '',
                bans=' '+banned_champ_list+'.' if 'bans' in word[1].split() else ''
            ))
        else:
            hexchat.command('say '+'In game as {champ} for {length}m.{runes}{bans}'.format(
                champ=active_game_champ,
                length=minutes,
                runes=' '+rune_list+'.' if 'runes' in word[1].split() else '',
                bans=' Bans: '+banned_champ_list+'.' if 'bans' in word[1].split() else ''
            ))
        # if bans argument was used

        # if runes argument was used
        return hexchat.EAT_ALL
    elif command == '!time' or command == '!now':
        # TODO: write this function to display the time in my timezone
        return hexchat.EAT_ALL
    elif command == '!title':
        username = word[0]
        if username != 'jakehoffmann':
            hexchat.command('say No! Not for you!')
            return hexchat.EAT_ALL
        title_base = word[1][7:]
        update_title()
        return hexchat.EAT_ALL
    elif command == "!test":
        print(hexchat.get_info('channel'))
        hexchat.command('say hello '+hexchat.get_info('channel'))
    else:
        return hexchat.EAT_ALL


def loaded_cb(userdata):
    print('Hoffmannbot loaded...')
    return 1


def unload_cb(userdata):
    conn.commit()
    c.close()
    print('==========Hoffmannbot unloaded==========')


print('==========Hoffmannbot loaded============')

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
# hexchat.hook_timer(3000, update_database_cb)
# hexchat.hook_print('Channel Message', channel_message_cb)

### local only versions
# update_cb('')
# hexchat.hook_timer(3000, update_cb)
# hexchat.hook_print('Channel Message', channelmessage_cb)


# hexchat.hook_timer(5000, loaded_cb)
hexchat.hook_unload(unload_cb)
