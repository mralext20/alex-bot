import enum
from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, List, Optional, Union

import discord
import feedparser


@dataclass
class RingRate:
    times: int = 1
    rate: float = 1


@dataclass
class FeedConfig:
    tagId: Optional[int]
    feedUrl: str


@dataclass
class MovieSuggestion:
    title: str
    watched: bool
    suggestor: int
    watchdate: str


class SugeryZone(enum.Enum):
    VERYLOW = enum.auto()
    LOW = enum.auto()
    NORMAL = enum.auto()
    HIGH = enum.auto()
    VERYHIGH = enum.auto()


googleVoices = [
    ('en-US-Wavenet-A', 'Male'),
    ('en-US-Wavenet-B', 'Male'),
    ('en-US-Wavenet-C', 'Female'),
    ('en-US-Wavenet-D', 'Male'),
    ('en-US-Wavenet-E', 'Female'),
    ('en-US-Wavenet-F', 'Female'),
    ('en-US-Wavenet-G', 'Female'),
    ('en-US-Wavenet-H', 'Female'),
    ('en-US-Wavenet-I', 'Male'),
    ('en-US-Wavenet-J', 'Male'),
]


SugeryTranslations = {
    SugeryZone.VERYLOW: "Sehr Niedrig",
    SugeryZone.LOW: "Niedrig",
    SugeryZone.NORMAL: "Normal",
    SugeryZone.HIGH: "Hoch",
    SugeryZone.VERYHIGH: "Sehr Hoch",
}
