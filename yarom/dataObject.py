import rdflib as R
import traceback
import logging as L
import hashlib
from .mapper import *
from .dataUser import DataUser

# in general it should be possible to recover the entire object from its identifier: the object should be representable as a connected graph.
# However, this need not be a connected *RDF* graph. Indeed, graph literals may hold information which can yield triples which are not
# connected by an actual node

def _bnode_to_var(x):
    return "?" + x

def _serialize_rdflib_term(x, namespace_manager=None):
    if isinstance(x, R.BNode):
        return _bnode_to_var(x)
    elif isinstance(x, R.URIRef) and DataObject._is_variable(x):
        return DataObject._graph_variable_to_var(x)
    else:
        return x.n3(namespace_manager)

def triples_to_bgp(trips, namespace_manager=None):
    # XXX: Collisions could result between the variable names of different objects
    g = " .\n".join(" ".join(_serialize_rdflib_term(x, namespace_manager) for x in y) for y in trips)
    return g

# We keep a little tree of properties in here

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
        Properties

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

    identifier_hash_method = get_hash_function(DataUser.conf.get('dataObject.identifier_hash', 'md5'))

    @classmethod
    def openSet(self):
        """ The open set contains items that must be saved directly in order for their data to be written out """
        return self._openSet

    def __init__(self,ident=False,triples=False,key=False,**kwargs):
        if not triples:
            self._triples = []
        else:
            self._triples = triples

        self.properties = []
        for x in self.__class__.dataObjectProperties:
            self.properties.append(x(owner=self))

        if ident:
            self._id = R.URIRef(ident)
        elif key:
            self._id = self.make_identifier(key)
        else:
            # Randomly generate an identifier if the derived class can't
            # come up with one from the start. Ensures we always have something
            # that functions as an identifier
            import random
            v = (random.random(), random.random())
            cname = self.__class__.__name__
            self._id_variable = self._graph_variable(cname + "_" + hashlib.md5(str(v).encode()).hexdigest())

    @property
    def _id_is_set(self):
        """ Indicates whether the identifier will return a URI appropriate for use by YAROM

        Sub-classes should not override this method.
        """
        return hasattr(self,"_id")

    def __eq__(self,other):
        return isinstance(other,DataObject) and (self.identifier() == other.identifier())

    def __hash__(self):
        return hash(self.identifier())

    def __lt__(self, other):
        return hash(self.identifier()) < hash(other.identifier())

    def __str__(self):
        seen = set()
        def helper():
            s = self.__class__.__name__ + "("
            l = []
            for x in self.properties:
                if x.hasValue() and (x not in seen):
                    seen.add(x)
                    l.append(str(x))
                else:
                    l.append("...")
            s +=  ", ".join(l)
            s += ")"
            return s
        return helper()

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
    def _is_variable(cls, uri):
        """ Is the uriref a graph variable? """
        if isinstance(uri, R.Variable):
            return True
        from urllib.parse import urlparse
        u = urlparse(uri)
        x = u.path.split('/')
        return len(x) >= 3 and (x[2] == 'variable')

    @classmethod
    def _graph_variable_to_var(cls, uri):
        return uri

    @classmethod
    def make_identifier(cls, data):
        return R.URIRef(cls.rdf_namespace["a"+cls.identifier_hash_method(str(data).encode()).hexdigest()])

    def identifier(self,query=False):
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
        """ Should be overridden by derived classes to return appropriate triples

        Returns
        --------
        An iterable of triples
        """
        if visited_list == False:
            visited_list = set()

        if self.identifier(query=query) in visited_list:
            return
        else:
            visited_list.add(self.identifier(query=query))

        ident = self.identifier(query=query)
        yield (ident, R.RDF['type'], self.rdf_type)

        # For objects that are defined by triples, we can just release these.
        # However, they are still data objects, so they must have the above
        # triples released as well.
        for x in self._triples:
            yield x

        # Properties (of type Property) can be attached to an object
        # However, we won't require that there even is a property list in this
        # case.
        if hasattr(self, 'properties'):
            for x in self.properties:
                if x.hasValue():
                    yield (ident, x.link, x.identifier(query=query))
                    for y in x.triples(query=query, visited_list=visited_list):
                        yield y

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
        return triples_to_bgp(self.triples(query=query), namespace_manager=nm)

    def save(self):
        """ Write in-memory data to the database. Derived classes should call this to update the store. """

        ss = set()

        try:
            self.add_statements(self.triples(visited_list=ss))
        except IdentifierMissingException as e:
            Exception("You are attempting to save unresolved values "+str(e))

    @classmethod
    def _extract_property_name(self,uri):
        from urllib.parse import urlparse
        u = urlparse(uri)
        x = u.path.split('/')
        if len(x) >= 4 and x[1] == 'entities':
            return x[3]

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
            q = "SELECT DISTINCT {0} where {{ {1} .}}".format(ident.n3(), gp)
            qres = self.rdf.query(q)
            for g in qres:
                new_ident = g[0]
                new_object = self.object_from_id(new_ident)
                yield new_object

    def retract(self):
        """ Remove this object from the data store. """
        self.retract_statements(self.graph_pattern(query=True))

    def __getitem__(self, x):
        try:
            return DataUser.__getitem__(self, x)
        except KeyError:
            raise Exception("You attempted to get the value `%s' from `%s'. It isn't here. Perhaps you misspelled the name of a Property?" % (x, self))

# Define a property by writing the get
class Property(DataObject):
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
        DataObject.__init__(self, **kwargs)
        self.owner = owner
        if self.owner:
            if name:
                setattr(self.owner, name, self)
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
        if not hasattr(self,'linkName'):
            self.__class__.linkName = self.__class__.__name__ + "property"
        Property.__init__(self, name=self.linkName, **kwargs)

        # The 'value_property' is the URI used in the RDF graph pointing
        # from this property to its value. It is a different value for
        # each property type.
        self.value_property = self.rdf_namespace['value']

        # 'v' holds values that have been set on this SimpleProperty. It acts
        # as a sort of staging area before saving the values to the graph.
        self.v = []

        if self.owner != False:
            self.link = self.owner_type.rdf_namespace[self.linkName]

    def hasValue(self):
        """ Returns true if the ``Property`` has had ``load`` called previously and some value was available or if ``set`` has been called previously """
        return len(self.v) > 0

    @classmethod
    def _id_hash(cls, value):
        assert(isinstance(value, str))
        return hashlib.md5(value.encode()).hexdigest()

    def get(self):
        """ If the ``Property`` has had ``load`` or ``set`` called previously, returns
        the resulting values. Also queries the configured rdf graph for values
        which are set for the ``Property``'s owner.
        """

        returned = set() # collection of returned values so we don't send them multiple times

        for x in self.v:
            if x.value not in returned:
                returned.add(x.value)
                yield x.value

        gp = self.graph_pattern(query=True)

        var = R.Variable(self._id_hash(self.identifier(query=True)) +"_value")
        q = "SELECT DISTINCT " + var.n3() + " WHERE { " + gp + " }"
        qres = self.rdf.query(q)
        for x in qres:
            if x[0] not in returned:
                returned.add(x[0])
                if self.property_type == 'ObjectProperty':
                    yield self.object_from_id(x[0])
                else:
                    yield x[0]

    def set(self,v):
        import bisect
        v = PropertyValue(self.property_type, v)
        if self.multiple:
            bisect.insort(self.v, v)
        else:
            self.v = [v]

    def triples(self,*args,**kwargs):
        """ Yields the triples for describing a simple property """

        query=kwargs.get('query',False)

        if not (query or self.hasValue()):
            return

        if not kwargs.get('visited_list', False):
            kwargs['visited_list'] = set()

        if self.identifier(query=query) in kwargs['visited_list']:
            return
        else:
            kwargs['visited_list'].add(self.identifier(query=query))


        ident = self.identifier(query=query)

        if query and (len(self.v) == 0):
            part = self._id_hash(self.identifier(query=query))
            yield (ident, self.rdf_namespace['value'], R.Variable(part+"_value") )
            # XXX: It may be good to send out the triples for our owner as well so
            #      that, in some sense, the property is completely specified for
            #      the purposes of querying.
            for x in self.owner.triples(*args, **kwargs):
                yield x
        elif len(self.v) > 0:
            for x in Property.triples(self,*args, **kwargs):
                yield x

            def yield_triples_helper(propertyValue):
                try:
                    yield (ident, self.value_property, propertyValue.identifier(query=query))
                    for t in propertyValue.triples(*args, **kwargs):
                        yield t
                except Exception:
                    traceback.print_exc()
            if self.multiple:
                for x in self.v:
                    for triple in yield_triples_helper(x):
                        yield triple
            else:
                for triple in yield_triples_helper(self.v[0]):
                    yield triple


    def identifier(self,query=False):
        """ Return the URI for this object

        Parameters
        ----------
        query: bool
            Indicates whether the identifier is to be used in a query or not
        """
        if self._id_is_set:
            return DataObject.identifier(self,query=query)
        vlen = len(self.v)

        if vlen > 0:
            value_data = "".join(str(x.identifier(query=query)) for x in self.v if self is not x)
            return self.make_identifier((self.link, value_data))
        return DataObject.identifier(self,query=query)


    def __str__(self):
        return str(self.linkName + "=" + str(";".join(str(x) for x in self.v)))

class DatatypeProperty(SimpleProperty):
    pass

class ObjectProperty(SimpleProperty):
    pass

class PropertyValue(object):
    def __init__(self, property_type, value=None):
        if property_type == 'DatatypeProperty':
            self.vtype = 'literal'
            self.value = R.Literal(value)
        else:
            self.vtype = 'object'
            self.value = value

    def triples(self, *args, **kwargs):
        if self.vtype == 'object':
            for t in self.value.triples(*args,**kwargs):
                yield t

    def identifier(self, query=False):
        if self.vtype == 'object':
            return self.value.identifier(query=query)
        elif self.vtype == 'literal':
            return self.value
        else:
            raise Exception("A property's value type must be either 'literal' or 'object'")

    def __hash__(self):
        return hash(self.value)

    def __str__(self):
        return "<" + str(self.value) + ">"

    def __repr__(self):
        return str(self)

    def __lt__(self, other):
        return self.value < other.value

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
        DataObject.__init__(self,**kwargs)
        self.add = self.member
        self.group_name = self.name
        self.name(group_name)

    def identifier(self, query=False):
        return self.make_identifier(self.group_name)
