# config file. copy to `config.py` and fill in your details.

from alexBot.classes import RingRate
import os

import discord

token = os.environ.get('BOT_TOKEN')

cat_token = os.environ.get('THECATAPI_KEY')

avwx_token = os.environ.get('AVWX_KEY')

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
        'messagable_id': 69198249432449024,  # SnowyLuma
        'shared_guild': 383886323699679234,  # shared guild with bot
    },
}


ringRates = {
    discord.Status.online: RingRate(4, 0.5),
    discord.Status.idle: RingRate(10, 1),
    discord.Status.dnd: RingRate(1, 1),
    discord.Status.offline: RingRate(15, 5),
}


listenServers = [272885620769161216]
listens = ['alex', 'alaska']

db = "configs.db"
