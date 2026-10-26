import uuid

from katydid.model.entry import Entry
from katydid.model.tag import Tag

from katydid.model.errors import DuplicateContentError
from katydid.model.errors import TagInUseError
from katydid.model.errors import DefaultTagError
from katydid.model.errors import EntryValidationError
from katydid.model.errors import CharLimitConflictError

from katydid.model.query import *

class Collection:
    def __init__(self, title, description, default_tags, id=None, char_limit=None, 
                 entries=None, custom_tags=None, tag_ids=None):
        self.title = title
        self.description = description
        self._default_tags = default_tags

        self._id = id if id is not None else uuid.uuid4().hex

        # bypasses setter intentionally because entries is referenced in the setter for limit change rules
        # loads are also not blocked by char_limit rules with this logic
        self._check_limit_value(char_limit)
        self._char_limit = char_limit

        self.tag_ids = tag_ids if tag_ids is not None else set()

        # entries and various tags should load what is passed if they exist, or create a new dict if they don't
        if entries is not None:
            self._entries = {entry.id: entry for entry in entries}
        else:
            self._entries = {}
        
        if custom_tags is not None:
            self._custom_tags = {tag.id: tag for tag in custom_tags}
        else:
            self._custom_tags = {}

    def _name_taken(self, tag_name, ignore_id=None):
        input = tag_name.strip().casefold()
        return any(
            tag.name.strip().casefold() == input
            for tag in self.available_tags().values()
            if tag.id != ignore_id
        )

    @property
    def id(self):
        return self._id

    @property
    def title(self):
        return self._title

    # title character limit 50
    @title.setter
    def title(self, new_title):
        if not isinstance(new_title, str):
            raise TypeError("Title data type invalid.")
        if len(new_title) > 50:
            raise ValueError("Collection title is too long.")
        self._title = new_title

    @property
    def description(self):
        return self._description

    # description character limit 500
    @description.setter
    def description(self, new_desc):
        if not isinstance(new_desc, str):
            raise TypeError("Description data type invalid.")
        if len(new_desc) > 500:
            raise ValueError("Collection description is too long.")
        self._description = new_desc

    @property
    def char_limit(self):
        return self._char_limit

    # helper method for checking character limit
    # prevents initial character limit construction from trying to check a non-existent entries dict
    # char limit setter restrictions:
        # only non-boolean integers greater than or equal to 1 are allowed
        # None is also accepted and is interpreted in other code as an unlimited max character count
    @staticmethod
    def _check_limit_value(limit):
        if limit is None:
            return
        if not isinstance(limit, int) or isinstance(limit, bool):
            raise TypeError("Requested limit not an integer")
        elif limit < 1:
            raise ValueError("Limit cannot be lower than 1")

    # ensures character limit changes do not fall below the size of any existing entries
    @char_limit.setter
    def char_limit(self, limit):
        self._check_limit_value(limit)
        if limit is None:
            self._char_limit = None
            return
        conflicts = [entry for entry in self._entries.values() if entry.length() > limit]
        if conflicts:
            raise CharLimitConflictError(conflicts)
        self._char_limit = limit

    # entries and tags return copies of themselves so that they are not mutable in other classes
    # their contents remain mutable through the shallow copy, though
    @property
    def entries(self):
        return self._entries.copy()

    @property
    def custom_tags(self):
        return self._custom_tags.copy()

    @property
    def tag_ids(self):
        return self._tag_ids

    @tag_ids.setter
    def tag_ids(self, tags):
        self._tag_ids = set(tags)

    # concatenates dicts of default and custom tags
    def available_tags(self):
        return {**self._default_tags, **self._custom_tags}

    def add_tag(self, tag_name, tag_color):
        if self._name_taken(tag_name):
            raise DuplicateContentError(f"A tag named '{tag_name}' already exists.")
        new_tag = Tag(tag_name, tag_color)
        self._custom_tags[new_tag.id] = new_tag
        return new_tag

    def add_entry(self, entry):
        if entry.id in self._entries:
            raise KeyError("Entry already exists")
        problems = self.validate_entry(entry)
        if problems:
            raise EntryValidationError(problems)
        self._entries[entry.id] = entry

    def update_entry(self, entry):
        if entry.id not in self._entries:
            raise KeyError("Unable to locate entry")
        problems = self.validate_entry(entry)
        if problems:
            raise EntryValidationError(problems)
        self._entries[entry.id] = entry
        entry.touch() # touching the entry here ensures that the entry is timestamped when updated

    def query(self, q: EntryQuery):
        results = list(self._entries.values())
        if q.keywords:
            kept = []
            search_words = q.keywords.casefold().split()
            for entry in results:
                entry_text = (entry.title + " " + entry.body).casefold()
                if all(word in entry_text for word in search_words):
                    kept.append(entry)
            results = kept

        if q.tag_ids:
            kept = []
            if q.mode == TagMode.ALL:
                for entry in results:
                    if q.tag_ids.issubset(entry.tag_ids):
                        kept.append(entry)
            elif q.mode == TagMode.ANY:
                for entry in results:
                    if not q.tag_ids.isdisjoint(entry.tag_ids):
                        kept.append(entry)
            results = kept

        match q.sort:
            case EntrySort.RECENT:
                results.sort(key=lambda entry: entry.modified, reverse=not q.flip)
            case EntrySort.LENGTH:
                results.sort(key=lambda entry: entry.length(), reverse=not q.flip)
            case EntrySort.TITLE:
                results.sort(key=lambda entry: entry.title.casefold(), reverse=q.flip)
        return results


    # checks to see if any entries whose only tag's deletion has been requested
    # if it has, it returns a list of those entries, otherwise it returns an empty list
    def blocking_entries(self, tag_id):
        blocked_list = []
        for entry in self._entries.values():
            if entry.tag_ids == {tag_id}:
                blocked_list.append(entry)
        return blocked_list

    # returns the popped entry for the sake of future undo implementation
    def remove_entry(self, entry_id):
        if entry_id in self._entries:
            return self._entries.pop(entry_id)
        else:
            raise KeyError(f"Queried Entry with ID {entry_id} does not exist")

    # delete a tag. A tag cannot be deleted if:
    # 1. it is a default tag
    # 2. the tag does not exist
    # 3. the tag is the sole tag on an Entry in the Collection
    # Returns a list of modified entries for later use
    def delete_tag(self, tag_id):
        if tag_id not in self.available_tags():
            raise KeyError(f"Cannot delete Tag with ID {tag_id} because it does not exist")
        elif tag_id in self._default_tags:
            raise DefaultTagError("Cannot delete default tags")
        entries_in_use = self.blocking_entries(tag_id)
        if entries_in_use:
            raise TagInUseError(entries_in_use)
        modified_entries = []
        for entry in self._entries.values():
            if tag_id in entry.tag_ids:
                modified_entries.append(entry)
                entry.tag_ids.remove(tag_id)
        self._custom_tags.pop(tag_id)
        return modified_entries

    def rename_tag(self, tag_id, new_name):
        if tag_id not in self.available_tags():
            raise KeyError("No such tag is available to rename")
        if tag_id in self._default_tags:
            raise DefaultTagError("Cannot rename default tag")
        if self._name_taken(new_name, ignore_id=tag_id):
            raise DuplicateContentError(f"A Tag named {new_name} already exists")
        self._custom_tags[tag_id].name = new_name

    def get_entry(self, entry_id):
        if entry_id in self._entries:
            return self._entries[entry_id]
        else:
            raise KeyError(f"Queried Entry with ID {entry_id} does not exist")

    def _title_taken(self, title, ignore_id=None):
        requested = title.strip().casefold()
        return any(
            entry.title.strip().casefold() == requested
            for entry in self._entries.values()
            if entry.id != ignore_id
        )

    def validate_entry(self, entry: Entry) -> list[str]:
        problems = []
        if not entry.is_valid(self._char_limit):
            problems.append(f"Entry length of {entry.length()} exceeds character limit of {self._char_limit}.")
        if not entry.tag_ids:
            problems.append("An Entry must have at least one Tag.")
        all_tags = self.available_tags()
        for tag_id in entry.tag_ids:
            if tag_id not in all_tags:
                problems.append(f"This entry uses a tag that doesn't exist or no longer exists.")
        if self._title_taken(entry.title, ignore_id=entry.id):
            problems.append(f"An Entry titled {entry.title} already exists.")
        return problems