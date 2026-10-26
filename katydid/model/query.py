from enum import Enum
from dataclasses import field, dataclass

class TagMode(Enum):
    ALL = "all"
    ANY = "any"

class EntrySort(Enum):
    RECENT = "recent"
    LENGTH = "length"
    TITLE = "title"

@dataclass
class EntryQuery:
    keywords: str = ""
    tag_ids: set[str] = field(default_factory=set)
    mode: TagMode = TagMode.ALL
    sort: EntrySort = EntrySort.RECENT
    flip: bool = False

@dataclass
class CollectionQuery:
    keywords: str = ""
    tag_ids: set[str] = field(default_factory=set)
    mode: TagMode = TagMode.ALL