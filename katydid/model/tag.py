import uuid
import string

class Tag:
    def __init__(self, name, color, id=None):
        self._id = id if id is not None else uuid.uuid4().hex
        self.name = name
        self.color = color

    @property
    def id(self):
        return self._id
    
    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name):
        self._name = new_name

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, new_color):
        self.validate_color(new_color)
        self._color = new_color

    @staticmethod
    def validate_color(color):
        if not all(c in string.hexdigits for c in color[1:]) or len(color) != 7 or color[0] != "#":
            raise ValueError("Color string incorrect format")

    def __repr__(self):
        return f"Tag(id='{self.id}', name='{self.name}', color='{self.color}')"