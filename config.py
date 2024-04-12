from dotenv import load_dotenv

load_dotenv()

import base64
import json
import os

if os.environ.get("GOOGLE_SERVICE_ACCOUNT"):
    # get data, it's b64 encoded
    google_service_account = json.loads(base64.b64decode(os.environ.get("GOOGLE_SERVICE_ACCOUNT").encode("ascii")))
else:
    google_service_account = None

mqtt_url = os.environ.get('MQTT_URL')

ha_webhook_notifs = os.environ.get('HA_WEBHOOK_NOTIFS')

discord_token = os.environ.get('DISCORD_TOKEN')

cat_token = os.environ.get('THECATAPI_KEY')

prefix = os.environ.get('BOT_PREFIX')


# setthe DATABASE_URL env var
db_full_url = os.environ.get("DATABASE_URL")

# OR set all of these:
db_user = os.environ.get("POSTGRES_USER")
db_pw = os.environ.get("POSTGRES_PASSWORD")
db_name = os.environ.get("POSTGRES_DB")
db_host = os.environ.get("POSTGRES_HOST")
db_port = os.environ.get("POSTGRES_PORT")
