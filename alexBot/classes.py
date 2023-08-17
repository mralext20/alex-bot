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


SugeryTranslations = {
    SugeryZone.VERYLOW: "Sehr Niedrig",
    SugeryZone.LOW: "Niedrig",
    SugeryZone.NORMAL: "Normal",
    SugeryZone.HIGH: "Hoch",
    SugeryZone.VERYHIGH: "Sehr Hoch",
}
