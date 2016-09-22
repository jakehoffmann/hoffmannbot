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
    'BR': 'br',
    'EUNE': 'eune',
    'EUW': 'euw',
    'JP': 'jp',
    'KR': 'kr',
    'LAN': 'lan',
    'LAS': 'las',
    'NA': 'na',
    'OCE': 'oce',
    'TR': 'tr',
    'RU': 'ru',

    'spectator_region_na': 'NA1'
}

PLATFORMS = {
    'BR': 'BR1',
    'EUNE': 'EUN1',
    'EUW': 'EUW1',
    'JP': 'JP1',
    'KR': 'KR',
    'LAN': 'LA1',
    'LAS': 'LA2',
    'NA': 'NA1',
    'OCE': 'OC1',
    'TR': 'TR1',
    'RU': 'RU',
}