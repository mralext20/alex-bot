FROM gorialis/discord.py:rewrite

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "bot.py"]