import pytest

from katydid.model.library import Library
from katydid.model.tag import Tag
from katydid.model.query import CollectionQuery, TagMode
from katydid.model.errors import DuplicateContentError


def first_collection(library):
    # the library fixture holds exactly one collection; return it
    return next(iter(library.collections.values()))


class TestLibraryCollections:

    def test_new_library_empty(self):
        # test that a new library has no collections or tags
        lib = Library()
        assert lib.collections == {}
        assert lib.collection_tags == {}
        assert lib.default_entry_tags == {}

    def test_defaults_keyed_by_id(self, default_tags):
        # test that default tags passed as a list are stored keyed by id
        lib = Library(default_entry_tags=list(default_tags.values()))
        assert set(lib.default_entry_tags) == set(default_tags)

    def test_create_collection(self, library):
        # test that a created collection is returned and can be retrieved
        new_col = library.create_collection(title="Recipes", description="things to cook")
        assert library.get_collection(new_col.id) is new_col

    def test_new_collections_see_defaults(self, library, default_tags):
        # test that a new collection can use every default tag
        new_col = library.create_collection(title="Recipes", description="things to cook")
        assert set(default_tags) <= set(new_col.available_tags())

    def test_duplicate_title_normalized(self, library):
        # test that a title matching an existing one, ignoring case and spaces, is rejected
        with pytest.raises(DuplicateContentError):
            library.create_collection(title="  tests ", description="test")

    def test_loading_skips_title_check(self):
        # test that loading never fails over duplicate titles
        lib = Library()
        for col_id in ["c1", "c2"]:
            lib.load_collection(title="Same", description="test", id=col_id, char_limit=None,
                                entries=[], custom_tags=[], tag_ids=[])
        assert len(lib.collections) == 2

    def test_rename_collection(self, library):
        # test that a collection can be renamed
        col = first_collection(library)
        library.rename_collection(col.id, "Notes")
        assert col.title == "Notes"

    def test_rename_to_own_title_new_case(self, library):
        # test that renaming a collection to its own title in a different case is allowed
        col = first_collection(library)
        new_title = col.title.upper()
        library.rename_collection(col.id, new_title)
        assert col.title == new_title

    def test_rename_to_taken_title_rejected(self, library):
        # test that renaming to another collection's title is rejected
        other = library.create_collection(title="Other", description="test")
        with pytest.raises(DuplicateContentError):
            library.rename_collection(other.id, first_collection(library).title)

    def test_rename_unknown_collection_rejected(self, library):
        # test that renaming an unknown collection raises
        with pytest.raises(KeyError):
            library.rename_collection("nope", "Anything")

    def test_change_description(self, library):
        # test that a collection's description can be changed
        col = first_collection(library)
        library.change_collection_description(col.id, "new")
        assert col.description == "new"

    def test_description_too_long_rejected(self, library):
        # test that a description over 500 characters is rejected
        col = first_collection(library)
        with pytest.raises(ValueError):
            library.change_collection_description(col.id, "a" * 501)

    def test_description_unknown_collection_rejected(self, library):
        # test that changing an unknown collection's description raises
        with pytest.raises(KeyError):
            library.change_collection_description("nope", "new")

    def test_delete_returns_collection(self, library):
        # test that deleting a collection returns it and it can no longer be found
        col = first_collection(library)
        assert library.delete_collection(col.id) is col
        with pytest.raises(KeyError):
            library.get_collection(col.id)

    @pytest.mark.parametrize("method", ["get_collection", "delete_collection"])
    def test_unknown_collection_id_rejected(self, library, method):
        # test that getting or deleting an unknown id raises
        with pytest.raises(KeyError):
            getattr(library, method)("nope")


class TestLibraryCollectionTags:

    def test_add_collection_tag(self, library):
        # test that an added collection tag is returned and stored
        new_tag = library.add_collection_tag("Work", "#3366CC")
        assert new_tag.id in library.collection_tags

    def test_duplicate_tag_name_normalized(self, library):
        # test that a tag name matching an existing one, ignoring case and spaces, is rejected
        with pytest.raises(DuplicateContentError):
            library.add_collection_tag("  category ", "#3366CC")

    def test_rename_collection_tag(self, library):
        # test that a collection tag can be renamed
        library.rename_collection_tag("ctag-a", "Home")
        assert library.collection_tags["ctag-a"].name == "Home"

    def test_rename_tag_to_taken_name_rejected(self, library):
        # test that renaming a tag to another tag's name is rejected
        other = library.add_collection_tag("Work", "#3366CC")
        with pytest.raises(DuplicateContentError):
            library.rename_collection_tag(other.id, "Category")

    def test_rename_unknown_tag_rejected(self, library):
        # test that renaming an unknown tag raises
        with pytest.raises(KeyError):
            library.rename_collection_tag("nope", "Anything")

    def test_assign_tags(self, library):
        # test that tags can be assigned to a collection
        col = first_collection(library)
        other = library.add_collection_tag("Work", "#3366CC")
        library.set_collection_tags(col.id, {"ctag-a", other.id})
        assert col.tag_ids == {"ctag-a", other.id}

    def test_clear_tags(self, library):
        # test that assigning an empty set clears a collection's tags
        col = first_collection(library)
        library.set_collection_tags(col.id, {"ctag-a"})
        library.set_collection_tags(col.id, set())
        assert col.tag_ids == set()

    def test_unknown_tag_changes_nothing(self, library):
        # test that an unknown tag id raises and leaves the collection's tags unchanged
        col = first_collection(library)
        library.set_collection_tags(col.id, {"ctag-a"})
        with pytest.raises(KeyError):
            library.set_collection_tags(col.id, {"ctag-a", "ghost"})
        assert col.tag_ids == {"ctag-a"}

    def test_set_tags_unknown_collection_rejected(self, library):
        # test that tagging an unknown collection raises
        with pytest.raises(KeyError):
            library.set_collection_tags("nope", set())

    def test_delete_never_blocks(self, library):
        # test that deleting a collection's only tag succeeds and clears it
        col = first_collection(library)
        library.set_collection_tags(col.id, {"ctag-a"})
        library.delete_collection_tag("ctag-a")
        assert col.tag_ids == set()

    def test_delete_returns_changed_collections(self, library):
        # test that deleting a tag returns only the collections that had it
        tagged = first_collection(library)
        library.create_collection(title="Untagged", description="test")
        library.set_collection_tags(tagged.id, {"ctag-a"})
        changed = library.delete_collection_tag("ctag-a")
        assert changed == [tagged]
        assert "ctag-a" not in library.collection_tags

    def test_delete_unknown_tag_rejected(self, library):
        # test that deleting an unknown tag raises
        with pytest.raises(KeyError):
            library.delete_collection_tag("nope")


class TestLibraryQueries:

    def test_empty_query_returns_all(self, library):
        # test that a default query returns every collection
        library.create_collection(title="Two", description="test")
        library.create_collection(title="Three", description="test")
        assert len(library.query_collections(CollectionQuery())) == 3

    def test_keyword_title_or_description(self, library):
        # test that keywords match titles and descriptions
        by_title = library.create_collection(title="Recipes", description="test")
        by_desc = library.create_collection(title="Cooking", description="a recipe box")
        results = library.query_collections(CollectionQuery(keywords="recipe"))
        assert {c.id for c in results} == {by_title.id, by_desc.id}

    @pytest.mark.parametrize("mode, expected", [(TagMode.ALL, 1), (TagMode.ANY, 3)])
    def test_tag_modes(self, mode, expected):
        # test that ALL keeps collections with every selected tag and ANY keeps those with at least one
        lib = Library()
        a = lib.add_collection_tag("A", "#3366CC")
        b = lib.add_collection_tag("B", "#AABBCC")
        for title, tags in [("One", {a.id}), ("Two", {a.id, b.id}), ("Three", {b.id})]:
            col = lib.create_collection(title=title, description="test")
            lib.set_collection_tags(col.id, tags)
        results = lib.query_collections(CollectionQuery(tag_ids={a.id, b.id}, mode=mode))
        assert len(results) == expected