# config file. copy to `config.py` and fill in your details.

import os

import discord

from alexBot.classes import RingRate, SugeryUser, SugeryZone
from alexBot.cogs.sugery import Sugery

token = os.environ.get('BOT_TOKEN')

cat_token = os.environ.get('THECATAPI_KEY')

prefix = "a!"

location = "prod or dev"


logging = {
    'info': 'webhook url here',
    'warning': 'webhook here too',
    'error': 'webhook url here three',
}
#  bots who's owner gets a dm whenever they go offline
monitored_bots = {
    288369203046645761: {  # Mousey
        'messagable_id': 69198249432449024,  # the bot channel in mousey's server
        'shards': 2,
    },
    701277606758318090: {  # parakarry
        'messagable_id': 125233822760566784,  # mattBSG
        'shared_guild': 314857672585248768,  # a shared guild. will be used instead of scanning any guilds.
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

neosTZData = r"..\neostz\data.json"


suggery = [
    # SugeryUser(
    #     guild=0,
    #     user=0,
    #     baseURL="https://someUser.herokuapp.com",
    #     names={
    #         SugeryZone.VERYLOW: "very low",
    #         SugeryZone.LOW: "low",
    #         SugeryZone.NORMAL: "normal",
    #         SugeryZone.HIGH: "high",
    #         SugeryZone.VERYHIGH: "very high",
    #     },
    # )
]
