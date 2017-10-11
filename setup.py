# creates databases in mongodb
import sys


def leave(str):
    print(str)
    exit(1)

try:
    assert sys.version_info[0] == 3 and sys.version_info[1] > 5
except AssertionError:
    leave("you need to have python 3.6 or later.")


try:
    import config
    import pymongo
    import pymongo.errors
except ImportError(config):
    leave("you need to make a config. please read the README.md for help.")
except ImportError(pymongo):
    leave("you need to install the requirements.")


for i in [config.mongo, config.token]:
    try:
        assert isinstance(i, str)
    except AssertionError:
        leave("please fill in the config file.")

try:
    mongo = pymongo.MongoClient(config.mongo)
except:
    leave("uh ur auth is wrong kiddo, or smthin")


db = mongo.alexbot

tags = db.tags
configs = db.configs

# initial tag from b1nZ for tags
tags.insert_one({"NAME":"hello world",
                 "CONTENT":"Its nice to meet you.",
                 "GUILD":295341979800436736,
                 "AUTHOR":80351110224678912,
                 "HASH": "1ca25c85001011127a3db6712b5e425b4ad4672c9754535b81e72f99c784112e"})

# initial config for memework
configs.insert_one({"ID":295341979800436736,
                    "TYPE": "GUILD",
                    "CURRENCY": True})


print("Done!")
