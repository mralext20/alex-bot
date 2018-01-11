from random import uniform

token = ""

dsn = 'dbname="alexbot" user="postgres" password="password"'

money = {
    'enabled': False,
    'CHANCE': .20,
    'PER_MESSAGE': uniform(1, 3),
    'REACTION': "\N{MONEY-MOUTH FACE}"
}

logging = {
    'info': 'webhook url here',
    'warning': 'webhook here too',
    'error': 'webhook url here three',

}
#  bots who's owner gets a dm whenever they go offline
monitored_bots = {
    288369203046645761: 69198249432449024,  # Mousey, FrostLuma
}
