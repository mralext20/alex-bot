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
except ImportError:
    leave("you need to make a config. please see example_config.py for help.")

try:
    import aiosqlite
except ImportError:
    leave("please install deps, `python3 -m pip install -r requierments.txt`")


for i in [config.token]:
    try:
        assert isinstance(i, str)
    except AssertionError:
        leave("please fill in the config file.")

cur = sqlite3.connect('configs.db').cursor()


# build tables
with open('schema.sql', 'r') as f:
    cur.executescript(f.read())

print("Done!")
