from random import choice

token = ""

dsn = 'dbname="alexbot" user="postgres" password="password"'

MONEY = {'CHANCE': .05, 'PER_MESSAGE': choice(range(0, 100)) / 100, "REACTION": "\n{MONEY-MOUTH FACE}"}

logging = {
    'info': 'webhook url here',
    'warning': 'webhook here too',
    'error': 'webhook url here three',
}
