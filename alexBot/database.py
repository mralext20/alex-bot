import datetime
import os
import uuid

import discord

# from alexBot.classes import
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Interval, String, select
from sqlalchemy.dialects.postgresql import BIGINT, UUID
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column, relationship

from alexBot.classes import SugeryZone, Thresholds
from alexBot.tools import time_cache


class Base(
    MappedAsDataclass,
    DeclarativeBase,
):
    pass


from typing import Optional, Union


class VoiceStat(Base):
    __tablename__ = "voiceStats"
    id: Mapped[int] = mapped_column(BIGINT(), primary_key=True)
    longest_session: Mapped[datetime.timedelta] = mapped_column(Interval(), default=datetime.timedelta(seconds=0))
    currently_running: Mapped[bool] = mapped_column(Boolean(), default=False)
    average_duration: Mapped[datetime.timedelta] = mapped_column(Interval(), default=datetime.timedelta(seconds=1))
    total_sessions: Mapped[int] = mapped_column(Integer(), default=0)
    recently_ended: Mapped[bool] = mapped_column(Boolean(), default=False)
    last_started: Mapped[datetime.datetime] = mapped_column(DateTime(), default=datetime.datetime.now)


class Reminder(Base):
    """a reminder. can be recurring (set frequency) or one time (no frequency) target is the id of the channel that the reminder is sent in."""

    __tablename__ = "reminders"
    target: Mapped[int] = mapped_column(BIGINT(), nullable=False)
    owner: Mapped[int] = mapped_column(BIGINT(), nullable=False)
    guildId: Mapped[Optional[int]] = mapped_column(BIGINT(), nullable=True)
    message: Mapped[str] = mapped_column(String(), nullable=False)
    next_remind: Mapped[datetime.datetime] = mapped_column(DateTime(), nullable=False)
    frequency: Mapped[Optional[datetime.timedelta]] = mapped_column(Interval(), nullable=True)
    require_clearing: Mapped[bool] = mapped_column(Boolean(), default=False)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default_factory=uuid.uuid4)

    @time_cache(300)
    def user_can_manage_reminder(self, user: Union[discord.Member, discord.User]):
        if self.owner == user.id:
            return True
        if isinstance(user, discord.Member) and user.guild.id == self.guildId:
            return user.guild_permissions.manage_guild
        return False


class GuildConfig(Base):
    __tablename__ = "guildconfigs"
    __config_keys__ = [
        "ayy",
        "tikTok",
        "veryCool",
        "collectVoiceData",
        "firstAmendment",
        "privateOnePersonVCs",
        "transcribeVoiceMessages",
        "minecraft",
    ]
    guildId: Mapped[int] = mapped_column(BIGINT(), primary_key=True)
    ayy: Mapped[bool] = mapped_column(Boolean(), default=False)
    tikTok: Mapped[bool] = mapped_column(Boolean(), default=False)
    veryCool: Mapped[bool] = mapped_column(Boolean(), default=False)
    collectVoiceData: Mapped[bool] = mapped_column(Boolean(), default=True)
    firstAmendment: Mapped[bool] = mapped_column(Boolean(), default=False)
    privateOnePersonVCs: Mapped[bool] = mapped_column(Boolean(), default=False)
    transcribeVoiceMessages: Mapped[bool] = mapped_column(Boolean(), default=False)
    minecraft: Mapped[str] = mapped_column(String(), default="")


class UserConfig(Base):
    __tablename__ = "userconfigs"
    __config_keys__ = ["ringable", "collectVoiceData"]
    userId: Mapped[int] = mapped_column(BIGINT(), primary_key=True)
    ringable: Mapped[bool] = mapped_column(Boolean(), default=True)
    collectVoiceData: Mapped[bool] = mapped_column(Boolean(), default=True)


class VoiceName(Base):
    __tablename__ = "voicenames"
    userId: Mapped[int] = mapped_column(BIGINT(), primary_key=True)
    channelId: Mapped[int] = mapped_column(BIGINT(), primary_key=True)
    name: Mapped[str] = mapped_column(String())


class SugeryZoneNames(Base):
    __tablename__ = "sugeryzonenames"
    VERYLOW: Mapped[str] = mapped_column(String())
    LOW: Mapped[str] = mapped_column(String())
    NORMAL: Mapped[str] = mapped_column(String())
    HIGH: Mapped[str] = mapped_column(String())
    VERYHIGH: Mapped[str] = mapped_column(String())
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default_factory=uuid.uuid4)


class SugeryUser(Base):
    __tablename__ = "sugeryusers"
    guildId: Mapped[int] = mapped_column(BIGINT(), primary_key=True)
    userId: Mapped[int] = mapped_column(BIGINT(), primary_key=True)
    baseURL: Mapped[str]
    namesId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(SugeryZoneNames.id))
    names: Mapped[SugeryZoneNames] = relationship(SugeryZoneNames, foreign_keys=[namesId])
    constantAlerts: Mapped[Optional[int]] = mapped_column(BIGINT())
    alertsTranslationsId: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey(SugeryZoneNames.id)
    )
    alertsTranslations: Mapped[Optional[SugeryZoneNames]] = relationship(
        SugeryZoneNames, foreign_keys=[alertsTranslationsId]
    )
    lastGroup: Mapped[SugeryZone] = mapped_column(Integer(), default=SugeryZone.NORMAL.value)

    thresholds: Optional[Thresholds] = None


user = os.environ.get("POSTGRES_USER")
pw = os.environ.get("POSTGRES_PASSWORD")
db = os.environ.get("POSTGRES_DB")
db_host = os.environ.get("POSTGRES_HOST")
db_port = os.environ.get("POSTGRES_PORT")
database_url = os.environ.get("DATABASE_URL") or f"postgresql+asyncpg://{user}:{pw}@{db_host}:{db_port}/{db}"
if database_url and database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif os.environ.get("DATABASE_URL") is None:
    if None in (user, pw, db, db_host, db_port):
        raise ValueError("Missing database environment variable")

engine = create_async_engine(database_url)
async_session = async_sessionmaker(
    engine,
    expire_on_commit=False,
)
