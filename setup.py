# creates databases in mongodb
import sys
import sqlite3


def leave(msg):
    print(msg)
    exit(1)


try:
    assert sys.version_info[0] == 3 and sys.version_info[1] > 5
except AssertionError:
    leave("you need to have python 3.6 or later.")


try:
    import config
    import aiosqlite
except ImportError(config):
    leave("you need to make a config. please see example_config.py for help.")
except ImportError(aiosqlite):
    leave("you need to install the requirements.")


for i in [config.token]:
    try:
        assert isinstance(i, str)
    except AssertionError:
        leave("please fill in the config file.")
cur = None
try:
    cur = sqlite3.connect('configs.db').cursor()
except sqlite3.Error:
    leave("uh ur auth is wrong kiddo, or smthin")

# build tables
with open('schema.sql', 'r') as f:
    cur.execute(f.read())

print("Done!")
