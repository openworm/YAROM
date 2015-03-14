
class GraphObject(object):
    def identifier(self):
        raise NotImplementedError()

    def defined(self):
        raise NotImplementedError()

    @property
    def idl(self):
        if self.defined:
            return self.identifier
        else:
            return self.variable

    def owner_properties(self):
        raise NotImplementedError()

    def properties(self):
        raise NotImplementedError()

    def __hash__(self):
        raise NotImplementedError()

    def __eq__(self, other):
        if id(self) == id(other):
            return True
        elif isinstance(other, GraphObject):
            return self.idl == other.idl

    def __lt__(self, other):
        if isinstance(other, GraphObject):
            return self.idl < other.idl
        else:
            return id(self) < id(other)
