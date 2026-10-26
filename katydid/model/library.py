from katydid.model.tag import Tag
from katydid.model.collection import Collection

from katydid.model.query import CollectionQuery
from katydid.model.query import TagMode

from katydid.model.errors import DuplicateContentError

class Library:
    def __init__(self, default_entry_tags=None, collection_tags=None):
        if default_entry_tags is not None:
            self._default_entry_tags = {tag.id: tag for tag in default_entry_tags}
        else:
            self._default_entry_tags = {}

        if collection_tags is not None:
            self._collection_tags = {tag.id: tag for tag in collection_tags}
        else:
            self._collection_tags = {}

        self._collections = {}

    @property
    def collections(self):
        return self._collections.copy()

    @property
    def default_entry_tags(self):
        return self._default_entry_tags.copy()

    @property
    def collection_tags(self):
        return self._collection_tags.copy()

    def get_collection(self, collection_id) -> Collection:
        if collection_id in self._collections:
            return self._collections[collection_id]
        else:
            raise KeyError(f"Queried Collection with ID {collection_id} does not exist")

    def _title_taken(self, title, ignore_id=None):
        requested = title.strip().casefold()
        return any(
            collection.title.strip().casefold() == requested
            for collection in self._collections.values()
            if collection.id != ignore_id
        )

    def _name_taken(self, name, ignore_id=None):
        requested = name.strip().casefold()
        return any(
            tag.name.strip().casefold() == requested
            for tag in self._collection_tags.values()
            if tag.id != ignore_id
        )

    def create_collection(self, title, description, char_limit=None) -> Collection:
        if self._title_taken(title):
            raise DuplicateContentError("Duplicate collection name")
        collection = Collection(title, description, self._default_entry_tags, char_limit=char_limit)

        self._collections[collection.id] = collection
        return collection

    def load_collection(self, title, description, id, char_limit, entries, custom_tags, tag_ids) -> Collection:
        collection = Collection(title, description, self._default_entry_tags, id=id, char_limit=char_limit, 
                                entries=entries, custom_tags=custom_tags, tag_ids=tag_ids)
        self._collections[collection.id] = collection
        return collection

    def rename_collection(self, collection_id, new_title):
        if collection_id not in self._collections:
            raise KeyError("No such collection available to rename")
        if self._title_taken(new_title, ignore_id=collection_id):
            raise DuplicateContentError(f"A Collection named {new_title} already exists")
        self._collections[collection_id].title = new_title
        

    def change_collection_description(self, collection_id, new_desc):
        if collection_id not in self._collections:
            raise KeyError("No such collection available to alter")
        self._collections[collection_id].description = new_desc

    def delete_collection(self, collection_id):
        if collection_id in self._collections:
            return self._collections.pop(collection_id)
        else:
            raise KeyError(f"Queried Collection with ID {collection_id} does not exist")

    def add_collection_tag(self, name, color) -> Tag:
        if self._name_taken(name):
            raise DuplicateContentError(f"A tag named '{name}' already exists.")
        new_tag = Tag(name, color)
        self._collection_tags[new_tag.id] = new_tag
        return new_tag

    def delete_collection_tag(self, tag_id):
        if tag_id not in self._collection_tags:
            raise KeyError(f"Cannot delete Tag with ID {tag_id} because it does not exist")
        modified_collections = []
        for collection in self._collections.values():
            if tag_id in collection.tag_ids:
                modified_collections.append(collection)
                collection.tag_ids.remove(tag_id)
        self._collection_tags.pop(tag_id)
        return modified_collections

    def rename_collection_tag(self, tag_id, new_name):
        if tag_id not in self._collection_tags:
            raise KeyError("No such tag available to alter")
        if self._name_taken(new_name, ignore_id=tag_id):
            raise DuplicateContentError(f"A tag named '{new_name}' already exists.")
        self._collection_tags[tag_id].name = new_name

    def query_collections(self, q: CollectionQuery):
        results = list(self._collections.values())
        if q.keywords:
            kept = []
            search_words = q.keywords.casefold().split()
            for collection in results:
                collection_text = (collection.title + " " + collection.description).casefold()
                if all(word in collection_text for word in search_words):
                    kept.append(collection)
            results = kept

        if q.tag_ids:
            kept = []
            if q.mode == TagMode.ALL:
                for collection in results:
                    if q.tag_ids.issubset(collection.tag_ids):
                        kept.append(collection)
            elif q.mode == TagMode.ANY:
                for collection in results:
                    if not q.tag_ids.isdisjoint(collection.tag_ids):
                        kept.append(collection)
            results = kept
        return results

    # guardrail for when the UI layer needs to assign collection tags
    def set_collection_tags(self, collection_id, tag_ids):
        if collection_id not in self._collections:
            raise KeyError(f"Collection with ID {collection_id} does not exist")
        unknown = [tag_id for tag_id in tag_ids if tag_id not in self._collection_tags]
        if unknown:
            raise KeyError(f"Did not recognize tag IDs: {unknown}")
        self._collections[collection_id].tag_ids = tag_ids