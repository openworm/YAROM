import rdflib
from .graphObject import GraphObject, IdentifierMissingException

class Variable(GraphObject):
    def __init__(self, name):
        GraphObject.__init__(self)
        self.var = rdflib.Variable(name)

    def identifier(self):
        raise IdentifierMissingException(self)

    def variable(self):
        return self.var

    @property
    def defined(self):
        return False

    def __hash__(self):
        return hash(self.var)

    def __str__(self):
        return str(self.var)

    def __repr__(self):
        return "Variable('"+str(self)+"')"
