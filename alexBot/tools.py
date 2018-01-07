import aiohttp
import logging
import decimal
import json


from discord.ext import commands

log = logging.getLogger(__name__)

configKeys = {
    "money": False,
    "ayy": False,
    "hide_coins": False
}

ZERO = decimal.Decimal(0)
INF = decimal.Decimal('inf')


class Cog:
    """ The Cog base class that all cogs should inherit from. """

    def __init__(self, bot):
        self.bot = bot


class BoolConverter(commands.Converter):
    async def convert(self,  ctx, argument):
        if argument[0].lower() == "f":
            return False
        elif argument[0].lower() == "t":
            return True
        else:
            raise commands.BadArgument(f'can not convert {argument} to True or False')


class TransactionError(commands.UserInputError):
    """raised when there is a transaction error."""
    pass


class BotError(commands.errors.BadArgument):
    """NO BOTS ALLOWED."""
    pass


class CoinConverter(commands.Converter):
    async def convert(self, ctx, argument) -> decimal.Decimal:
        ba = commands.BadArgument
        value = decimal.Decimal(argument)
        if value <= ZERO:
            raise ba("You can't input values lower or equal to 0.")
        elif value >= INF:
            raise ba("You can't input values lower of equal to infinity.")

        value = round(value, 2)

        return value


async def get_text(session: aiohttp.ClientSession, url) -> str:
    log.debug(f"fetched url: {url}")
    async with session.get(url) as content:
        return await content.text()


async def get_json(session: aiohttp.ClientSession, url) -> dict:
    log.debug(f"fetched json: {url}")
    async with session.get(url) as content:
        return await content.json()


async def haste(session: aiohttp.ClientSession, text: str, extension: str = "py") -> str:
    """ Pastes something to Hastebin, and returns the link to it. """
    async with session.post('https://hastebin.com/documents', data=text) as resp:
        resp_json = await resp.json()
        ret = f"https://hastebin.com/{resp_json['key']}.{extension}"
        log.info(f"hasted, return was {ret}")
        return ret


async def create_guild_config(bot, guild_id: int) -> dict:
    log.info(f'creating a guild config for {guild_id}')
    cfg = json.dumps(configKeys)
    await bot.pool.execute("""INSERT INTO configs (id, data, type) VALUES ($1, $2, 'guild')""", guild_id, cfg)
    return configKeys


async def get_guild_config(bot, guild_id: int) -> dict:
    ret = {}
    try:
        ret = bot.configs[guild_id]

    except KeyError:
        ret = await bot.pool.fetchrow("""SELECT data FROM configs WHERE id=$1 AND type='guild'""", guild_id)
        if ret is None:
            ret = await create_guild_config(bot, guild_id)
        else:
            ret = json.loads(ret['data'])
    finally:
        ret = {**configKeys, **ret}
        bot.configs[guild_id] = ret
    return ret


async def update_guild_key(bot, guild_id: int, key: str, value):
    """updates the `key` to be `value`.
    note: this method is extremely dumb,
    as it does no error checking to ensure that you are giving it the right value for a key."""
    bot.configs[guild_id][key] = value
    cfg = json.dumps(bot.configs[guild_id])
    await bot.pool.execute("""UPDATE configs SET data=$1 WHERE id=$2""", cfg, guild_id)


async def get_wallet(bot, user_id: int) -> float:
    log.info(f'getting wallet for user: {user_id}')
    target = bot.get_user(user_id)
    if target.bot:
        raise BotError
    ret = 0
    try:
        ret = bot.wallets[user_id]
    except KeyError:
        ret = await bot.pool.fetchrow("""SELECT amount FROM bank WHERE owner=$1""", user_id)
        if ret is None:
            ret = 0
            await bot.pool.execute("""INSERT INTO bank (owner, amount) VALUES ($1, $2)""", user_id, ret)
        else:
            ret = ret['amount']
    finally:
        bot.wallets[user_id] = ret
    return float(ret)


async def update_wallet(bot, user_id: int, amount):
    """changes a wallet directly."""
    bot.wallets[user_id] = amount
    try:
        ret = await bot.pool.execute("""UPDATE bank SET amount=$1 WHERE owner=$2""", amount, user_id)
        assert ret == "UPDATE 1"
    except AssertionError:
        await bot.pool.execute("""INSERT INTO bank (owner, amount) VALUES ($1, $2)""", user_id, amount)
