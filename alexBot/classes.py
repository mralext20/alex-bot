import datetime
import enum
from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, List, Optional, Union

import discord
import feedparser

from .tools import transform_neosdb


@dataclass
class RingRate:
    times: int = 1
    rate: float = 1


@dataclass
class VoiceStat:
    longest_session_raw: float = 0
    last_started_raw: float = datetime.datetime.now().timestamp()
    currently_running: bool = False
    average_duration_raw: float = 1
    total_sessions: int = 0
    recently_ended: bool = False

    @property
    def longest_session(self) -> datetime.timedelta:
        """
        the length of the longest Session, as returned as a `Datetime.timespan`
        """
        return datetime.timedelta(seconds=int(self.longest_session_raw))

    @longest_session.setter
    def longest_session(self, value: datetime.timedelta):
        self.longest_session_raw = value.total_seconds()

    @property
    def average_duration(self) -> datetime.timedelta:
        return datetime.timedelta(seconds=int(self.average_duration_raw))

    @property
    def last_started(self) -> datetime.datetime:
        """
        the start time of the current session. only valid if self.currentlyRunning == true
        """
        return datetime.datetime.fromtimestamp(self.last_started_raw)

    @last_started.setter
    def last_started(self, value: datetime.datetime):
        self.last_started_raw = int(value.timestamp())


@dataclass
class RecurringReminder:
    target: int  # the messegable to remind to (user or channel)
    message: str  # the message to send
    UTC_minute: int  # the minute of the day in UTC to remind at
    require_clearing: bool = False  # if the reminder requires interaction to clear


@dataclass
class ReactionRoleConfig:
    message: int
    role: int
    reaction: str


@dataclass
class FeedConfig:
    tagId: Optional[int]
    feedUrl: str


@dataclass
class NeosTZGroup:
    name: str
    tags: Dict[str, List[str]]
    default_icon: str
    users: Dict[str, str]

    def __init__(self, data) -> None:
        self.name = data['name']
        self.tags = data['tags']
        self.default_icon = data['default_icon']
        self.users = data['users']


@dataclass
class NeosTZData:
    zones: Dict[str, str]
    groups: List[NeosTZGroup]

    def __init__(self, data) -> None:
        self.zones = data['zones']
        self.groups = [NeosTZGroup(each) for each in data['groups']]


@dataclass
class NeosUser:
    idx: str
    username: str
    icon: Optional[str] = None

    def __eq__(self, o: "NeosUser") -> bool:
        return self.idx == o.idx

    def __hash__(self) -> int:
        return hash(self.idx)

    def __init__(self, data: dict) -> None:
        self.idx = data['id']
        self.username = data['username']
        if data.get('profile'):
            if data['profile'].get('iconUrl'):
                self.icon = transform_neosdb(data['profile']['iconUrl'])


@dataclass
class GuildConfig:
    ayy: bool = False
    tikTok: bool = False
    veryCool: bool = False
    collectVoiceData: bool = True
    firstAmendment: bool = False
    minecraft: str = ""

    @classmethod
    def from_dict(cls, data) -> "GuildConfig":
        new_data = {elm: val for (elm, val) in data.items() if elm != "reactionRoles"}
        return cls(**new_data)


@dataclass
class GuildData:
    voiceStat: VoiceStat = field(default_factory=VoiceStat)
    config: GuildConfig = field(default_factory=GuildConfig)

    @classmethod
    def from_dict(cls, data) -> "GuildData":
        return cls(
            voiceStat=VoiceStat(**data["voiceStat"]),
            config=GuildConfig.from_dict(data["config"]),
        )


@dataclass
class UserConfig:
    ringable: bool = True

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class MovieSuggestion:
    title: str
    watched: bool
    suggestor: int
    watchdate: str


class ButtonType(int, enum.Enum):
    LOCATION = 1
    GAME = 2
    PHONE = 3
    INTEREST = 4
    PRONOUN = 5


@dataclass
class ButtonRole:
    label: str
    role: int
    message: int
    type: ButtonType
    emoji: Optional[str] = None


@dataclass
class UserData:
    config: UserConfig = field(default_factory=UserConfig)
    voiceStat: VoiceStat = field(default_factory=VoiceStat)

    @classmethod
    def from_dict(cls, data):
        return cls(
            config=UserConfig.from_dict(data["config"]),
            voiceStat=(VoiceStat(**data["voiceStat"]) if data.get("voiceStat") else VoiceStat()),
        )


@dataclass
class Thresholds:
    veryHigh: int
    high: int
    low: int
    veryLow: int


class SugeryZone(enum.Enum):
    VERYLOW = enum.auto()
    LOW = enum.auto()
    NORMAL = enum.auto()
    HIGH = enum.auto()
    VERYHIGH = enum.auto()


SugeryTranslations = {
    SugeryZone.VERYLOW: "Sehr Niedrig",
    SugeryZone.LOW: "Niedrig",
    SugeryZone.NORMAL: "Normal",
    SugeryZone.HIGH: "Hoch",
    SugeryZone.VERYHIGH: "Sehr Hoch",
}


@dataclass
class SugeryUser:
    guild: int
    user: int
    baseURL: str
    names: Dict[SugeryZone, str] = field(default_factory=dict)
    thresholds: Thresholds = None
    lastGroup: SugeryZone = None
    constantAlerts: int = None
