from katydid.model.entry import Entry
import string
import datetime

import pytest

class TestEntry:

    def test_valid_defaults(self):
        # test that all the defaults in an entry are valid
        test_entry = Entry("Test")
        assert len(test_entry.id) == 32
        assert all(c in string.hexdigits for c in test_entry.id)
        assert test_entry.body == ""
        assert test_entry.tag_ids == set()
        assert test_entry.created == test_entry.modified

    def test_loaded_values_kept(self):
        # test that overridden values are maintained on entry creation
        t1 = datetime.datetime(2024, 8, 24)
        t2 = datetime.datetime(2026, 10, 28)
        entry = Entry("Test", id="e1", created=t1, modified=t2)
        assert entry.id == "e1"
        assert entry.created == t1
        assert entry.modified == t2

    def test_max_length_title_valid(self):
        # test that a 50 character title succeeds
        t = "this title is 50 characters long, right? ok. good."
        e = Entry(t)
        assert e.title == t

    def test_max_plus_one_title_rejects(self):
        # test that a 51 character title is rejected
        t = "wait, you're telling me this is 51 characters? damn"
        with pytest.raises(ValueError):
            Entry(t)

    def test_entry_rejects_non_string_title(self):
        # test that entry throws an error when passed non-string titles
        with pytest.raises(TypeError):
            Entry(69)

    def test_entry_rejects_non_string_body(self):
        # test that entry throws an error when passed a non-string body
        e = Entry("Test")
        with pytest.raises(TypeError):
            e.body = None

    def test_entry_tags_stored_as_set(self):
        # test that tags, when passed as a list, are stored as a set
        e = Entry("Test", tag_ids=["a", "a", "b"])
        assert e.tag_ids == {"a", "b"}

    def test_tag_list_private_copy(self):
        # test that the tag list is not mutable by a passed object
        ids = ["a"]
        e = Entry("Test", tag_ids=ids)
        ids.append("b")
        assert e.tag_ids == {"a"}

    def test_touch_increments_modified_time(self):
        # test that the touch() function in Entry changes the modified time to a newer time
        past_date = datetime.datetime(2024, 8, 24)
        e = Entry("Test", created=past_date, modified=past_date)
        e.touch()
        assert e.created < e.modified
        assert e.created == past_date

    def test_id_read_only(self):
        # test that the id is read-only
        e = Entry("Test")
        with pytest.raises(AttributeError):
            e.id = "test"

    def test_created_read_only(self):
        # test that the creation timestamp is read-only
        e = Entry("Test")
        with pytest.raises(AttributeError):
            e.created = datetime.datetime.now()

    def test_modified_read_only(self):
        # test that the modified timestamp is read-only
        e = Entry("Test")
        with pytest.raises(AttributeError):
            e.modified = datetime.datetime.now()

    def test_tags_not_shared(self):
        # test that updating one entry's tags does not update another's
        e1 = Entry("Test")
        e2 = Entry("Check")
        e1.tag_ids.add("a")
        assert e2.tag_ids == set()

    @pytest.mark.parametrize("text, expected", [
            ("**bold**", 4),
            ("# Head", 4),
            ("[link](http://rngdle.com)", 4),
            ("*italic*", 6),
            ("- list", 4),
            ("> quote", 5),
            ("plain text", 10)
        ])
    def test_length_ignores_markdown(self, qapp, text, expected):
        # test that various markdown formatting characters are not counted in body length
        e = Entry("Test", body=text)
        assert e.length() == expected

    def test_long_body_valid_with_no_limit(self, qapp):
        # test that a long body is valid when there's no character limit
        long_body = "test " * 1000
        e = Entry("Test", body=long_body)
        assert e.is_valid(None)

    def test_body_at_limit_valid(self, qapp):
        ## assert that a body at the character limit is valid with and without markdown
        body = "a" * 10
        bold_body = "**" + body + "**"
        e = Entry("Test", body=body)
        assert e.is_valid(10)
        e.body = bold_body
        assert e.is_valid(10)

    def test_body_over_limit_invalid(self, qapp):
        ## assert that a body one above the character limit is invalid with and without markdown
        body = "a" * 11
        bold_body = "**" + body + "**"
        e = Entry("Test", body=body)
        assert not e.is_valid(10)
        e.body = bold_body
        assert not e.is_valid(10)