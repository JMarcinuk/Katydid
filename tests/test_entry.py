from katydid.model.tag import Tag
from katydid.model.entry import Entry
import string
import datetime
import time

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
        t1 = datetime.datetime.now()
        time.sleep(0.1)
        t2 = datetime.datetime.now()
        entry = Entry("Test", id="e1", created=t1, modified=t2)
        assert entry.id == "e1"
        assert entry.created == t1
        assert entry.modified == t2