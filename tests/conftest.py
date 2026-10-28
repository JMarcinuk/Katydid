import pytest

from katydid.model.tag import Tag
from katydid.model.entry import Entry
from katydid.model.collection import Collection
from katydid.model.library import Library

from katydid.storage.repository import MarkdownFolderRepository

@pytest.fixture
def default_tags():
    tags = [
        Tag(name="Default A", color="#000000", id="default-a"),
        Tag(name="Default B", color="#FFFFFF", id='default-b')
    ]
    return {tag.id: tag for tag in tags}
    
@pytest.fixture
def make_entry():
    count = 0

    def _make(**overrides):
        nonlocal count
        count += 1
        values = {"title": f"TestEntry {count}", "tag_ids": {"default-a"}}
        values.update(overrides)
        return Entry(**values)

    return _make

@pytest.fixture
def collection(default_tags, make_entry):
    custom = Tag("CustomTest", "#121289", id="custom-a")
    entries = [
        make_entry(title="Test", tag_ids={"default-a"}),
        make_entry(title="Check", tag_ids={"default-a", "custom-a"})
    ]
    return Collection(
        "Test Collection", "test description", default_tags, entries=entries, custom_tags=[custom]
    )

@pytest.fixture
def library(default_tags):
    lib = Library(default_entry_tags=list(default_tags.values()), 
                  collection_tags=[Tag("Category", "#891212", id="ctag-a")])
    lib.create_collection("Tests", "test collection")
    return lib

@pytest.fixture
def repo(tmp_path):
    return MarkdownFolderRepository(tmp_path)