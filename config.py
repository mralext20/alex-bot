# config file. copy to `config.py` and fill in your details.

import os
import json

if os.path.exists('SERVICE_ACCOUNT.JSON'):
    google_service_account = json.load(open('SERVICE_ACCOUNT.JSON'))
else:
    google_service_account = None

mqttServer = os.environ.get('MQTT_SERVER')
token = os.environ.get('BOT_TOKEN')

cat_token = os.environ.get('THECATAPI_KEY')

prefix = os.environ.get('PREFIX') or 'alex!'

ha_webhook_notifs = os.environ.get('HA_WEBHOOK_NOTIFS')


discord_token = os.environ.get('DISCORD_TOKEN')
if not discord_token:
    raise ValueError('DISCORD_TOKEN not set')
