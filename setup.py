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
    import psycopg2
except ImportError(config):
    leave("you need to make a config. please see example_config.py for help.")
except ImportError(psycopg2):
    leave("you need to install the requirements.")


for i in [config.dsn, config.token]:
    try:
        assert isinstance(i, str)
    except AssertionError:
        leave("please fill in the config file.")
cur = None
try:
    cur = psycopg2.connect(config.dsn).cursor()
except psycopg2.Error:
    leave("uh ur auth is wrong kiddo, or smthin")

# build tables
cur.execute("""CREATE TABLE IF NOT EXISTS tags 
               (hash TEXT PRIMARY KEY NOT NULL,
               tag TEXT NOT NULL,
               guild BIGINT NOT NULL, 
               content TEXT NOT NULL, 
               author BIGINT NOT NULL)""")

cur.execute("""CREATE TABLE IF NOT EXISTS configs (guild BIGINT PRIMARY KEY, currency BOOL NOT NULL DEFAULT True)""")

# initial tag from b1nZ for tags

cur.execute("""INSERT INTO tags (hash, tag, guild, content, author) VALUES 
            ('1ca25c85001011127a3db6712b5e425b4ad4672c9754535b81e72f99c784112e',
            'hello world',
            295341979800436736,
            'hello, im ghost of b1nzy who wrote this tag',
            80351110224678912""")

# initial config for memework
cur.execute("""INSERT INTO configs (guild, currency) VALUES (295341979800436736, True)""")

print("Done!")
