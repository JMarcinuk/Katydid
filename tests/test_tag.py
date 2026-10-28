from katydid.model.tag import Tag
import string

import pytest

class TestTag:

    def test_new_id_generated(self):
        # test that tags generate a 32-character hex string when created
        test_tag = Tag("Test", "#AABBCC")
        assert len(test_tag.id) == 32
        assert all(c in string.hexdigits for c in test_tag.id)

    def test_tag_ids_unique(self):
        # test that two otherwise identical tags generate different ids
        tag_a = Tag("Test", "#AABBCC")
        tag_b = Tag("Test", "#AABBCC")
        assert tag_a.id != tag_b.id

    def test_overridden_id_allowed(self):
        # test that an overridden id is kept during tag creation
        tag = Tag("Test", "#AABBCC", id="default-a")
        assert tag.id == "default-a"

    @pytest.mark.parametrize("c", ["#1cA3fE", "#AABBCC", "#000000", "#ffffff"])
    def test_valid_colors_allowed(self, c):
        # test that valid colors are accepted by the constructor and properly set
        tag = Tag("x", c)
        assert tag.color == c

    @pytest.mark.parametrize("c", ["#ZZZZZZ", "AABBCC", "112233", "#FFF", "#AABBCC0", ""])
    def test_invalid_colors_rejected(self, c):
        # test that invalid colors and erroneous strings raise a ValueError
        with pytest.raises(ValueError):
            Tag("x", c)

    def test_non_string_color_rejected(self):
        # test that colors that are not strings are rejected
        with pytest.raises(TypeError):
            Tag("x", 123456)

    def test_color_setter_validates_format(self):
        # test that the tag setter rejects bad color values
        tag = Tag("x", "#112233")
        with pytest.raises(ValueError):
            tag.color = "#ZZZZZZ"
        assert tag.color == "#112233"

    def test_tag_renames(self):
        # test that tags can be renamed successfully without changing their id
        tag = Tag("x", "#112233")
        pre_change_id = tag.id
        tag.name = "y"
        assert tag.name == "y"
        assert tag.id == pre_change_id

    def test_id_read_only(self):
        # test that an error is raised if an id change is attempted
        tag = Tag("x", "#112233")
        with pytest.raises(AttributeError):
            tag.id = "other"