from .dataUser import DataUser
from .rdfUtils import *
from .variable import Variable
from .graphObject import *
from random import random
import rdflib
import logging
import hashlib

L = logging.getLogger(__name__)

# Define a property by writing the get
class Property(DataUser):
    """ Store a value associated with a DataObject

    Properties can be be accessed like methods. A method call like::

        a.P()

    for a property ``P`` will return values appropriate to that property for ``a``,
    the `owner` of the property.

    Parameters
    ----------
    owner : yarom.dataObject.DataObject
        The owner of this property
    name : string
        The name of this property. Can be accessed as an attribute like::

            owner.name

    """

    # Indicates whether the Property is multi-valued
    multiple = False

    def __init__(self, name=False, owner=False, **kwargs):
        DataUser.__init__(self, **kwargs)
        self.owner = owner
        # XXX: Default implementation is a box for a value
        self._value = False

    def get(self,*args):
        """ Get the things which are on the other side of this property

        The return value must be iterable. For a ``get`` that just returns
        a single value, an easy way to make an iterable is to wrap the
        value in a tuple like ``(value,)``.

        Derived classes must override.
        """
        # This should run a query or return a cached value
        raise NotImplementedError()

    def set(self,*args,**kwargs):
        """ Set the value of this property

        Derived classes must override.
        """
        # This should set some values and call DataObject.save()
        raise NotImplementedError()

    def one(self):
        """ Returns a single value for the ``Property`` whether or not it is multivalued.
        """

        try:
            r = self.get()
            return next(iter(r))
        except StopIteration:
            return None

    def hasValue(self):
        """ Returns true if the Property has any values set on it.

        This may be defined differently for each property
        """
        return True

    def __call__(self,*args,**kwargs):
        """ If arguments are passed to the ``Property``, its ``set`` method
        is called. Otherwise, the ``get`` method is called. If the ``multiple``
        member for the ``Property`` is set to ``True``, then a Python set containing
        the associated values is returned. Otherwise, a single bare value is returned.
        """

        if len(args) > 0 or len(kwargs) > 0:
            self.set(*args,**kwargs)
            return self
        else:
            r = self.get(*args,**kwargs)
            if self.multiple:
                return set(r)
            else:
                try:
                    return next(iter(r))
                except StopIteration:
                    return None

    # Get the property (a relationship) itself

class SimpleProperty(Property):
    """ A property that has one or more links to literals or DataObjects """

    def __init__(self,**kwargs):

        # The 'linkName' must be made up from the class name if one isn't set
        # before initialization (typically in mapper._create_property)
        if not hasattr(self, 'linkName'):
            self.__class__.linkName = self.__class__.__name__ + "property"

        Property.__init__(self, name=self.linkName, **kwargs)
        #
        # 'v' holds values that have been set on this SimpleProperty. It acts
        # as a sort of staging area before saving the values to the graph.
        self._v = []

        v = (random(), random())
        self._value = Variable("_" + hashlib.md5(str(v).encode()).hexdigest())

    def hasValue(self):
        """ Returns true if the ``Property`` has had ``load`` called previously and some value was available or if ``set`` has been called previously """
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
        v.owner_properties.append(self)

        if self.multiple:
            bisect.insort(self._v, v)
        else:
            self._v = [v]

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
        if not hasattr(v, "idl"):
            v = PropertyValue(v)
        return super().set(v)

    def get(self):
        for val in super().get():
            yield deserialize_rdflib_term(val)

class ObjectProperty(SimpleProperty):
    def set(self, v):
        from .dataObject import DataObject
        if not isinstance(v, (DataObject, Variable)):
            raise Exception("An ObjectProperty only accepts DataObject instances")
        return super().set(v)

    def get(self):
        from .mapper import oid,get_most_specific_rdf_type

        for ident in super().get():
            if not isinstance(ident, rdflib.URIRef):
                L.warn('ObjectProperty.get: Skipping non-URI term, "'+ident+'", returned for a data object.')
                continue
            types = set()
            for rdf_type in self.rdf.objects(ident, R.RDF['type']):
                types.add(rdf_type)
            if len(types) == 0:
                L.warn('ObjectProperty.get: Retrieved untypped URI, "'+ident+'", for a DataObject. Creating a default-typed object')
                the_type = DataObject.rdf_type
            else:
                the_type = get_most_specific_rdf_type(types)

            yield oid(ident, the_type)

class PropertyValue(GraphObject):
    """ Holds a literal value for a property """
    def __init__(self, value=None):
        self.value = R.Literal(value)
        self.owner_properties = []
        self.properties = []

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
        return "<" + str(self.value) + ">"

    def __repr__(self):
        return str(self)

    def __lt__(self, other):
        return self.value < other.value

    def __eq__(self, other):
        if id(self) == id(other):
            return True
        elif isinstance(other, PropertyValue):
            return self.value == other.value
        else:
            return self.value == R.Literal(other)
