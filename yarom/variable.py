import rdflib
from .graphObject import GraphObject

class Variable(GraphObject):
    def __init__(self, name):
        GraphObject.__init__(self)
        self.variable = rdflib.Variable(name)
        self.properties = []
        self.owner_properties = []

    def identifier(self, *args, **kwargs):
        return self.var

    @property
    def defined(self):
        return False

    def __hash__(self):
        return hash(self.variable)

    def __str__(self):
        return str(self.variable)

    def __repr__(self):
        return str(self)
