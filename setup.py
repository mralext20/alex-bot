# creates databases in postgres
import sys


def leave(str):
    print(str)
    exit(1)

try:
    assert sys.version_info[0] == 3 and sys.version_info[1] > 6
except AssertionError:
    leave("you need to have python 3.6 or later.")


try:
    import config
    import psycopg2
except ImportError(config):
    leave("you need to make a config. please read the README.md for help.")
except ImportError(psycopg2):
    leave("you need to install the requirements.")


for i in [config.dsn, config.token]:
    try:
        assert isinstance(i, str)
    except AssertionError:
        leave("please fill in the config file.")

cur = psycopg2.connect(config.dsn).cursor()

cur.execute("""CREATE TABLE tags (hash TEXT PRIMARY KEY, name TEXT, guild BIGINT, content TEXT, author BIGINT""")
print("created tags table")
