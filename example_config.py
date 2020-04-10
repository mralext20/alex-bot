# config file. copy to `config.py` and fill in your details.

import os

token = ""

cat_token = os.environ.get('THECATAPI_KEY')

dsn = os.environ.get('POSTGRES_URI')

prefix = "a!"

location = "prod or dev"

government_is_working = True

logging = {
    'info': 'webhook url here',
    'warning': 'webhook here too',
    'error': 'webhook url here three',

}
#  bots who's owner gets a dm whenever they go offline
monitored_bots = {
    288369203046645761: {  # Mousey
        'owner_id': 69198249432449024,  # SnowyLuma
        'shard_count': 2,  # Optional shard count of the Bot
    },
}


listenServers = [272885620769161216]
listens = ['alex', 'alaska']
