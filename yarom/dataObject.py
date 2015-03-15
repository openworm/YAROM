import rdflib as R
import traceback
import logging as L
import hashlib
import random
from .mapper import *
from .dataUser import DataUser
from .yProperty import SimpleProperty
from .rdfUtils import *
from .graphObject import *

# in general it should be possible to recover the entire object from its identifier: the object should be representable as a connected graph.
# However, this need not be a connected *RDF* graph. Indeed, graph literals may hold information which can yield triples which are not
# connected by an actual node

def _bnode_to_var(x):
    return "?" + x


class IdentifierMissingException(Exception):
    """ Indicates that an identifier should be set available for the object in question, but there is none """
    def __init__(self, dataObject="[unspecified object]", query=False, *args, **kwargs):
        mode = "query mode" if query else "non-query mode"
        super().__init__("An identifier should be provided for {} when used in {}".format(str(dataObject), mode), *args, **kwargs)

def get_hash_function(method_name):
    if method_name == "sha224":
        return hashlib.sha224
    elif method_name == "md5":
        return hashlib.md5
    elif method_name in hashlib.algorithms_available:
        return (lambda data: hashlib.new(method_name, data))

class DataObject(DataUser, metaclass=MappedClass):
    """ An object backed by the database

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
    i = 0

    configuration_variables = {
            "rdf.namespace" : {
                "description" : "Namespaces for DataObject sub-classes will be based off of this. For example, a subclass named A would have a namespace '[rdf.namespace]A/'",
                "type" : R.Namespace,
                "directly_configureable" : True
                },
            "dataObject.identifier_hash" : {
                "description" : "The hash method used for object identifiers. Defaults to md5.",
                "type" : "sha224, md5, or one of the types accepted by hashlib.new()",
                "directly_configureable" : True
                },
            }

    @classmethod
    def openSet(self):
        """ The open set contains items that must be saved directly in order for their data to be written out """
        return self._openSet

    def __init__(self,ident=False,var=False,triples=False,key=False,generate_key=False,**kwargs):
        try:
            DataUser.__init__(self,**kwargs)
        except BadConf as e:
            raise Exception("You may need to connect to a database before continuing.")

        if not triples:
            self._triples = []
        else:
            self._triples = triples

        self.properties = []
        self.owner_properties = []
        self._id = False
        if ident:
            if isinstance(ident, R.URIRef):
                self._id = ident
            else:
                self._id = R.URIRef(ident)
        elif var:
            self._id_variable = R.Variable(var)
        elif key: # TODO: Support a key function that generates the key based on live values of the object (e.g., property values)
            self.setKey(key)
        elif generate_key:
            self.setKey(random.random())
        else:
            # Randomly generate an identifier if the derived class can't
            # come up with one from the start. Ensures we always have something
            # that functions as an identifier
            v = (random.random(), random.random())
            cname = self.__class__.__name__
            self._id_variable = self._graph_variable(cname + "_" + hashlib.md5(str(v).encode()).hexdigest())

        for x in self.__class__.dataObjectProperties:
            prop = x(owner=self)
            self.properties.append(prop)
            if hasattr(self, prop.linkName):
                raise Exception("Cannot attach property '{}'. A property must have a different name from any attributes in DataObject".format(prop.linkName))
            setattr(self, prop.linkName, prop)

        for x in self.properties:
            if x.linkName in kwargs:
                self.relate(x.linkName, kwargs[x.linkName])

        if isinstance(self, DataObjectProperty):
            self.relate('rdf_type_property', RDFProperty.getInstance(), RDFTypeProperty)
        elif isinstance(self, DataObjectType):
            self.relate('rdf_type_property', RDFSClass.getInstance(), RDFTypeProperty)
        elif isinstance(self, RDFProperty):
            self.relate('rdf_type_property', RDFSClass.getInstance(), RDFTypeProperty)
        elif isinstance(self, RDFSClass):
            self.relate('rdf_type_property', self, RDFTypeProperty)
        else:
            self.relate('rdf_type_property', self.rdf_type_object, RDFTypeProperty)

    @classmethod
    def identifier_hash_method(self, o):
        return get_hash_function(self.conf.get('dataObject.identifier_hash', 'md5'))(o)

    @property
    def _id_is_set(self):
        """ Indicates whether the identifier will return a URI appropriate for use by YAROM

        Sub-classes should not override this method.
        """
        return self._id != False

    @property
    def defined(self):
        return self._id != False

    @property
    def idl(self):
        if self._id:
            return self._id
        else:
            return self._id_variable

    def setKey(self, key):
        if isinstance(key, str):
            self._id = self.make_identifier_direct(key)
        else:
            self._id = self.make_identifier(key)

    def relate(self, linkName, other, prop=False):
        cls = type(self)

        existing_property_names = [x.linkName for x in self.properties]
        if linkName in existing_property_names:
            p = getattr(self, linkName)
        else:
            if not prop:
                if isinstance(other, DataObject):
                    prop = makeObjectProperty(cls, linkName, value_type=type(other), multiple=True)
                else:
                    prop = makeDatatypeProperty(cls, linkName, multiple=True)
            p = prop(owner=self)
            self.properties.append(p)
            setattr(self, linkName, p)
        p.set(other)

    def get_defined_component(self):
        g = SV()(self)
        g.namespace_manager = self.namespace_manager
        return g

    def __eq__(self,other):
        return isinstance(other,DataObject) and (self.idl == other.idl)

    def __hash__(self):
        return hash(self.idl)

    def __lt__(self, other):
        return hash(self.identifier()) < hash(other.identifier())

    def __str__(self):
        return self.namespace_manager.normalizeUri(self.idl)

    def __repr__(self):
        return self.__str__()

    def _graph_variable(self,var_name):
        return R.Variable(var_name)

    @classmethod
    def object_from_id(cls,*args,**kwargs):
        return cls.oid(*args,**kwargs)

    @classmethod
    def addToOpenSet(cls,o):
        cls._openSet.add(o)

    @classmethod
    def removeFromOpenSet(cls,o):
        if o not in cls._closedSet:
            cls._openSet.remove(o)
            cls._closedSet.add(o)

    @classmethod
    def oid(cls, identifier, rdf_type=False):
        """ Load an object from the database using its type tag """
        # XXX: This is a class method because we need to get the conf
        # We should be able to extract the type from the identifier
        if rdf_type:
            uri = rdf_type
        else:
            uri = identifier

        cn = cls.extract_class_name(uri)
        # if its our class name, then make our own object
        # if there's a part after that, that's the property name
        o = DataObjects[cn](ident=identifier)
        return o

    @classmethod
    def extract_class_name(cls, uri):
        ns = str(cls.conf['rdf.namespace'])
        if uri.startswith(ns):
            class_name = uri[len(ns):]
            name_end_idx = class_name.find('/')
            if name_end_idx > 0:
                class_name = class_name[:name_end_idx]
            return class_name
        else:
            raise ValueError("URI must be like '"+ns+"<className>' optionally followed by a hash code")
    @classmethod
    def extract_unique_part(cls, uri):
        if uri.startswith(cls.rdf_namespace):
            return uri[:len(cls.rdf_namespace)]
        else:
            raise Exception("This URI ({}) doesn't start with the appropriate namespace ({})".format(uri, cls.rdf_namespace))

    @classmethod
    def _graph_variable_to_var(cls, uri):
        return uri

    @classmethod
    def make_identifier(cls, data):
        return R.URIRef(cls.rdf_namespace["a"+cls.identifier_hash_method(str(data).encode()).hexdigest()])

    @classmethod
    def make_identifier_direct(cls, string):
        if not isinstance(string, str):
            raise Exception("make_identifier_direct only accepts strings")
        from urllib.parse import quote
        return R.URIRef(cls.rdf_namespace[quote(string)])

    def identifier(self, query=False):
        """
        The identifier for this object in the rdf graph.

        This identifier may be randomly generated, but an identifier returned from the
        graph can be used to retrieve the specific object that it refers to.

        Sub-classes of DataObject may override this to construct identifiers based
        on some other key.
        """
        if query and not self._id_is_set:
            return self._id_variable
        elif self._id_is_set:
            return self._id
        else:
            # XXX: Make no mistake: not having an identifier here is an error.
            # You may, however, need to sub-class DataObject to make an
            # appropriate identifier method.
            raise IdentifierMissingException(self.__class__, query)

    def triples(self, query=False, visited_list=False):
        """
        Should be overridden by derived classes to return appropriate triples

        Returns
        --------
        An iterable of triples
        """
        return self.get_defined_component()

    def graph_pattern(self, query=False, shorten=False):
        """ Get the graph pattern for this object.

        It should be as simple as converting the result of triples() into a BGP

        Parameters
        ----------
        query : bool
            Indicates whether or not the graph_pattern is to be used for querying
            (as in a SPARQL query) or for storage
        shorten : bool
            Indicates whether to shorten the URLs with the namespace manager
            attached to the ``self``
        """

        nm = None
        if shorten:
            nm = self.namespace_manager
        return triples_to_bgp(self.get_defined_component(), namespace_manager=nm)

    def save(self):
        """ Write in-memory data to the database. Derived classes should call this to update the store. """
        self.add_statements(self.get_defined_component())

    def load(self):
        """ Load in data from the database. Derived classes should override this for their own data structures.

        ``load()`` returns an iterable object which yields DataObjects which have the same class as the object and have, for the Properties set, the same values

        :param self: An object which limits the set of objects which can be returned. Should have the configuration necessary to do the query
        """
        if not DataObject._is_variable(self.identifier(query=True)):
            yield self
        else:
            gp = self.graph_pattern(query=True)
            ident = self.identifier(query=True)
            q = "SELECT DISTINCT {0} where {{ {1} }}".format(ident.n3(), gp)
            qres = self.rdf.query(q)
            for g in qres:
                new_ident = g[0]
                new_object = self.object_from_id(new_ident)
                yield new_object

    def load2(self):
        for ident in GraphObjectQuerier(self)():
            types = set()
            for rdf_type in self.rdf.objects(ident, R.RDF['type']):
                types.add(rdf_type)
            the_type = get_most_specific_rdf_type(types)
            yield oid2(ident, the_type)

    def retract(self):
        """ Remove this object from the data store.

        Retract removes an object and everything it points to, transitively,
        which doesn't have pointers to it by something else.
        """
        self.retract_statements(self.get_defined_component())

    def __getitem__(self, x):
        try:
            return DataUser.__getitem__(self, x)
        except KeyError:
            raise Exception("You attempted to get the value `%s' from `%s'. It isn't here. Perhaps you misspelled the name of a Property?" % (x, self))

    def getOwners(self, property_name):
        """ Return the owners along a property pointing to this object """
        res = []
        for x in self.owner_properties:
            if isinstance(x, SimpleProperty):
                if str(x.linkName) == str(property_name):
                    res.append(x.owner)
        return res

class DataObjectType(DataObject): # This maybe becomes a DataObject later
    pass

class RDFSClass(DataObject): # This maybe becomes a DataObject later
    instance = None
    def __init__(self):
        DataObject.__init__(self, R.RDFS["Class"])

    @classmethod
    def getInstance(cls):
        if cls.instance is None:
            cls.instance = RDFSClass()
        return cls.instance

class RDFTypeProperty(SimpleProperty):
    link = R.RDF['type']
    linkName = "rdf_type"
    property_type = 'ObjectProperty'
    owner_type = DataObject
    multiple = True

class RDFSSubClassOfProperty(SimpleProperty):
    link = R.RDFS['subClassOf']
    linkName = "rdfs_subClassOf"
    property_type = 'ObjectProperty'
    owner_type = RDFSClass
    multiple = True

class DataObjectProperty(DataObjectType):
    """ An represents the property-as-object.

    Try not to confuse this with the Property class
    """

class RDFProperty(DataObject):
    """ An RDFProperty represents the property-as-object.

    Try not to confuse this with the Property class
    """
    instance = None
    def __init__(self):
        DataObject.__init__(self, R.RDF["Property"])

    @classmethod
    def getInstance(cls):
        if cls.instance is None:
            cls.instance = RDFProperty()
        return cls.instance

class ObjectCollection(DataObject):
    """
    A convenience class for working with a collection of objects

    Example::

        v = values('unc-13 neurons and muscles')
        n = P.Neuron()
        m = P.Muscle()
        n.receptor('UNC-13')
        m.receptor('UNC-13')
        for x in n.load():
            v.value(x)
        for x in m.load():
            v.value(x)
        # Save the group for later use
        v.save()
        ...
        # get the list back
        u = values('unc-13 neurons and muscles')
        nm = list(u.value())


    Parameters
    ----------
    group_name : string
        A name of the group of objects

    Attributes
    ----------
    name : DatatypeProperty
        The name of the group of objects
    group_name : DataObject
        an alias for ``name``
    value : ObjectProperty
        An object in the group
    add : ObjectProperty
        an alias for ``value``

    """
    objectProperties = ['member']
    datatypeProperties = ['name']
    def __init__(self,group_name,**kwargs):
        DataObject.__init__(self,key=group_name,**kwargs)
        self.add = self.member
        self.group_name = self.name
        self.name(group_name)

    def identifier(self, query=False):
        return self.make_identifier(self.group_name)

