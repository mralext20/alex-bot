from random import choice

token = ""

mongo = "mongodb://localhost"

MONEY = {'CHANCE': .05, 'PER_MESSAGE': choice(range(0, 100)) / 100, "REACTION": "\n{MONEY-MOUTH FACE}"}
