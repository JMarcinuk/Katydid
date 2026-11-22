import pytest
import datetime

from katydid.model.collection import Collection
from katydid.model.tag import Tag
from katydid.model.entry import Entry
from katydid.model.query import EntryQuery, EntrySort, TagMode
from katydid.model.errors import (
    CharLimitConflictError,
    DefaultTagError,
    DuplicateContentError,
    EntryValidationError,
    TagInUseError,
)

class TestCollectionConstruction:

    def test_lists_become_dicts_by_ID(self):
        # test that passed lists become dicts and are keyed by the generated id
        entries = [Entry("Test1"), Entry("Test2")]
        tags = [Tag("Test", "#AABBCC")]
        test_col = Collection(title="Test", description="test", default_tags={}, entries=entries, custom_tags=tags)
        assert isinstance(test_col.entries, dict)
        assert set(test_col.entries) == {e.id for e in entries}
        assert test_col.entries[entries[0].id] is entries[0]
        assert isinstance(test_col.custom_tags, dict)
        assert set(test_col.custom_tags) == {t.id for t in tags}
        assert test_col.custom_tags[tags[0].id] is tags[0]

    def test_getters_return_copies(self, collection):
        # check that getters return copies of entries rather than the entries themselves
        before = len(collection.entries)
        collection.entries.clear()
        assert len(collection.entries) == before

    def test_defaults_shared_not_copied(self, default_tags):
        # check that default_tags is a shared dict not a copy
        new_tag = Tag("Test", "#AABBCC")
        collection = Collection(title="Test", description="test", default_tags=default_tags)
        default_tags[new_tag.id] = new_tag
        assert new_tag.id in collection.available_tags()

    def test_too_long_title_disallowed(self):
        # test collections disallow a title longer than 50 characters
        with pytest.raises(ValueError):
            Collection(title="This title is way too long. A whole 51 characters!!", description="test", default_tags={})

    def test_too_long_description_disallowed(self):
        # test collections disallow a title longer than 500 characters
        test_desc = 'a' * 501
        with pytest.raises(ValueError):
            Collection(title="Test", description=test_desc, default_tags={})

    def test_non_string_title_disallowed(self):
        # test a collection with a non-string for a title errors
        with pytest.raises(TypeError):
            Collection(title=42, description="test", default_tags={})

    def test_non_string_description_disallowed(self):
        # test a collection with a non-string for a description errors
        with pytest.raises(TypeError):
            Collection(title="Test", description=42, default_tags={})


class TestCharLimit:
 
    @pytest.mark.parametrize("limit", [None, 1, 500])
    def test_accepted_limits(self, limit):
        # test that None and positive integers are accepted as character limits
        test_col = Collection(title="Test", description="test", default_tags={}, char_limit=limit)
        assert test_col.char_limit == limit
 
    @pytest.mark.parametrize("limit, error", [
        (0, ValueError),
        (-5, ValueError),
        ("500", TypeError),
        (True, TypeError),
        (2.5, TypeError),
    ])
    def test_bad_limits_rejected(self, limit, error):
        # test that zero, negatives, and non-integers are rejected as character limits
        with pytest.raises(error):
            Collection(title="Test", description="test", default_tags={}, char_limit=limit)
 
    def test_loading_never_blocked(self, qapp, default_tags, make_entry):
        # test that a collection loads even when an existing entry is over its limit
        long_entry = make_entry(body="a" * 20)
        test_col = Collection(title="Test", description="test", default_tags=default_tags,
                              char_limit=10, entries=[long_entry])
        assert long_entry.id in test_col.entries
 
    def test_lowering_below_entry_blocked(self, qapp, default_tags, make_entry):
        # test that lowering the limit below an existing entry raises and leaves the limit unchanged
        long_entry = make_entry(body="a" * 20)
        test_col = Collection(title="Test", description="test", default_tags=default_tags,
                              char_limit=100, entries=[long_entry])
        with pytest.raises(CharLimitConflictError) as err:
            test_col.char_limit = 10
        assert err.value.conflicting_entries == [long_entry]
        assert test_col.char_limit == 100
 
    def test_all_conflicts_reported(self, qapp, default_tags, make_entry):
        # test that every over-length entry is reported, not just the first
        entries = [make_entry(body="a" * 20), make_entry(body="b" * 30)]
        test_col = Collection(title="Test", description="test", default_tags=default_tags,
                              char_limit=100, entries=entries)
        with pytest.raises(CharLimitConflictError) as err:
            test_col.char_limit = 10
        assert len(err.value.conflicting_entries) == 2
 
    def test_removing_limit_always_allowed(self, qapp, default_tags, make_entry):
        # test that removing a limit never conflicts
        test_col = Collection(title="Test", description="test", default_tags=default_tags,
                              char_limit=100, entries=[make_entry(body="a" * 50)])
        test_col.char_limit = None
        assert test_col.char_limit is None
 
 
class TestCollectionEntries:
 
    def test_add_valid_entry(self, qapp, collection, make_entry):
        # test that a valid entry can be added and retrieved
        new_entry = make_entry()
        collection.add_entry(new_entry)
        assert collection.get_entry(new_entry.id) is new_entry
 
    def test_add_duplicate_id_rejected(self, qapp, collection):
        # test that adding an entry whose id is already stored raises
        existing = next(iter(collection.entries.values()))
        with pytest.raises(KeyError):
            collection.add_entry(existing)
 
    def test_add_invalid_entry_rejected(self, qapp, collection, make_entry):
        # test that an invalid entry raises and is not stored
        bad_entry = make_entry(tag_ids=set())
        with pytest.raises(EntryValidationError):
            collection.add_entry(bad_entry)
        assert bad_entry.id not in collection.entries
 
    def test_update_replaces_entry(self, qapp, collection):
        # test that updating stores the draft and refreshes its modified time
        stored = next(iter(collection.entries.values()))
        old = datetime.datetime(2020, 1, 1)
        draft = Entry(title=stored.title, id=stored.id, created=stored.created, modified=old,
                      body="new body", tag_ids=stored.tag_ids)
        collection.update_entry(draft)
        assert collection.get_entry(stored.id) is draft
        assert draft.modified > old
 
    def test_update_unknown_id_rejected(self, qapp, collection, make_entry):
        # test that updating an entry that isn't stored raises
        with pytest.raises(KeyError):
            collection.update_entry(make_entry())
 
    def test_failed_update_changes_nothing(self, qapp, collection):
        # test that an invalid update leaves the stored entry in place
        stored = next(iter(collection.entries.values()))
        draft = Entry(title=stored.title, id=stored.id, created=stored.created, body="new body", tag_ids=set())
        with pytest.raises(EntryValidationError):
            collection.update_entry(draft)
        assert collection.get_entry(stored.id) is stored
 
    def test_remove_returns_entry(self, collection):
        # test that removing an entry returns it and it can no longer be found
        stored = next(iter(collection.entries.values()))
        removed = collection.remove_entry(stored.id)
        assert removed is stored
        with pytest.raises(KeyError):
            collection.get_entry(stored.id)
 
    @pytest.mark.parametrize("method", ["remove_entry", "get_entry"])
    def test_unknown_entry_id_rejected(self, collection, method):
        # test that removing or getting an unknown id raises
        with pytest.raises(KeyError):
            getattr(collection, method)("nope")
 
 
class TestEntryValidation:
 
    def test_valid_entry_has_no_problems(self, qapp, collection, make_entry):
        # test that a valid entry produces an empty problem list
        assert collection.validate_entry(make_entry()) == []
 
    def test_over_limit_reported(self, qapp, default_tags, make_entry):
        # test that an entry over the character limit produces one problem
        test_col = Collection(title="Test", description="test", default_tags=default_tags, char_limit=10)
        assert len(test_col.validate_entry(make_entry(body="a" * 20))) == 1
 
    def test_no_tags_reported(self, qapp, collection, make_entry):
        # test that an entry with no tags produces one problem
        assert len(collection.validate_entry(make_entry(tag_ids=set()))) == 1
 
    def test_unknown_tag_reported(self, qapp, collection, make_entry):
        # test that an entry tagged with a nonexistent tag produces one problem
        assert len(collection.validate_entry(make_entry(tag_ids={"ghost"}))) == 1
 
    def test_duplicate_title_normalized(self, qapp, collection, make_entry):
        # test that a title matching a stored one, ignoring case and spaces, produces one problem
        stored_title = next(iter(collection.entries.values())).title
        new_entry = make_entry(title=f"  {stored_title.upper()} ")
        assert len(collection.validate_entry(new_entry)) == 1
 
    def test_own_title_not_duplicate(self, qapp, collection):
        # test that re-validating a stored entry doesn't flag its own title
        stored = next(iter(collection.entries.values()))
        assert collection.validate_entry(stored) == []
 
    def test_every_problem_reported(self, qapp, default_tags, make_entry):
        # test that several problems are all reported together
        test_col = Collection(title="Test", description="test", default_tags=default_tags,
                              char_limit=10, entries=[make_entry(title="Moon")])
        bad_entry = make_entry(title=" moon", body="a" * 20, tag_ids=set())
        assert len(test_col.validate_entry(bad_entry)) == 3
 
 
class TestCollectionTags:
 
    def test_add_tag(self, collection):
        # test that an added tag is returned and is available
        new_tag = collection.add_tag("Lantern", "#3366CC")
        assert new_tag.id in collection.custom_tags
        assert new_tag.id in collection.available_tags()
 
    @pytest.mark.parametrize("name", ["  customtest ", "Default A"])
    def test_duplicate_tag_name_rejected(self, collection, name):
        # test that names matching a custom or default tag, ignoring case and spaces, are rejected
        with pytest.raises(DuplicateContentError):
            collection.add_tag(name, "#3366CC")
 
    def test_bad_color_adds_nothing(self, collection):
        # test that a tag with an invalid color raises and isn't added
        before = len(collection.custom_tags)
        with pytest.raises(ValueError):
            collection.add_tag("x", "#ZZZZZZ")
        assert len(collection.custom_tags) == before
 
    def test_rename_tag(self, collection):
        # test that a custom tag can be renamed
        collection.rename_tag("custom-a", "Glass")
        assert collection.custom_tags["custom-a"].name == "Glass"
 
    def test_rename_to_own_name_new_case(self, collection):
        # test that renaming a tag to its own name in a different case is allowed
        collection.rename_tag("custom-a", "CUSTOMTEST")
        assert collection.custom_tags["custom-a"].name == "CUSTOMTEST"
 
    @pytest.mark.parametrize("tag_id, new_name, error", [
        ("custom-a", "Default A", DuplicateContentError),
        ("default-a", "Anything", DefaultTagError),
        ("nope", "Anything", KeyError),
    ])
    def test_rename_refused(self, collection, tag_id, new_name, error):
        # test that renames to a taken name, of a default tag, or of an unknown tag are refused
        with pytest.raises(error):
            collection.rename_tag(tag_id, new_name)
 
    def test_blocking_entries_sole_tag_only(self, collection):
        # test that only entries whose only tag is the given one are reported
        blocking = collection.blocking_entries("default-a")
        assert len(blocking) == 1
        assert blocking[0].tag_ids == {"default-a"}
 
    def test_no_blockers(self, collection):
        # test that a tag that is never an entry's only tag has no blockers
        assert collection.blocking_entries("custom-a") == []
 
    def test_delete_blocked(self, collection, make_entry):
        # test that deleting an entry's only tag raises, reports that entry, and keeps the tag
        lonely = make_entry(tag_ids={"custom-a"})
        collection.add_entry(lonely)
        with pytest.raises(TagInUseError) as err:
            collection.delete_tag("custom-a")
        assert err.value.blocking_entries == [lonely]
        assert "custom-a" in collection.custom_tags
 
    def test_delete_tag_cleans_up_entries(self, collection):
        # deleting a tag that is never an entry's only tag succeeds and removes it from every entry
        changed = collection.delete_tag("custom-a")
        assert "custom-a" not in collection.custom_tags
        assert all("custom-a" not in e.tag_ids for e in collection.entries.values())
        assert len(changed) == 1
 
    @pytest.mark.parametrize("tag_id, error", [
        ("default-a", DefaultTagError),
        ("nope", KeyError),
    ])
    def test_delete_refused(self, collection, tag_id, error):
        # test that deleting a default or unknown tag is refused
        with pytest.raises(error):
            collection.delete_tag(tag_id)
 
 
class TestCollectionQueries:
 
    def test_empty_query_returns_all(self, collection):
        # test that a default query returns every entry
        assert len(collection.query(EntryQuery())) == len(collection.entries)
 
    def test_keyword_any_case_title_or_body(self, default_tags, make_entry):
        # test that keywords match titles and bodies regardless of case
        entries = [make_entry(title="Moon"), make_entry(body="The moon rose."), make_entry(title="Sun")]
        test_col = Collection(title="Test", description="test", default_tags=default_tags, entries=entries)
        results = test_col.query(EntryQuery(keywords="MOON"))
        assert {e.id for e in results} == {entries[0].id, entries[1].id}
 
    def test_partial_word_match(self, default_tags, make_entry):
        # test that a keyword matches part of a longer word
        entry = make_entry(body="moonlight")
        test_col = Collection(title="Test", description="test", default_tags=default_tags, entries=[entry])
        assert test_col.query(EntryQuery(keywords="moon")) == [entry]
 
    def test_all_keywords_required(self, default_tags, make_entry):
        # test that every keyword must appear for an entry to match
        both = make_entry(body="moon glass")
        one = make_entry(body="moon")
        test_col = Collection(title="Test", description="test", default_tags=default_tags, entries=[both, one])
        assert test_col.query(EntryQuery(keywords="moon glass")) == [both]
 
    def test_tag_mode_all(self, default_tags, make_entry):
        # test that ALL mode keeps only entries with every selected tag
        only_a = make_entry(tag_ids={"default-a"})
        both = make_entry(tag_ids={"default-a", "default-b"})
        test_col = Collection(title="Test", description="test", default_tags=default_tags, entries=[only_a, both])
        query = EntryQuery(tag_ids={"default-a", "default-b"}, mode=TagMode.ALL)
        assert test_col.query(query) == [both]
 
    def test_tag_mode_any(self, default_tags, make_entry):
        # test that ANY mode keeps entries with at least one selected tag
        a = make_entry(tag_ids={"default-a"})
        b = make_entry(tag_ids={"default-b"})
        c = make_entry(tag_ids={"other"})
        test_col = Collection(title="Test", description="test", default_tags=default_tags, entries=[a, b, c])
        query = EntryQuery(tag_ids={"default-a", "default-b"}, mode=TagMode.ANY)
        assert {e.id for e in test_col.query(query)} == {a.id, b.id}
 
    def test_any_with_nothing_selected(self, collection):
        # test that ANY mode with no tags selected returns every entry
        query = EntryQuery(mode=TagMode.ANY)
        assert len(collection.query(query)) == len(collection.entries)
 
    def test_keyword_and_tag_combine(self, default_tags, make_entry):
        # test that keyword and tag filters both apply
        match = make_entry(title="Moon", tag_ids={"default-b"})
        wrong_tag = make_entry(body="moon", tag_ids={"default-a"})
        wrong_word = make_entry(title="Sun", tag_ids={"default-b"})
        test_col = Collection(title="Test", description="test", default_tags=default_tags,
                              entries=[match, wrong_tag, wrong_word])
        query = EntryQuery(keywords="moon", tag_ids={"default-b"})
        assert test_col.query(query) == [match]
 
    def test_recent_sort_and_flip(self, default_tags, make_entry):
        # test that recent sort puts the newest first, and flip reverses it
        base = datetime.datetime(2026, 1, 1)
        entries = [make_entry(title=f"Day {i}", modified=base + datetime.timedelta(days=i)) for i in range(3)]
        test_col = Collection(title="Test", description="test", default_tags=default_tags, entries=entries)
        newest_first = [e.title for e in test_col.query(EntryQuery(sort=EntrySort.RECENT))]
        oldest_first = [e.title for e in test_col.query(EntryQuery(sort=EntrySort.RECENT, flip=True))]
        assert newest_first == ["Day 2", "Day 1", "Day 0"]
        assert oldest_first == ["Day 0", "Day 1", "Day 2"]
 
    def test_title_sort_any_case(self, default_tags, make_entry):
        # test that title sort is alphabetical regardless of case
        entries = [make_entry(title="b"), make_entry(title="A"), make_entry(title="c")]
        test_col = Collection(title="Test", description="test", default_tags=default_tags, entries=entries)
        titles = [e.title for e in test_col.query(EntryQuery(sort=EntrySort.TITLE))]
        assert titles == ["A", "b", "c"]
 
    def test_length_sort(self, qapp, default_tags, make_entry):
        # test that length sort puts the longest entry first
        entries = [make_entry(body="aa"), make_entry(body="aaaa"), make_entry(body="a")]
        test_col = Collection(title="Test", description="test", default_tags=default_tags, entries=entries)
        lengths = [e.length() for e in test_col.query(EntryQuery(sort=EntrySort.LENGTH))]
        assert lengths == [4, 2, 1]
 
    def test_query_never_changes_data(self, collection):
        # test that a narrowing query leaves the stored entries untouched
        before = len(collection.entries)
        collection.query(EntryQuery(keywords="nothing matches this"))
        assert len(collection.entries) == before