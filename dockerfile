FROM gorialis/discord.py:pypi-minimal

WORKDIR /alexbot

COPY requirements.txt /alexbot/requirements.txt
RUN pip install -U -r requirements.txt


COPY . /alexbot
CMD ["python", "bot.py"]
