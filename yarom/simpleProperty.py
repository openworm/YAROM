import rdflib
import logging
import hashlib
import six

from .variable import Variable
from .graphObject import GraphObjectQuerier
from .rdfUtils import deserialize_rdflib_term
from .yProperty import Property
from .propertyValue import PropertyValue
from .mapper import MappedPropertyClass
from random import random

L = logging.getLogger(__name__)

__all__ = ["SimpleProperty", "DatatypeProperty", "ObjectProperty", "NoRelationshipException"]

class NoRelationshipException(Exception):

    """ Indicates that a Relationship was asked for but one could not be given. """

class SimpleProperty(six.with_metaclass(MappedPropertyClass, Property)):
    """ A property that has one or more links to literals or DataObjects """

    def __init__(self,**kwargs):
        # The 'linkName' must be made up from the class name if one isn't set
        # before initialization (typically in mapper._create_property)
        super(SimpleProperty, self).__init__(**kwargs)
        if not hasattr(self, 'linkName'):
            self.__class__.linkName = self.__class__.__name__ + "property"

        #
        # 'v' holds values that have been set on this SimpleProperty. It acts
        # as a sort of staging area before saving the values to the graph.
        self._v = []

        v = (random(), random())
        self._value = Variable("_" + hashlib.md5(str(v).encode()).hexdigest())

    def hasValue(self):
        """ Returns true if the :meth:`set` has been called previously """
        return len(self._v) > 0

    def _get(self):
        for x in self._v:
            yield x

    @property
    def values(self):
        return self._v

    def setValue(self, v):
        self.set(v)

    def get(self):
        """ If the ``Property`` has had ``load`` or ``set`` called previously, returns
        the resulting values. Also queries the configured rdf graph for values
        which are set for the ``Property``'s owner.
        """
        v = Variable("var"+str(id(self)))
        self.set(v)
        results = GraphObjectQuerier(v, self.rdf)()
        self.unset(v)
        return results

    def unset(self, v):
        idx = self._v.index(v)
        if idx >= 0:
            actual_val = self._v[idx]
            actual_val.owner_properties.remove(self)
            self._v.remove(actual_val)
        else:
            raise Exception("Can't find value {}".format(v))

    def set(self,v):
        import bisect
        if isinstance(v, Rel):
            v = v.rel()

        if not hasattr(v, "idl"):
            v = PropertyValue(v)

        if self not in v.owner_properties:
            v.owner_properties.append(self)

        if self.multiple:
            bisect.insort(self._v, v)
        else:
            self._v = [v]
        return Rel(self.owner, self, v)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.link == other.link

    def __hash__(self):
        return hash(self.link)

    def __str__(self):
        return str(self.linkName + "(" + str(" ".join(repr(x) for x in self._v)) + ")")

    def __repr__(self):
        return str(self)

class DatatypeProperty(SimpleProperty):
    def set(self, v):
        from .dataObject import DataObject
        if isinstance(v, DataObject):
            L.warn('You are attempting to set a DataObject where a literal is expected.')
        return SimpleProperty.set(self,v)

    def get(self):
        for val in SimpleProperty.get(self):
            yield deserialize_rdflib_term(val)

class ObjectProperty(SimpleProperty):
    def set(self, v):
        from .dataObject import DataObject
        if not isinstance(v, (DataObject, Variable)):
            raise Exception("An ObjectProperty only accepts DataObject or Variable instances. Got a "+str(type(v)))
        return SimpleProperty.set(self, v)

    def get(self):
        from .dataObject import DataObject
        from .mapper import oid,get_most_specific_rdf_type

        for ident in SimpleProperty.get(self):
            if not isinstance(ident, rdflib.URIRef):
                L.warn('ObjectProperty.get: Skipping non-URI term, "'+ident+'", returned for a data object.')
                continue
            types = set()
            for rdf_type in self.rdf.objects(ident, rdflib.RDF['type']):
                types.add(rdf_type)

            if len(types) == 0:
                L.warn('ObjectProperty.get: Retrieved un-typed URI, "'+ident+'", for a DataObject. Creating a default-typed object')
                the_type = DataObject.rdf_type
            else:
                the_type = get_most_specific_rdf_type(types)

            yield oid(ident, the_type)

class UnionProperty(SimpleProperty):
    """ A Property that can handle either DataObjects or basic types """
    def set(self, v):
        return SimpleProperty.set(self, v)

    def get(self):
        from .dataObject import DataObject
        from .mapper import oid,get_most_specific_rdf_type

        for ident in SimpleProperty.get(self):
            if isinstance(ident, rdflib.Literal):
                yield deserialize_rdflib_term(ident)
            elif isinstance(ident, rdflib.BNode):
                L.warn('UnionProperty.get: Retrieved BNode, "'+ident+'". BNodes are not supported in yarom')
            else:
                types = set()
                for rdf_type in self.rdf.objects(ident, rdflib.RDF['type']):
                    types.add(rdf_type)
                L.debug("{} <- types, {} <- ident".format(types,ident))
                the_type = DataObject.rdf_type
                if len(types) == 0:
                    L.warn('UnionProperty.get: Retrieved un-typed URI, "'+ident+'", for a DataObject. Creating a default-typed object')
                else:
                    try:
                        the_type = get_most_specific_rdf_type(types)
                        L.debug("the_type = {}".format(the_type))
                    except:
                        L.warn('UnionProperty.get: Couldn\'t resolve types for `{}\'. Defaulting to a DataObject typed object'.format(ident))

                yield oid(ident, the_type)

class Rel(tuple):
    """ A container for a relationship-assignment """
    _map=dict(s=0,p=1,o=2)
    def __new__(cls, s, p, o):
        return super(Rel, cls).__new__(cls, (s,p,o))

    def __getattr__(self, n):
        return self[Rel._map[n]]

    def rel(self):
        from .relationship import Relationship
        return Relationship(subject=self.s, property=self.p.rdf_object, object=self.o)
