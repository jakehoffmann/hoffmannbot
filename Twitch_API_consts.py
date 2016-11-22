URL = {
    'base': 'https://api.twitch.tv/kraken/{url}',
    'channels': 'channels/{user}',
    'streams': 'streams'
}

HEADERS = {
    'Accept': 'application/vnd.twitchtv.v3+json',
    'Authorization': 'Oauth {token}',
    'Client-ID': '{client_id}',
    'content-type': 'application/json'
}