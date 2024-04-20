FROM gorialis/discord.py:3.11-pypi-minimal

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
RUN rm /alexbot/.env; echo
CMD ["bash", "entry_point.sh"]
