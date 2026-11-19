import json
import datetime

import pytest

from katydid.model.library import Library
from katydid.model.tag import Tag
from katydid.storage.repository import MarkdownFolderRepository

# an id from resources/default_tags.json; load_library() reads the real file, not the fixture
REAL_DEFAULT_ID = "default-unsorted"


def entry_path(root, collection_id, entry_id):
    return root / "collections" / collection_id / "entries" / f"{entry_id}.md"


def write_raw(path, text):
    # write a file by hand, bypassing the repository
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def entry_text(metadata, body="body"):
    return "---\n" + json.dumps(metadata) + "\n---\n" + body


def good_metadata(entry_id="hand-made", **overrides):
    metadata = {
        "format_version": 1,
        "id": entry_id,
        "title": "Hand made",
        "tag_ids": ["default-a"],
        "created": "2026-01-01T12:00:00",
        "modified": "2026-01-01T12:00:00",
    }
    metadata.update(overrides)
    return metadata


def collection_metadata(collection_id, **overrides):
    metadata = {
        "format_version": 1,
        "id": collection_id,
        "title": f"Collection {collection_id}",
        "description": "test",
        "char_limit": None,
        "tag_ids": [],
        "custom_tags": [],
    }
    metadata.update(overrides)
    return metadata


@pytest.fixture
def tricky_entry(make_entry):
    body = (
        "# Moonrise\n"
        "\n"
        "The **chill** in the air bit at his face. Mom’s porch light was still on.\n"
        "---\n"
        "Every now and again, the Moon would *oscillate* in the sky."
    )
    return make_entry(title="Moonrise — test entry", body=body, tag_ids={"default-a", "custom-a"})


@pytest.fixture
def saved_collection(repo, collection):
    # the collection fixture, saved to disk with its entries
    repo.save_collection(collection)
    for entry in collection.entries.values():
        repo.save_entry(collection, entry)
    return collection


class TestRepoEntries:

    def test_round_trip_keeps_every_field(self, repo, tmp_path, collection, tricky_entry):
        # test that an awkward entry survives a save and reload unchanged
        repo.save_entry(collection, tricky_entry)
        loaded = repo._read_entry(entry_path(tmp_path, collection.id, tricky_entry.id))
        assert loaded.id == tricky_entry.id
        assert loaded.title == tricky_entry.title
        assert loaded.body == tricky_entry.body
        assert loaded.tag_ids == tricky_entry.tag_ids
        assert loaded.created == tricky_entry.created
        assert loaded.modified == tricky_entry.modified

    def test_file_location_and_name(self, repo, tmp_path, collection, make_entry):
        # test that an entry is saved under its collection, named by its id
        entry = make_entry()
        repo.save_entry(collection, entry)
        assert entry_path(tmp_path, collection.id, entry.id).is_file()

    def test_no_leftover_temp_file(self, repo, tmp_path, collection, make_entry):
        # test that the safe write leaves no .tmp file behind
        entry = make_entry()
        repo.save_entry(collection, entry)
        folder = entry_path(tmp_path, collection.id, entry.id).parent
        assert list(folder.glob("*.tmp")) == []

    def test_non_ascii_stays_readable(self, repo, tmp_path, collection, make_entry):
        # test that curly quotes are written as-is, not escaped
        entry = make_entry(title="Mom’s garden")
        repo.save_entry(collection, entry)
        raw = entry_path(tmp_path, collection.id, entry.id).read_text(encoding="utf-8")
        assert "’" in raw
        assert "\\u2019" not in raw

    def test_saving_twice_overwrites(self, repo, tmp_path, collection, make_entry):
        # test that saving the same entry twice leaves one file with the newest body
        entry = make_entry(body="first")
        repo.save_entry(collection, entry)
        entry.body = "second"
        repo.save_entry(collection, entry)
        folder = entry_path(tmp_path, collection.id, entry.id).parent
        assert len(list(folder.glob("*.md"))) == 1
        assert repo._read_entry(entry_path(tmp_path, collection.id, entry.id)).body == "second"


class TestRepoCollectionsAndLibrary:

    def test_first_run(self, repo, tmp_path):
        # test that loading an empty folder gives an empty library and creates nothing
        library = repo.load_library()
        assert library.collections == {}
        assert REAL_DEFAULT_ID in library.default_entry_tags
        assert list(tmp_path.iterdir()) == []

    def test_collection_writes_only_its_own_file(self, repo, tmp_path, collection):
        # test that saving a collection writes collection.json but no entries
        repo.save_collection(collection)
        folder = tmp_path / "collections" / collection.id
        assert (folder / "collection.json").is_file()
        assert not (folder / "entries").exists()

    @pytest.mark.parametrize("limit", [None, 500])
    def test_collection_round_trip(self, repo, limit):
        # test that a collection's fields survive a save and reload
        lib = Library(collection_tags=[Tag("Work", "#577C9F", id="ctag-a")])
        col = lib.create_collection(title="Round", description="trip", char_limit=limit)
        lib.set_collection_tags(col.id, {"ctag-a"})
        custom = col.add_tag("Lantern", "#3366CC")
        repo.save_library(lib)
        repo.save_collection(col)

        loaded = repo.load_library().get_collection(col.id)
        assert loaded.title == "Round"
        assert loaded.description == "trip"
        assert loaded.char_limit == limit
        assert loaded.tag_ids == {"ctag-a"}
        assert loaded.custom_tags[custom.id].name == "Lantern"

    def test_loaded_collections_see_defaults(self, repo, saved_collection):
        # test that a loaded collection can use the default tags
        loaded = repo.load_library().get_collection(saved_collection.id)
        assert REAL_DEFAULT_ID in loaded.available_tags()

    def test_library_round_trip(self, repo):
        # test that collection tags survive a save and reload with their ids
        lib = Library(collection_tags=[Tag("Work", "#577C9F", id="ctag-a"), Tag("Home", "#AABBCC", id="ctag-b")])
        repo.save_library(lib)
        loaded = repo.load_library()
        assert set(loaded.collection_tags) == {"ctag-a", "ctag-b"}
        assert loaded.collection_tags["ctag-b"].name == "Home"

    def test_whole_library_round_trip(self, tmp_path, default_tags, make_entry):
        # test that a full library saved by one repo loads identically in another
        lib = Library(default_entry_tags=list(default_tags.values()),
                      collection_tags=[Tag("Work", "#577C9F", id="ctag-a")])
        writer = MarkdownFolderRepository(tmp_path)
        for title in ["One", "Two"]:
            col = lib.create_collection(title=title, description="test")
            col.add_entry(make_entry())
            col.add_entry(make_entry())
            writer.save_collection(col)
            for entry in col.entries.values():
                writer.save_entry(col, entry)
        writer.save_library(lib)

        loaded = MarkdownFolderRepository(tmp_path).load_library()
        assert set(loaded.collections) == set(lib.collections)
        assert set(loaded.collection_tags) == {"ctag-a"}
        for col_id, original in lib.collections.items():
            loaded_col = loaded.get_collection(col_id)
            assert set(loaded_col.entries) == set(original.entries)
            for entry_id, entry in original.entries.items():
                assert loaded_col.get_entry(entry_id).body == entry.body


class TestRepoDamagedFiles:

    @pytest.mark.parametrize("bad_text", [
        "---\n{not json\n---\nbody",
        "no dividers at all",
        entry_text({k: v for k, v in good_metadata().items() if k != "title"}),
    ], ids=["broken-json", "no-dividers", "missing-title"])
    def test_damaged_entry_skipped(self, repo, tmp_path, saved_collection, bad_text):
        # test that a damaged entry file is skipped and the rest still load
        write_raw(entry_path(tmp_path, saved_collection.id, "bad"), bad_text)
        loaded = repo.load_library().get_collection(saved_collection.id)
        assert set(loaded.entries) == set(saved_collection.entries)

    def test_damaged_collection_skipped(self, repo, tmp_path, saved_collection):
        # test that a damaged collection.json is skipped and other collections still load
        write_raw(tmp_path / "collections" / "bad" / "collection.json", "{nope")
        assert set(repo.load_library().collections) == {saved_collection.id}

    @pytest.mark.parametrize("stray", ["empty-folder", "stray-file"])
    def test_non_collections_skipped(self, repo, tmp_path, saved_collection, stray):
        # test that folders without collection.json and stray files are ignored
        if stray == "empty-folder":
            (tmp_path / "collections" / "not-a-collection").mkdir()
        else:
            write_raw(tmp_path / "collections" / "notes.txt", "hello")
        assert set(repo.load_library().collections) == {saved_collection.id}

    @pytest.mark.parametrize("bad_text", ["{broken", '{"format_version": 1}'],
                             ids=["broken-json", "missing-collection-tags"])
    def test_damaged_library_file_rejected(self, repo, tmp_path, bad_text):
        # test that a damaged library.json raises rather than loading empty
        write_raw(tmp_path / "library.json", bad_text)
        with pytest.raises(ValueError):
            repo.load_library()

    def test_stray_temp_file_ignored(self, repo, tmp_path, saved_collection):
        # test that a leftover .tmp file is not loaded as an entry
        folder = entry_path(tmp_path, saved_collection.id, "x").parent
        write_raw(folder / "leftover.tmp", entry_text(good_metadata("leftover")))
        loaded = repo.load_library().get_collection(saved_collection.id)
        assert set(loaded.entries) == set(saved_collection.entries)

    def test_newer_entry_skipped(self, repo, tmp_path, saved_collection):
        # test that an entry from a newer format version is skipped
        write_raw(entry_path(tmp_path, saved_collection.id, "future"),
                  entry_text(good_metadata("future", format_version=99)))
        loaded = repo.load_library().get_collection(saved_collection.id)
        assert "future" not in loaded.entries

    def test_newer_collection_skipped(self, repo, tmp_path, saved_collection):
        # test that a collection from a newer format version is skipped
        write_raw(tmp_path / "collections" / "future" / "collection.json",
                  json.dumps(collection_metadata("future", format_version=99)))
        assert set(repo.load_library().collections) == {saved_collection.id}

    def test_newer_library_refused(self, repo, tmp_path):
        # test that a library.json from a newer format version raises
        write_raw(tmp_path / "library.json", json.dumps({"format_version": 99, "collection_tags": []}))
        with pytest.raises(ValueError, match="newer"):
            repo.load_library()

    def test_missing_version_means_one(self, repo, tmp_path, saved_collection):
        # test that an entry header with no format_version still loads
        metadata = good_metadata("old-style")
        del metadata["format_version"]
        write_raw(entry_path(tmp_path, saved_collection.id, "old-style"), entry_text(metadata))
        loaded = repo.load_library().get_collection(saved_collection.id)
        assert "old-style" in loaded.entries


class TestRepoDeletes:

    def test_delete_entry(self, repo, tmp_path, saved_collection):
        # test that deleting an entry removes its file
        entry_id = next(iter(saved_collection.entries))
        repo.delete_entry(saved_collection, entry_id)
        assert not entry_path(tmp_path, saved_collection.id, entry_id).exists()

    def test_delete_missing_entry(self, repo, saved_collection):
        # test that deleting an entry with no file is not an error
        repo.delete_entry(saved_collection, "abc")

    def test_collection_goes_to_trash(self, repo, tmp_path, saved_collection):
        # test that a deleted collection is moved into .trash, not destroyed
        repo.delete_collection(saved_collection.id)
        assert not (tmp_path / "collections" / saved_collection.id).exists()
        trashed = [p.name for p in (tmp_path / ".trash").iterdir()]
        assert any(name.startswith(f"{saved_collection.id}_") for name in trashed)

    def test_trash_never_loaded(self, repo, saved_collection):
        # test that a trashed collection does not come back on load
        repo.delete_collection(saved_collection.id)
        assert saved_collection.id not in repo.load_library().collections

    def test_delete_missing_collection(self, repo):
        # test that deleting a collection with no folder is not an error
        repo.delete_collection("abc")

    @pytest.mark.parametrize("bad_id", ["", ".", "..", "a/b", "a\\b"])
    def test_unsafe_ids_refused(self, repo, tmp_path, saved_collection, bad_id):
        # test that unsafe ids are refused by both deletes and nothing is removed
        with pytest.raises(ValueError):
            repo.delete_entry(saved_collection, bad_id)
        with pytest.raises(ValueError):
            repo.delete_collection(bad_id)
        assert (tmp_path / "collections" / saved_collection.id / "collection.json").is_file()