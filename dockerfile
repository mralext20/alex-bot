FROM gorialis/discord.py:pypi-minimal

WORKDIR /alexbot

COPY requirements.txt /alexbot/requirements.txt
RUN pip install -U -r /alexbot/requirements.txt


COPY . /alexbot
RUN rm /alexbot/.env; echo
CMD ["bash", "entry_point.sh"]
