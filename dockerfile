FROM python:3.12

WORKDIR /alexbot


COPY requirements.txt /alexbot/requirements.txt


# only install until the #SMALLER comment
RUN sed -i '/#SMALLER/,$d' /alexbot/requirements.txt

RUN pip install -U -r /alexbot/requirements.txt  --no-cache-dir

COPY requirements.txt /alexbot/requirements.txt

# only install after the #SMALLER comment
RUN sed -i '/#SMALLER/,$!d' /alexbot/requirements.txt
RUN pip install -U -r /alexbot/requirements.txt  --no-cache-dir



COPY . /alexbot
# always install newest discord.py
RUN pip install -U 'discord.py[voice] @ git+https://github.com/rapptz/discord.py' --no-cache-dir

RUN rm /alexbot/.env; echo
CMD ["bash", "entry_point.sh"]
