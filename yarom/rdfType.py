import rdflib as R

class RDFType(object): # This maybe becomes a DataObject later
    def __init__(self, type_uri):
        self.uri = R.URIRef(type_uri)
        self.owner_properties = list() # A list of DataObjects of this type

    def identifier(self, *args, **kwargs):
        return self.uri

    @property
    def defined(self):
        return True

    @property
    def idl(self):
        return self.uri

    @property
    def p(self):
        return self.owner_properties

    @property
    def o(self):
        return []

    def triples(self, *args, **kwargs):
        return []

    def __hash__(self):
        return hash(self.uri)

    def __str__(self):
        return str(self.uri)

    def __repr__(self):
        return str(self)

    def __lt__(self, other):
        return self.uri < other.uri #XXX define by class relationship?

