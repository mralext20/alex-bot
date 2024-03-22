# config file. copy to `config.py` and fill in your details.

import os
from typing import List

import discord

from alexBot.classes import ButtonRole, FeedConfig, RingRate, SugeryUser, SugeryZone
from alexBot.cogs.sugery import Sugery

hass_token = os.environ.get('HASS_TOKEN')

hass_host = os.environ.get('HASS_HOST')

hass_target = os.environ.get('HASS_TARGET')

ha_webhook_notifs: str = None


token = os.environ.get('BOT_TOKEN')

cat_token = os.environ.get('THECATAPI_KEY')

prefix = "a!"

location = "prod or dev"


nerdiowoBannedPhrases = ['elon', 'musk', 'tesla']

nerdiowoRoles = {
    "Texas": 1052661471034736710,
    "Germany": 1052568850694164571,
    "North Carolina": 1052405508277031063,
    "Alaskan": 1052376307696148571,
    "UK": 1052070749550153789,
}


nerdiowoRolesMessageId = None

feedPosting: List[FeedConfig] = [
    FeedConfig(
        1054601016315744296,  # a tag ID
        "https://www.youtube.com/feeds/videos.xml?channel_id=UCO-zhhas4n_kAPHaeLe1qnQ",  # techdiff
    ),
]


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
