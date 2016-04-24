import rdflib
import six
from .graphObject import GraphObject


class PropertyValue(GraphObject):
    """ Holds a literal value for a property """
    def __init__(self, value):
        super(PropertyValue, self).__init__()
        if not isinstance(value, rdflib.term.Identifier):
            self.value = rdflib.Literal(value)
        else:
            self.value = value

    def triples(self, *args, **kwargs):
        return []

    def identifier(self):
        return self.value

    @property
    def defined(self):
        return True

    @property
    def idl(self):
        return self.identifier()

    def __hash__(self):
        return hash(self.value)

    def __str__(self):
        if six.PY3:
            return self.value
        else:
            return self.value.encode('UTF-8')

    def __repr__(self):
        return repr(self.value)

    def __lt__(self, other):
        return self.value < other.value

    def __eq__(self, other):
        if id(self) == id(other):
            return True
        elif isinstance(other, PropertyValue):
            return self.value == other.value
        else:
            return self.value == rdflib.Literal(other)
