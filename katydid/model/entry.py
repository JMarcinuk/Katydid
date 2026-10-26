import uuid
import datetime
from PySide6.QtGui import QTextDocument

class Entry:
    def __init__(self, title, id=None, created=None, modified=None, body="", tag_ids=None):
        self.title = title
        self._id = id if id is not None else uuid.uuid4().hex

        self.body = body
        # if a tag_id list exists already, load it. otherwise, make an empty one
        self.tag_ids = tag_ids if tag_ids is not None else set()
        # generate timestamps at time of creation
        creation_time = datetime.datetime.now()

        # to prevent re-stamping every entry every time it's loaded, check for existing stamps
        self._created = created if created is not None else creation_time
        self._modified = modified if modified is not None else creation_time

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
            raise ValueError("Entry title is too long.")
        self._title = new_title
            
    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, content):
        if not isinstance(content, str):
            raise TypeError("Incorrect type in entry body")
        self._body = content

    @property
    def tag_ids(self):
        return self._tag_ids

    @tag_ids.setter
    def tag_ids(self, tags):
        self._tag_ids = set(tags)

    @property
    def created(self):
        return self._created

    @property
    def modified(self):
        return self._modified

    @staticmethod
    def markdown_to_plain_text(markdown):
        md_doc = QTextDocument()
        md_doc.setMarkdown(markdown)
        return md_doc.toPlainText()

    def length(self):
        plain_text = self.markdown_to_plain_text(self.body)
        return len(plain_text)

    def is_valid(self, char_limit):
        return char_limit is None or self.length() <= char_limit

    # the only way to update modified
    def touch(self):
        self._modified = datetime.datetime.now()

    def __repr__(self):
            return f"Entry(id='{self.id}', title='{self.title}')"