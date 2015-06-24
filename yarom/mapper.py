import rdflib as R
from yarom import DataUser
import logging
import yarom as Y
import traceback

__all__ = [ "MappedClass", "MappedPropertyClass", "MappedClasses", "DataObjectsParents",
            "RDFTypeTable", "get_most_specific_rdf_type", "oid", "load_module"]

L = logging.getLogger(__name__)

MappedClasses = dict() # class names to classes
DataObjectsParents = dict() # class names to parents of the related class
RDFTypeTable = dict() # class rdf types to classes
DataObjectProperties = dict() # Property classes to

ProplistToProptype = { "datatypeProperties" : "DatatypeProperty",
                       "objectProperties"   : "ObjectProperty",
                       "_" : "UnionProperty"
                     }

class MappedClass(type):
    """A type for MappedClasses

    Sets up the graph with things needed for MappedClasses
    """
    def __init__(cls, name, bases, dct):
        type.__init__(cls,name,bases,dct)
        if 'rdf_type' in dct:
            cls.rdf_type = dct['rdf_type']
        else:
            cls.rdf_type = cls.conf['rdf.namespace'][cls.__name__]

        if 'rdf_namespace' in dct:
            cls.rdf_namespace = dct['rdf_namespace']
        else:
            cls.rdf_namespace = R.Namespace(cls.conf['rdf.namespace'][cls.__name__] + "/")

        cls.dataObjectProperties = []
        for x in bases:
            try:
                cls.dataObjectProperties += x.dataObjectProperties
            except AttributeError:
                pass
        cls.register()

    @classmethod
    def make_class(cls, name, bases, objectProperties=False, datatypeProperties=False):
        """ Intended to be used for setting up a class from the RDF graph, for instance. """
        # Need to distinguish datatype and object properties...
        if not datatypeProperties:
            datatypeProperties = []
        if not objectProperties:
            objectProperties = []
        cls(name, bases, dict(objectProperties=objectProperties, datatypeProperties=datatypeProperties))

    @property
    def du(self):
        # This is just a little indirection to make sure we initialize the DataUser property before using it.
        # Initialization isn't done in __init__ because I wanted to make sure you could call `connect` before
        # or after declaring your classes
        if hasattr(self,'_du'):
            return self._du
        else:
            raise Exception("You should have called `map` to get here")

    @du.setter
    def du(self, value):
        assert(isinstance(value,DataUser))
        self._du = value

    def __lt__(cls, other):
        if isinstance(other, MappedPropertyClass):
            return False
        return issubclass(cls,other) or ((not issubclass(other, cls)) and cls.__name__ < other.__name__)

    def register(cls):
        """
        Registers the class as a DataObject to be included in the configured rdf graph.

        Also creates the classes for and registers the properties of this DataObject
        """
        cls._du = DataUser()
        MappedClasses[cls.__name__] = cls
        DataObjectsParents[cls.__name__] = [x for x in cls.__bases__ if isinstance(x, MappedClass)]
        cls.parents = DataObjectsParents[cls.__name__]

        cls.addObjectProperties()
        cls.addDatatypeProperties()
        cls.addSimpleProperties()
        setattr(Y, cls.__name__, cls)

        return cls

    def map(cls):
        """Sets up the object graph related to this class

        ``map`` never touches the RDF graph itself.
        """
        # NOTE: Map should be quick: it runs for every DataObject sub-class created and possibly
        #       several times in testing
        from .dataObject import TypeDataObject
        cls.rdf_type_object = TypeDataObject(ident=cls.rdf_type)

        RDFTypeTable[cls.rdf_type] = cls

        cls.addParentsToGraph()
        cls.addNamespaceToManager()

        return cls

    def addNamespaceToManager(cls):
        cls.du['rdf.namespace_manager'].bind(cls.__name__, cls.rdf_namespace)

    def addParentsToGraph(cls):
        from .dataObject import RDFSSubClassOfProperty,DataObject
        for parent in cls.parents:
            for ancestor in [x for x in parent.mro() if issubclass(x, DataObject)]:
                cls.rdf_type_object.relate('rdfs_subClassOf', ancestor.rdf_type_object, RDFSSubClassOfProperty)

    def addProperties(cls, listName):
        # TODO: Make an option string to abbreviate these options
        try:
            if hasattr(cls, listName):
                propList = getattr(cls, listName)
                propType = ProplistToProptype[listName]

                assert(isinstance(propList, (tuple,list,set)))
                for x in propList:
                    value_type = False
                    p = None
                    if isinstance(x, tuple):
                        if len(x) > 2:
                            value_type = x[2]
                        p = _create_property(cls, x[0], propType, value_type=value_type)
                    elif isinstance(x, dict):
                        if 'prop' in x:
                            p = DataObjectProperties[x['prop']]
                        else:
                            name = x['name']
                            del x['name']

                            if 'type' in x:
                                value_type = x['type']
                                del x['type']

                            p = _create_property(cls, name, propType, value_type=value_type, **x)
                    else:
                        p = _create_property(cls, x, propType)
                    cls.dataObjectProperties.append(p)
                setattr(cls, '_'+listName, propList)
                setattr(cls, listName, [])
        except:
            traceback.print_exc()

    def addObjectProperties(cls):
        cls.addProperties('objectProperties')

    def addDatatypeProperties(cls):
        cls.addProperties('datatypeProperties')

    def addSimpleProperties(cls):
        cls.addProperties('_')

    def _cleanupGraph(cls):
        """ Cleans up the graph by removing statements that can't be connected to typed statement. """
        # XXX: This might belong in DataUser instead
        q = """
        DELETE { ?b ?x ?y }
        WHERE
        {
            ?b ?x ?y .
            FILTER (NOT EXISTS { ?b rdf:type ?c } ) .
        }
          """
        cls.du.rdf.update(q)

class MappedPropertyClass(type):
    def __init__(cls, name, bases, dct):
        type.__init__(cls,name,bases,dct)
        if 'link' not in dct:
            cls.link = cls.conf['rdf.namespace'][cls.__name__]
        else:
            cls.link = dct['link']

        cls.register()

    def register(cls):
        # This is how we create the RDF predicate that points from the owner
        # to this property
        MappedClasses[cls.__name__] = cls
        DataObjectProperties[cls.__name__] = cls

        setattr(Y, cls.__name__, cls)

        return cls

    def map(cls):
        from .dataObject import PropertyDataObject,RDFSDomainProperty,RDFSRangeProperty
        cls.rdf_object = PropertyDataObject(ident=cls.link)
        if hasattr(cls, 'owner_type'):
            cls.rdf_object.relate('rdfs_domain', cls.owner_type.rdf_type_object, RDFSDomainProperty)

        if hasattr(cls, 'value_type'):
            cls.rdf_object.relate('rdfs_range', cls.value_type.rdf_type_object, RDFSRangeProperty)

    def __lt__(cls, other):
        return issubclass(cls,other) or isinstance(other, MappedClass) or ((not issubclass(other, cls)) and cls.__name__ < other.__name__)

def remap():
    """ Calls `map` on all of the registered classes """
    classes = sorted(list(MappedClasses.values()))
    classes.reverse()
    for x in classes:
        x.map()

def resolve_classes_from_rdf(graph):
    """ Gathers Python classes from the RDF graph.

    If there is a remote Python module registered in the RDF graph then an
    import of the module is attempted. If no remote module can be found (i.e.,
    none has been registered or the registered module cannot be retrieved) then
    a subclass of DataObject is generated from data available in the graph
    """
    # get the DataObject class resource
    # get the subclasses of DataObject, transitively
    # take the list of subclasses and resolve them into Python classes
    for x in graph.transitive_subjects( R.RDFS['subClassOf'],Y.DataObject.rdf_type ):
        L.debug("RESOLVING {}".format(x))
        resolve_class(x)

def resolve_class(uri):
    from .classRegistry import RegistryEntry
    # look up the class in the registryCache
    if uri in RDFTypeTable:
        # if it is in the regCache, then return the class;
        return RDFTypeTable[uri]
    else:
        # otherwise, attempt to load into the cache by
        # reading the RDF graph.
        re = RegistryEntry()
        re.rdfClass(uri)
        for cd in get_class_descriptions(re):
            # TODO: if load fails, attempt to construct the class
            return load_class_from_description(cd)

def load_class_from_description(cd):
    # TODO: Undo the effects to YAROM of loading a class when the
    #       module doesn't, in fact, have the class being searched
    #       for.
    mod_name = cd.moduleName.one()
    class_name = cd.className.one()
    load_module(mod_name)
    mod = Y
    if mod is not None:
        if hasattr(mod, class_name):
            cls = getattr(mod, class_name)
            if cls is not None:
                return cls
        else:
            raise Exception("Cannot find class "+class_name)

def get_class_descriptions(re):
    mod_data = []
    for x in re.load():
        for y in x.pythonClass():
            mod_data.append(y)
    return mod_data

def load_module(module_name):
    import importlib as I
    a = I.import_module(module_name)
    remap()
    return a

def oid(identifier_or_rdf_type, rdf_type=False):
    """ Create an object from its rdf type

    Parameters
    ----------
    identifier_or_rdf_type : :class:`str` or :class:`rdflib.term.URIRef`
        If `rdf_type` is provided, then this value is used as the identifier
        for the newly created object. Otherwise, this value will be the
        :attr:`rdf_type` of the object used to determine the Python type and the
        object's identifier will be randomly generated.
    rdf_type : :class:`str`, :class:`rdflib.term.URIRef`, :const:`False`
        If provided, this will be the :attr:`rdf_type` of the newly created object.

    Returns
    -------
       The newly created object

    """
    identifier = identifier_or_rdf_type
    if not rdf_type:
        rdf_type = identifier_or_rdf_type
        identifier = False

    L.debug("oid making a {} with ident {}".format(rdf_type, identifier))
    c = RDFTypeTable[rdf_type]
    # if its our class name, then make our own object
    # if there's a part after that, that's the property name
    o = None
    if identifier:
        o = c(ident=identifier)
    else:
        o = c(generate_key=True)
    return o

def _slice_dict(d, s):
    return {k:v for k,v in d.items() if k in s}

def _create_property(owner_type, linkName, property_type, value_type=False, multiple=True, link=False):
    #XXX This should actually get called for all of the properties when their owner
    #    classes are defined.
    #    The initialization, however, must happen with the owner object's creation
    from .simpleProperty import ObjectProperty, DatatypeProperty, UnionProperty


    properties = _slice_dict(locals(), ['owner_type', 'linkName', 'multiple'])

    owner_class_name = owner_type.__name__
    property_class_name = owner_class_name + "_" + linkName

    x = None
    if property_type == 'ObjectProperty':
        x = ObjectProperty
        if value_type == False:
            value_type = Y.DataObject
        properties['value_type'] = value_type
    elif property_type == 'DatatypeProperty':
        x = DatatypeProperty
    else:
        x = UnionProperty

    if link:
        properties['link'] = link
    else:
        properties['link'] = owner_type.rdf_namespace[linkName]

    c = MappedPropertyClass(property_class_name, (x,), properties)
    return c

def get_most_specific_rdf_type(types):
    """ Gets the most specific rdf_type.

    Returns the URI corresponding to the lowest in the DataObject class hierarchy
    from among the given URIs.
    """
    from .dataObject import DataObject
    least = DataObject
    for x in types:
        try:
            if RDFTypeTable[x] < least:
                least = RDFTypeTable[x]
        except KeyError as e:
            pass
    return least.rdf_type

