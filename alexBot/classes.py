import datetime
import posixpath
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlparse


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
class ReactionRoleConfig:
    channel: int
    role: int
    reaction: str


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

    def __init__(self, data: dict) -> None:
        self.idx = data['id']
        self.username = data['username']
        if data.get('profile'):
            if data['profile'].get('iconUrl'):
                url = urlparse(data['profile']['iconUrl'])
                self.icon = f"https://cloudxstorage.blob.core.windows.net/assets{posixpath.splitext(url.path)[0]}"


@dataclass
class GuildConfig:
    ayy: bool = False
    tikTok: bool = False
    veryCool: bool = False
    collectVoiceData: bool = True
    firstAmendment: bool = False
    reactionRoles: List[ReactionRoleConfig] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data) -> "GuildConfig":
        return cls(**data, reactionRoles=[ReactionRoleConfig(**[d for d in data["reactionRoles"]])])


@dataclass
class GuildData:
    voiceStat: VoiceStat = field(default_factory=VoiceStat)
    config: GuildConfig = field(default_factory=GuildConfig)

    @classmethod
    def from_dict(cls, data) -> "GuildData":
        return cls(
            voiceStat=VoiceStat(**data["voiceStat"]),
            config=GuildConfig(**data["config"]),
        )


@dataclass
class UserConfig:
    ringable: bool = True

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class UserData:
    config: UserConfig = field(default_factory=UserConfig)

    @classmethod
    def from_dict(cls, data):
        return cls(config=UserConfig.from_dict(data["config"]))
