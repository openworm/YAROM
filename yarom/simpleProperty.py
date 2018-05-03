import logging
import sys
import six

from .variable import Variable
from .graphObject import GraphObjectQuerier
from .propertyMixins import (
    DatatypePropertyMixin,
    ObjectPropertyMixin,
    UnionPropertyMixin)
from .rangedObjects import InRange
from .yProperty import Property
from .propertyValue import PropertyValue
from .mappedProperty import MappedPropertyClass
from .deprecation import deprecated
from random import randint
from lazy_object_proxy import Proxy


L = logging.getLogger(__name__)

__all__ = [
    "SimpleProperty",
    "DatatypeProperty",
    "ObjectProperty",
    "NoRelationshipException"]


class NoRelationshipException(Exception):

    """ Indicates that a Relationship was asked for but one could not be given. """


class SimpleProperty(six.with_metaclass(MappedPropertyClass, Property)):

    """ A property that has one or more links to literals or DataObjects """

    def __init__(self, **kwargs):
        # The 'linkName' must be made up from the class name if one isn't set
        # before initialization (typically in mapper._create_property)
        super(SimpleProperty, self).__init__(**kwargs)
        if not hasattr(self, 'linkName'):
            self.__class__.linkName = self.__class__.__name__ + "property"

        #
        # 'v' holds values that have been set on this SimpleProperty. It acts
        # as a sort of staging area before saving the values to the graph.
        self._v = []

    def has_value(self):
        """ Returns true if the :meth:`set` has been called previously """
        return len(self._v) > 0

    @deprecated('Please use has_value instead.')
    def hasValue(self):
        """ Returns true if the :meth:`set` has been called previously """
        return self.has_value()

    def has_defined_value(self):
        """
        Returns true if this property has a defined value
        """
        for x in self._v:
            if x.defined:
                return True
        return False

    def _get(self):
        """ Get values from a generator """
        for x in self._v:
            yield x

    @property
    def values(self):
        """ Get all values """
        return self._v

    @property
    def defined_values(self):
        """ Get values which are have their defined property set to True """
        return tuple(x for x in self._v if x.defined)

    @deprecated('Please use set instead.')
    def setValue(self, v):
        self.set(v)

    def get(self):
        """ If the ``Property`` has had ``load`` or ``set`` called previously, returns
        the resulting values. Also queries the configured rdf graph for values
        which are set for the ``Property``'s owner.
        """
        v = Variable("var" + str(id(self)))
        self.set(v)
        results = GraphObjectQuerier(v, self.rdf)()
        self.unset(v)
        return results

    def unset(self, v):

        for idx, val in enumerate(self._v):
            if not hasattr(v, 'idl') and isinstance(val, PropertyValue):
                deval = self.resolver.deserializer(val.identifier)
            else:
                deval = val
            if deval == v:
                break
        else: # no break
            raise Exception("Can't find value {}".format(v))
        actual_val = self._v[idx]
        actual_val.owner_properties.remove(self)
        self._v.remove(actual_val)

    def set(self, v):
        if isinstance(v, Rel):
            v = v.rel()

        if isinstance(v, InRange):
            vcname = 'Variable' + v.__class__.__name__
            vclass = v.__class__
            v.__class__ = type(vcname, (vclass, Variable), {})
            Variable.__init__(v, '_' + hex(randint(0, sys.maxsize))[2:])

        if not hasattr(v, "idl"):
            v = PropertyValue(v)

        if not self.multiple:
            self.clear()

        self._insert_value(v)

        return RelationshipProxy(Rel(self.owner, self, v))

    def _remove_value(self, v):
        assert self in v.owner_properties
        v.owner_properties.remove(self)
        self._v.remove(v)

    def clear(self):
        for x in self._v:
            self._remove_value(x)

    def _insert_value(self, v):
        self._v.append(v)
        if self not in v.owner_properties:
            v.owner_properties.append(self)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and (self.link == other.link)

    def __hash__(self):
        return hash(self.link)

    def __str__(self):
        return "{}({})".format(self.linkName,
                               " ".join(repr(x) for x in self._v))

    def __repr__(self):
        return str(self)


class DatatypeProperty(DatatypePropertyMixin, SimpleProperty):
    pass


class ObjectProperty(ObjectPropertyMixin, SimpleProperty):
    pass


class UnionProperty(UnionPropertyMixin, SimpleProperty):

    """ A Property that can handle either DataObjects or basic types """


class RelationshipProxy(Proxy):
    def __repr__(self):
        return repr(self.__wrapped__)

    def in_context(self, context):
        rel = self.__factory__
        rel.p.context = context
        return self

    def unwrapped(self):
        return self.__wrapped__


class Rel(tuple):

    """ A container for a relationship-assignment """
    _map = dict(s=0, p=1, o=2)

    def __new__(cls, s, p, o):
        return super(Rel, cls).__new__(cls, (s, p, o))

    def __getattr__(self, n):
        return self[Rel._map[n]]

    def __call__(self):
        return self.rel()

    def rel(self):
        from .relationship import Relationship
        return Relationship(
            s=(self.s if self.s.defined else None),
            p=self.p.rdf_object,
            o=(self.o if self.o.defined else None))


__yarom_mapped_classes__ = (SimpleProperty, ObjectProperty, DatatypeProperty, UnionProperty)
