import rdflib as R
import logging
import hashlib
import six
import random

from .mapperTypeResolver import Resolver
from .mappedClass import MappedClass
from .mappedProperty import MappedPropertyClass
from .dataUser import DataUser
from .configure import BadConf
from .simpleProperty import (SimpleProperty, DatatypeProperty, ObjectProperty)
from .rdfUtils import triples_to_bgp
from .graphObject import (
    GraphObject,
    GraphObjectQuerier,
    ComponentTripler,
    HeroTripler,
    ReferenceTripler,
    DescendantTripler,
    IdentifierMissingException)

"""
.. autoclass:: DataObject
"""

# NOTE: This module (and all modules containing DataObject sub-types) may
# be reloaded. Objects should not be created in the top-level of this
# module.

L = logging.getLogger(__name__)


def _bnode_to_var(x):
    return "?" + x


def get_hash_function(method_name):
    if method_name == "sha224":
        return hashlib.sha224
    elif method_name == "md5":
        return hashlib.md5
    elif method_name in hashlib.algorithms_available:
        return (lambda data: hashlib.new(method_name, data))


class DataObject(six.with_metaclass(MappedClass, GraphObject, DataUser)):

    """
    An object backed by the database

    Attributes
    -----------
    rdf_type : rdflib.term.URIRef
        The RDF type URI for objects of this type
    rdf_namespace : rdflib.namespace.Namespace
        The rdflib namespace (prefix for URIs) for objects from this class
    properties : list of Property
        Properties belonging to this object
    owner_properties : list of Property
        Properties belonging to parents of this object
    """

    _openSet = set()
    _closedSet = set()

    configuration_variables = {
        "rdf.namespace": {
            "description": "Namespaces for DataObject sub-classes will, by "
            "default, be based off of this. For example, a subclass named A "
            "would have a namespace '[rdf.namespace]A/'",
            "type": R.Namespace,
            "directly_configureable": True},
        "dataObject.identifier_hash": {
            "description": "The hash method used for object identifiers. "
            "Defaults to md5.",
            "type": "sha224, md5, or one of the types accepted by"
            "hashlib.new()",
            "directly_configureable": True},
    }

    @classmethod
    def open_set(self):
        """ The open set contains items that must be saved directly in order for
        their data to be written out
        """
        return self._openSet

    def __init__(
            self,
            ident=False,
            var=False,
            key=False,
            generate_key=False,
            **kwargs):
        """A subclass of DataObject cannot have any required positional arguments.

        Parameters
        ----------
        ident : rdflib.term.URIRef or str
            The identifier for this DataObject
        var : str
            In lieu of `ident`, sets the variable for this object
        key : str or object
            In lieu of `ident` or `var`, sets the identifier for this
            DataObject using the key value. For a namespace `ex:` and key `a`,
            the identifier would be `ex:a`.
        generate_key : bool
            If true generates a random key value
        kwargs : dict
            Values to set for named properties
        """
        try:
            super(DataObject, self).__init__()
        except BadConf as e:
            six.raise_from(
                Exception("You may need to connect to " +
                          "a database before continuing."), e)

        if not self.__class__.mapped:
            raise Exception(
                ("The class `{0}` has not been mapped. You should call "
                 "`{0}.map()` before creating any instances.").format(
                    self.__class__.__name__))

        self._id = False

        if ident:
            if isinstance(ident, R.URIRef):
                self._id = ident
            else:
                self._id = R.URIRef(ident)
        elif var:
            self._id_variable = R.Variable(var)
        # TODO: Support a key function that generates the key based on live
        # values of the object (e.g., property values)
        elif key:
            self.setKey(key)
        elif generate_key:
            self.setKey(random.random())
        else:
            # Randomly generate an identifier if the derived class can't
            # come up with one from the start. Ensures we always have something
            # that functions as an identifier
            v = (random.random(), random.random())
            cname = self.__class__.__name__
            self._id_variable = R.Variable(cname + "_" + hashlib.md5(
                str(v).encode()).hexdigest())

        for x in self.__class__.dataObjectProperties:
            self.attachProperty(x)

        existing_property_names = [x.linkName for x in self.properties]
        for propName in kwargs.keys():
            if propName not in existing_property_names:
                raise ValueError(
                    "No such argument {} to {}::__init__".format(
                        propName,
                        self.__class__.__name__))

        for x in self.properties:
            if x.linkName in kwargs:
                self.relate(x.linkName, kwargs[x.linkName])

        if isinstance(self, PropertyDataObject):
            self.relate(
                'rdf_type_property',
                RDFProperty.getInstance(),
                RDFTypeProperty)
        elif isinstance(self, TypeDataObject):
            self.relate(
                'rdf_type_property',
                RDFSClass.getInstance(),
                RDFTypeProperty)
        elif isinstance(self, RDFProperty):
            self.relate(
                'rdf_type_property',
                RDFSClass.getInstance(),
                RDFTypeProperty)
        elif isinstance(self, RDFSClass):
            self.relate('rdf_type_property', self, RDFTypeProperty)
        else:
            self.relate(
                'rdf_type_property',
                self.rdf_type_object,
                RDFTypeProperty)

    @classmethod
    def identifier_hash_method(self, o):
        return get_hash_function(
            self.conf.get(
                'dataObject.identifier_hash',
                'md5'))(o)

    def set_property_values(self, values):
        for k in six.iterkeys(values.keys):
            o = values[k]
            if o is not None:
                setattr(self, k, o)

    def make_identifier_from_properties(self, *properties):
        if len(properties) == 0:
            raise Exception("No properties provided to make identifier")
        data = ""
        for propName in properties:
            for value in getattr(self, propName).values:
                data += value.idl.n3()
        if len(data) == 0:
            raise Exception("No properties to make identifier")
        return self.make_identifier(data)

    @property
    def defined(self):
        """Returns `True` if this object has an identifier

        To define a custom identifier, override :meth:`defined_augment` to return
        True when your custom identifier would be defined. You must also override
        :meth:`identifier_augment`
        """
        # TODO: Add a check for circular definition of "defined" status by
        #       defined_augment like:
        #
        #           a is defined if b is defined
        #           b is defined if a is defined.
        #
        #       such definitions are legal and if one or the other has its
        #       ident set explicitly, then there would be done unbounded
        #       recursion.
        if self._id:
            return True
        else:
            return self.defined_augment()

    def defined_augment(self):
        """ This fuction must return False if :meth:`identifier_augment` would
        raise an :exc:`~yarom.graphObject.IdentifierMissingException`. Override
        it when defining a non-standard identifier for subclasses of DataObjects.
        """
        return False

    def variable(self):
        """ Returns the variable to be usedin queries with this DataObject

        Raises
        ------

        IdentifierMissingException

        """
        if self._id_variable is not None:
            return self._id_variable
        else:
            raise IdentifierMissingException(self)

    def setKey(self, key):
        if isinstance(key, str):
            self._id = self.make_identifier_direct(key)
        else:
            self._id = self.make_identifier(key)

    def relate(self, linkName, other, prop=False):
        existing_property_names = [x.linkName for x in self.properties]
        if linkName in existing_property_names:
            if prop and not isinstance(getattr(self, linkName), prop):
                L.warning(
                    "A property class, {}, was provided to relate, but it"
                    " will be ignored since there's already a property, {},"
                    " with the given linkName '{}' and it has a different"
                    " class".format(prop, getattr(self, linkName), linkName))
            p = getattr(self, linkName)
        else:
            if not prop:
                # Make up a property class
                property_type = None
                if isinstance(other, DataObject):
                    property_type = ObjectProperty
                else:
                    property_type = DatatypeProperty
                prop = self._create_related_property(linkName, property_type)
            elif not hasattr(prop, 'linkName'):
                prop.linkName = linkName
            p = self.attachProperty(prop)
        return p.set(other)

    def _create_related_property(self, linkName, property_type):
        link = type(self).rdf_namespace[linkName]
        return MappedPropertyClass(
            linkName, (property_type,), dict(
                link=link, linkName=linkName, multiple=True))

    def attachProperty(self, prop):
        if not hasattr(prop, 'linkName'):
            raise Exception("The given property class cannot be attached"
                            " because it has no `linkName` attribute")
        p = prop(resolver=Resolver.get_instance(), owner=self)

        if hasattr(self, prop.linkName):
            raise Exception(
                "Cannot attach property '{}'. A property must have a different \
                        name from any attributes in DataObject".format(
                    prop.linkName))
        self.properties.append(p)
        setattr(self, p.linkName, p)
        return p

    def get_defined_component(self):
        g = ComponentTripler(self, generator=True)()
        if not isinstance(g, R.Graph):
            h = R.Graph()
            for t in g:
                h.add(t)
            g = h
        g.namespace_manager = self.namespace_manager
        return g

    def __eq__(self, other):
        return ((isinstance(other, DataObject) and
                 (self.idl == other.idl)) or
                (isinstance(other, R.URIRef) and
                 (self.idl == other)))

    def __hash__(self):
        return hash(self.idl)

    def __str__(self):
        return self.namespace_manager.normalizeUri(self.idl)

    def __repr__(self):
        return self.__str__()

    @classmethod
    def add_to_open_set(cls, o):
        cls._openSet.add(o)

    @classmethod
    def remove_from_open_set(cls, o):
        if o not in cls._closedSet:
            cls._openSet.remove(o)
            cls._closedSet.add(o)

    @classmethod
    def extract_unique_part(cls, uri):
        if uri.startswith(cls.rdf_namespace):
            return uri[:len(cls.rdf_namespace)]
        else:
            raise Exception(
                "This URI ({}) doesn't start with the appropriate namespace ({})".format(
                    uri,
                    cls.rdf_namespace))

    @classmethod
    def make_identifier(cls, data):
        # NOTE: The "a" prefix allows all identifiers to nicely reduce to
        # abbreviated form in n3
        return R.URIRef(
            cls.rdf_namespace[
                "a" +
                cls.identifier_hash_method(
                    str(data).encode()).hexdigest()])

    @classmethod
    def make_identifier_direct(cls, string):
        if not isinstance(string, str):
            raise Exception("make_identifier_direct only accepts strings")
        from six.moves import urllib
        return R.URIRef(cls.rdf_namespace[urllib.parse.quote(string)])

    def identifier(self):
        """ The identifier for this object in the rdf graph.

        This identifier may be randomly generated, but an identifier returned from the
        graph can be used to retrieve the specific object that it refers to.

        If it is desireable to customize the identifier, a subclass of DataObject should
        override :meth:`identifier_augment` rather than this method.

        Returns
        -------
        :class:`rdflib.term.URIRef`
        """
        if self._id:
            return self._id
        else:
            return self.identifier_augment()

    def identifier_augment(self):
        """ Override this method to define an identifier in lieu of one explicity set.

        One must also override :meth:`defined_augment` to return True whenever
        this method could return a valid identifier.
        :exc:`~yarom.graphObject.IdentifierMissingException` should be
        raised if an identifier cannot be generated by this method.

        Raises
        ------

        IdentifierMissingException

        """
        raise IdentifierMissingException(self)

    def triples(self):
        """ Returns 3-tuples of the connected component of the object graph starting from this object.

        Returns
        --------
        An iterable of triples
        """
        return self.get_defined_component()

    def graph_pattern(self, shorten=False):
        """ Get the graph pattern for this object.

        It should be as simple as converting the result of triples() into a BGP

        Parameters
        ----------
        query : bool
            Indicates whether or not the graph_pattern is to be used for
            querying (as in a SPARQL query) or for storage
        shorten : bool
            Indicates whether to shorten the URLs with the namespace manager
            attached to the ``self``
        """

        nm = None
        if shorten:
            nm = self.namespace_manager
        return triples_to_bgp(
            self.get_defined_component(),
            namespace_manager=nm)

    def load(self):
        for ident in GraphObjectQuerier(self, self.rdf)():
            types = set()
            for rdf_type in self.rdf.objects(ident, R.RDF['type']):
                types.add(rdf_type)
            the_type = self.mapper.get_most_specific_rdf_type(types)
            yield self.mapper.oid(ident, the_type)

    def resolve(self):
        """ Resolve this object from the graph.

        Gets the value for each of the properties attached to this object. In
        contrast to :meth:`load`, this method requires that the object already
        has its identifier.
        """

        for p in self.properties:
            values = set(p.get())
            for v in values:
                p.set(v)

    def save(self):
        """ Write in-memory data to the database. Derived classes should call this to update
        the store.

        Dual to retract.
        """
        self.add_statements(self.get_defined_component())

    def retract(self):
        """ Remove this object from the data store.

        Retract removes an object and everything it points to, transitively, and everything
        which points to it.

        Dual to save.
        """
        self.retract_statements(self.get_defined_component())

    def save_object(self):
        """ Write in-memory data to the database. Derived classes should call this to update
        the store.

        Dual to retract_object.
        """
        self.add_statements(DescendantTripler(self)())

    def retract_object(self):
        """ Remove this object from the data store.

        Retract removes an object and everything it points to, transitively, and everything
        which points to it.

        Dual to save_object.
        """
        self.retract_statements(HeroTripler(self)())

    def retract_objectG(self):
        """ Remove this object from the data store.

        Retract removes an object and everything it points to, transitively, and everything
        which points to it.

        Dual to save_objectG.
        """
        g = HeroTripler(self, self.rdf)()
        self.retract_statements(g)

    def retract_references(self):
        """ Remove all references directly to or made by this object """
        self.retract_statements(ReferenceTripler(self)())

    def retract_referencesG(self):
        """ Remove all references directly to or made by this object """
        self.retract_statements(ReferenceTripler(self, self.rdf)())

    def __getitem__(self, x):
        try:
            return self.conf[x]
        except KeyError:
            raise Exception(
                "You attempted to get the value `{}' from `{}'. It isn't here."
                " Perhaps you misspelled the name of a Property?".format(
                    x, self))

    def get_owners(self, property_name):
        """ Return the owners along a property pointing to this object """
        res = []
        for x in self.owner_properties:
            if isinstance(x, SimpleProperty):
                if str(x.linkName) == str(property_name):
                    res.append(x.owner)
        return res


def validateG(do_type):
    """ Given a DataObject type, call validate() on all objects of that type in the Python object graph """


def validate(do_type):
    """ Given a DataObject type, call validate() on all objects of that type in the RDF object graph """


class TypeDataObject(DataObject):
    pass


class DataObjectSingleton(DataObject):
    instance = None

    def __init__(self, *args, **kwargs):
        if type(self)._gettingInstance:
            super(DataObjectSingleton, self).__init__(*args, **kwargs)
        else:
            raise Exception(
                "You must call getInstance to get " +
                type(self).__name__)

    @classmethod
    def getInstance(cls):
        if cls.instance is None:
            cls._gettingInstance = True
            cls.instance = cls()
            cls._gettingInstance = False

        return cls.instance


class RDFSClass(DataObjectSingleton):  # This maybe becomes a DataObject later

    """ The DataObject corresponding to rdfs:Class """
    # XXX: This class may be changed from a singleton later to facilitate dumping
    #      and reloading the object graph
    rdf_type = R.RDFS['Class']
    auto_mapped = True

    def __init__(self):
        super(RDFSClass, self).__init__(R.RDFS["Class"])


class RDFProperty(DataObjectSingleton):

    """ The DataObject corresponding to rdf:Property """
    rdf_type = R.RDF['Property']

    def __init__(self):
        super(RDFProperty, self).__init__(R.RDF["Property"])


class RDFTypeProperty(ObjectProperty):
    link = R.RDF['type']
    linkName = "rdf_type_property"
    owner_type = DataObject
    value_type = RDFSClass
    multiple = True


class RDFSSubClassOfProperty(ObjectProperty):
    link = R.RDFS['subClassOf']
    linkName = "rdfs_subClassOf"
    owner_type = RDFSClass
    value_type = RDFSClass
    multiple = True


class PropertyDataObject(DataObject):

    """ A PropertyDataObject represents the property-as-object.

    Try not to confuse this with the Property class
    """


class RDFSDomainProperty(ObjectProperty):
    link = R.RDFS['domain']
    linkName = "rdfs_domain"
    owner_type = RDFProperty
    value_type = RDFSClass
    multiple = True


class RDFSRangeProperty(ObjectProperty):
    link = R.RDFS['range']
    linkName = "rdfs_range"
    owner_type = RDFProperty
    value_type = RDFSClass
    multiple = True
