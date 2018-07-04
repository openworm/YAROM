from .mapper import FCN
from .rdfUtils import DOWN


class ZeroOrMore(object):
    def __init__(self, identifier, predicate, direction=DOWN):
        self.identifier = identifier
        self.predicate = predicate
        self.direction = direction

    def __repr__(self):
        return "{}({}, {}, {})".format(FCN(type(self)),
                                       repr(self.identifier),
                                       repr(self.predicate),
                                       repr(self.direction))
