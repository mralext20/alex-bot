from random import choice

token = ""

dsn = 'dbname="alexbot" user="postgres" password="password"'

money = {'CHANCE': .20, #chance a message will get a money
         'PER_MESSAGE': choice(range(100, 300)) / 100, # amount of money a message gets
         "REACTION": "\N{MONEY-MOUTH FACE}", # the reaction that bot will use to say 'you got money!'
}

logging = {
    'info': 'webhook url here',
    'warning': 'webhook here too',
    'error': 'webhook url here three',
}
