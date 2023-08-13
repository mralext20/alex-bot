FROM gorialis/discord.py:pypi-minimal

WORKDIR /alexbot

COPY requirements.txt /alexbot/requirements.txt
RUN pip install -U -r requirements.txt


COPY . /alexbot
RUN rm /alexbot/.env
CMD ["bash", "entry_point.sh"]
