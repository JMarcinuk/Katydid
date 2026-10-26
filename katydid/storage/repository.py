from pathlib import Path
import json
from datetime import datetime
import time

from abc import ABC, abstractmethod

from katydid.model.library import Library
from katydid.model.collection import Collection
from katydid.model.tag import Tag
from katydid.model.entry import Entry

FORMAT_VERSION = 1

class Repository(ABC):
    @abstractmethod
    def load_library(self) -> Library:
        """loads the library from the filesystem, creates the Library object and returns it"""
        pass

    @abstractmethod
    def save_library(self, library: Library):
        """Writes changes to a Library object to the filesystem"""
        pass

    @abstractmethod
    def save_collection(self, collection: Collection):
        """Writes changes to a collection object to the filesystem"""
        pass

    @abstractmethod
    def delete_collection(self, collection_id: str):
        """removes a collection from the filesystem"""
        pass

    @abstractmethod
    def save_entry(self, collection: Collection, entry: Entry):
        """writes an entry to a specific collection and saves changes to the filesystem"""
        pass

    @abstractmethod
    def delete_entry(self, collection: Collection, entry_id: str):
        """removes an entry from a collection and saves changes to filesystem"""
        pass

class MarkdownFolderRepository(Repository):
    def __init__(self, root_path: Path):
        self._root_path = root_path

    def _read_entry(self, file: Path) -> Entry:
        raw_file = file.read_text(encoding="utf-8")
        file_list = raw_file.split("---\n", maxsplit=2)
        metadata = json.loads(file_list[1])
        body = file_list[2]

        return Entry(title=metadata["title"], id=metadata["id"], created=datetime.fromisoformat(metadata["created"]), 
                     modified=datetime.fromisoformat(metadata["modified"]), body=body, tag_ids=metadata["tag_ids"])

    def _write_entry(self, folder: str, entry: Entry):
        entries_path = self._root_path / "collections" / folder / "entries"

        metadata = {
            "format_version": FORMAT_VERSION,
            "id": entry.id,
            "title": entry.title,
            "tag_ids": sorted(entry.tag_ids),
            "created": entry.created.isoformat(),
            "modified": entry.modified.isoformat()
        }

        divider = "---"
        filetext = (divider, json.dumps(metadata, indent=2, ensure_ascii=False), divider, entry.body)

        new_entry = entries_path / f"{entry.id}.md"
        self._safe_write(new_entry, "\n".join(filetext))

    @staticmethod
    def _tag_to_dict(tag: Tag) -> dict:
        tag_dict = {
            "id": tag.id,
            "name": tag.name,
            "color": tag.color
        }
        return tag_dict

    @staticmethod
    def _safe_write(path: Path, text: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        
        temp_file = path.with_suffix(".tmp")
        temp_file.write_text(text, encoding="utf-8")
        try:
            temp_file.replace(path)
        except PermissionError:
            time.sleep(0.2) # catch OneDrive hiccups, try again
            temp_file.replace(path)

    @staticmethod
    def _dict_to_tag(data: dict) -> Tag:
        tag = Tag(id=data["id"], name=data["name"], color=data["color"])
        return tag

    def _read_collection(self, folder: Path) -> dict | None:
        if not folder.is_dir():
            return None
        collection_metadata = folder / "collection.json"
        if not collection_metadata.is_file():
            return None
        info = json.loads(collection_metadata.read_text(encoding="utf-8"))
        entries = []
        entries_dir = folder / "entries"
        if entries_dir.is_dir():
            for file in entries_dir.glob("*.md"):
                try:
                    entries.append(self._read_entry(file=file))
                except (json.JSONDecodeError, KeyError, ValueError, IndexError):
                    continue
        custom_tags = [self._dict_to_tag(d) for d in info["custom_tags"]]
        collection_dict = {
            "title": info["title"],
            "description": info["description"],
            "id": info["id"],
            "char_limit": info["char_limit"],
            "entries": entries,
            "custom_tags": custom_tags,
            "tag_ids": info["tag_ids"]
        }
        return collection_dict

    def _write_collection(self, collection: Collection):
        path = self._root_path / "collections" / collection.id / "collection.json"

        collection_dict = {
            "format_version": FORMAT_VERSION,
            "id": collection.id,
            "title": collection.title,
            "description": collection.description,
            "char_limit": collection.char_limit,
            "tag_ids": sorted(collection.tag_ids),
            "custom_tags": [self._tag_to_dict(tag) for tag in collection.custom_tags.values()]
        }

        json_text = json.dumps(collection_dict, indent=2, ensure_ascii=False)
        self._safe_write(path, json_text)

    def load_library(self) -> Library:
        tags_json_file = Path(__file__).parent.parent / "resources" / "default_tags.json"
        tags_list_json = json.loads(tags_json_file.read_text(encoding="utf-8"))
        default_tags_list = []
        for tag_dict in tags_list_json:
            default_tags_list.append(self._dict_to_tag(tag_dict))

        metadata_path = self._root_path / "library.json"
        if metadata_path.is_file():
            try: 
                metafile = metadata_path.read_text(encoding="utf-8")
                metadata = json.loads(metafile)
                tags = [self._dict_to_tag(d) for d in metadata["collection_tags"]]
                library = Library(default_entry_tags=default_tags_list, collection_tags=tags)
            except (json.JSONDecodeError, KeyError) as err:
                raise ValueError(f"Library metadata is damaged and could not be loaded: {err}") from err
        else:
            library = Library(default_entry_tags=default_tags_list)
        

        collections_dir = self._root_path / "collections"
        if not collections_dir.is_dir():
            return library # this is a first-time load, return an empty library
        for folder in collections_dir.iterdir():
            try:
                collection_dict = self._read_collection(folder)
            except (json.JSONDecodeError, KeyError):
                continue
            if collection_dict is None:
                continue
            library.load_collection(**collection_dict)
            
        return library
            
    def save_library(self, library: Library):
        raise NotImplementedError

    def save_collection(self, collection: Collection):
        self._write_collection(collection)

    def delete_collection(self, collection_id: str):
        raise NotImplementedError

    def save_entry(self, collection: Collection, entry: Entry):
        self._write_entry(collection.id, entry)

    def delete_entry(self, collection: Collection, entry_id: str):
        raise NotImplementedError