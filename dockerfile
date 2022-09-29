FROM gorialis/discord.py:pypi-minimal

WORKDIR /alexbot
COPY . /alexbot

RUN pip install -U -r requirements.txt

CMD ["python", "bot.py"]
