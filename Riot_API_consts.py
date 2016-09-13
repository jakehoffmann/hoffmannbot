URL = {
    'base': 'https://{proxy}.api.pvp.net/api/lol/{region}/{url}',
    'spectator_base': 'https://{proxy}.api.pvp.net/observer-mode/rest/consumer/getSpectatorGameInfo/{platform}/{url}',
    'summoner_by_name': 'v{version}/summoner/by-name/{names}',
    'matchlist': 'v{version}/matchlist/by-summoner/{id}',
    'match': 'v{version}/match/{matchId}',
    'currentgame': '{id}'
}

API_VERSIONS = {
    'summoner': '1.4',
    'matchlist': '2.2',
    'match': '2.2'
}

REGIONS = {
    'north_america': 'na',
    'spectator_region_na': 'NA1'
}

PLATFORMS = {
    'north_america': 'NA1'
}