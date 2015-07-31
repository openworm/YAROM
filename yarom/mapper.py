import importlib as I
import traceback
import logging
import rdflib as R
from yarom import DataUser
from .rdfTypeResolver import RDFTypeResolver
import yarom as Y

__all__ = [
    "MappedClass",
    "MappedPropertyClass",
    "MappedClasses",
    "DataObjectsParents",
    "RDFTypeTable",
    "get_most_specific_rdf_type",
    "oid",
    "Resolver",
    "reload_module",
    "load_module"]

L = logging.getLogger(__name__)

MappedClasses = dict()  # class names to classes
DataObjectsParents = dict()  # class names to parents of the related class
DataObjectProperties = dict()  # Property classes to

RDFTypeTable = dict()  # class rdf types to classes

ProplistToProptype = {"datatypeProperties": "DatatypeProperty",
                      "objectProperties": "ObjectProperty",
                      "_": "UnionProperty"
                      }


class MappedClass(type):

    """A type for MappedClasses

    Sets up the graph with things needed for MappedClasses
    """
    def __init__(cls, name, bases, dct):
        type.__init__(cls, name, bases, dct)
        if 'rdf_type' in dct:
            cls.rdf_type = dct['rdf_type']
        else:
            cls.rdf_type = cls.conf['rdf.namespace'][cls.__name__]

        if 'rdf_namespace' in dct:
            cls.rdf_namespace = dct['rdf_namespace']
        else:
            cls.rdf_namespace = R.Namespace(
                cls.conf['rdf.namespace'][cls.__name__] + "/")

        cls.dataObjectProperties = []
        for x in bases:
            try:
                cls.dataObjectProperties += x.dataObjectProperties
            except AttributeError:
                pass
        cls.register()

    @classmethod
    def make_class(
            cls,
            name,
            bases,
            objectProperties=False,
            datatypeProperties=False):
        """ Intended to be used for setting up a class from the RDF graph, for instance. """
        # Need to distinguish datatype and object properties...
        if not datatypeProperties:
            datatypeProperties = []
        if not objectProperties:
            objectProperties = []
        cls(name, bases,
            dict(
                objectProperties=objectProperties,
                datatypeProperties=datatypeProperties))

    @property
    def du(self):
        # This is just a little indirection to make sure we initialize the DataUser property before using it.
        # Initialization isn't done in __init__ because I wanted to make sure you could call `connect` before
        # or after declaring your classes
        if hasattr(self, '_du'):
            return self._du
        else:
            raise Exception("You should have called `map` to get here")

    @du.setter
    def du(self, value):
        assert(isinstance(value, DataUser))
        self._du = value

    def __lt__(cls, other):
        if isinstance(other, MappedPropertyClass):
            return False
        return issubclass(cls, other) or ((not issubclass(other, cls)) \
                    and (cls.__name__ < other.__name__))

    def register(cls):
        """Sets up the object graph related to this class

        :meth:`regsister` never touches the RDF graph itself.

        Also registers the properties of this DataObject
        """
        cls._du = DataUser()
        cls.children = []
        MappedClasses[cls.__name__] = cls
        DataObjectsParents[cls.__name__] = \
                [x for x in cls.__bases__ if isinstance(x, MappedClass)]
        cls.parents = DataObjectsParents[cls.__name__]
        for c in cls.parents:
            c.add_child(cls)

        cls.addProperties('objectProperties')
        cls.addProperties('datatypeProperties')
        cls.addProperties('_')

        if getattr(Y, cls.__name__, False):
            new_name = "_" + cls.__name__
            warnMismapping(
                'yarom module',
                cls.__name__,
                "nothing",
                getattr(
                    Y,
                    cls.__name__))
            if getattr(Y, new_name, False):
                L.warning(
                    "Still unable to add {0} to {1}. {0} will not be accessible through {1}".format(
                        new_name,
                        'yarom module'))
            else:
                setattr(Y, new_name, cls)
        else:
            setattr(Y, cls.__name__, cls)

        return cls

    def deregister(cls):
        """Removes the class from the object graph.

        Should make it possible to garbage collect

        :method:``deregister`` never touches the RDF graph itself.
        """
        if getattr(Y, cls.__name__) == cls:
            delattr(Y, cls.__name__)
        elif getattr(Y, "_" + cls.__name__) == cls:
            delattr(Y, "_" + cls.__name__)

        if cls.__name__ in MappedClasses:
            del MappedClasses[cls.__name__]

        if cls.__name__ in DataObjectsParents:
            del DataObjectsParents[cls.__name__]

        for c in cls.parents:
            c.remove_child(cls)

    def remove_child(cls, child):
        if hasattr(cls, 'children'):
            cls.children.remove(child)
        else:
            raise Exception(
                "Cannot remove child {0} from {1} as {1} has not yet been registered".format(
                    child,
                    cls))

    def add_child(cls, child):
        if hasattr(cls, 'children'):
            cls.children.append(child)
        else:
            raise Exception(
                "Cannot add child {0} to {1} as {1} has not yet been registered".format(
                    child,
                    cls))

    def map(cls):
        """
        Maps the class to the configured rdf graph.
        """
        # NOTE: Map should be quick: it runs for every DataObject sub-class created and possibly
        #       several times in testing
        from .dataObject import TypeDataObject
        cls.rdf_type_object = TypeDataObject(ident=cls.rdf_type)

        RDFTypeTable[cls.rdf_type] = cls

        cls._add_parents_to_graph()
        cls._add_namespace_to_manager()

        return cls

    def unmap(cls):
        """
        Unmaps the class
        """

    def _remove_namespace_from_manager(cls):
        pass
        #cls.du['rdf.namespace_manager'].bind(cls.__name__, "")

    def _add_namespace_to_manager(cls):
        cls.du['rdf.namespace_manager'].bind(
            cls.__name__,
            cls.rdf_namespace,
            replace=True)

    def _add_parents_to_graph(cls):
        from .dataObject import RDFSSubClassOfProperty, DataObject
        for parent in cls.parents:
            ancestors = (x for x in parent.mro() if issubclass(x, DataObject))
            for ancestor in ancestors:
                cls.rdf_type_object.relate(
                    'rdfs_subClassOf',
                    ancestor.rdf_type_object,
                    RDFSSubClassOfProperty)

    def addProperties(cls, listName):
        # TODO: Make an option string to abbreviate these options
        try:
            if hasattr(cls, listName):
                propList = getattr(cls, listName)
                propType = ProplistToProptype[listName]

                assert(isinstance(propList, (tuple, list, set)))
                for x in propList:
                    value_type = None
                    p = None
                    if isinstance(x, tuple):
                        if len(x) > 2:
                            value_type = x[2]
                        p = _create_property(
                            cls,
                            x[0],
                            propType,
                            value_type=value_type)
                    elif isinstance(x, dict):
                        if 'prop' in x:
                            p = DataObjectProperties[x['prop']]
                        else:
                            name = x['name']
                            del x['name']

                            if 'type' in x:
                                value_type = x['type']
                                del x['type']

                            p = _create_property(
                                cls,
                                name,
                                propType,
                                value_type=value_type,
                                **x)
                    else:
                        p = _create_property(cls, x, propType)
                    cls.dataObjectProperties.append(p)
                setattr(cls, '_' + listName, propList)
                setattr(cls, listName, [])
        except:
            traceback.print_exc()

    def _cleanupGraph(cls):
        """ Cleans up the graph by removing statements that can't be connected to typed statement. """
        # XXX: This might belong in DataUser instead
        q = """DELETE { ?b ?x ?y }
        WHERE
        {
            ?b ?x ?y .
            FILTER (NOT EXISTS { ?b rdf:type ?c } ) .
        }"""
        cls.du.rdf.update(q)


def warnMismapping(mapping, key, should_be, is_actually=None):
    if is_actually is None:
        is_actually = mapping[key]

    L.warning(
        "Mismapping of {} in {}. Is {}. Should be {}".format(
            key,
            mapping,
            is_actually,
            should_be))
    raise Exception("Mismapping")


class MappedPropertyClass(type):

    def __init__(cls, name, bases, dct):
        super(MappedPropertyClass, cls).__init__(name, bases, dct)
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

    def deregister(cls):
        if MappedClasses.get(cls.__name__, False) == cls:
            del MappedClasses[cls.__name__]
        else:
            warnMismapping(MappedClasses, cls.__name__, cls)

        if DataObjectProperties.get(cls.__name__, False) == cls:
            del DataObjectProperties[cls.__name__]
        else:
            warnMismapping(DataObjectProperties, cls.__name__, cls)

        if getattr(Y, cls.__name__) == cls:
            setattr(Y, cls.__name__, cls)
        else:
            warnMismapping(dir(Y), cls.__name__, cls)

        return cls

    def map(cls):
        from .dataObject import PropertyDataObject, RDFSDomainProperty, RDFSRangeProperty
        cls.rdf_object = PropertyDataObject(ident=cls.link)
        if hasattr(cls, 'owner_type'):
            cls.rdf_object.relate(
                'rdfs_domain',
                cls.owner_type.rdf_type_object,
                RDFSDomainProperty)

        if hasattr(cls, 'value_type'):
            cls.rdf_object.relate(
                'rdfs_range',
                cls.value_type.rdf_type_object,
                RDFSRangeProperty)

    def __lt__(cls, other):
        return issubclass(cls, other) \
                or isinstance(other, MappedClass) \
                or ((not issubclass(other, cls)) \
                    and (cls.__name__ < other.__name__))


def remap():
    """ Calls `map` on all of the registered classes """
    classes = sorted(list(MappedClasses.values()))
    classes.reverse()
    for x in classes:
        x.map()


def unmap_all():
    for cls in MappedClasses:
        cls.unmap()


def deregister_all():
    global MappedClasses
    keys = list(MappedClasses.keys())
    for cname in keys:
        MappedClasses[cname].deregister()


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
    for x in graph.transitive_subjects(
            R.RDFS['subClassOf'],
            Y.DataObject.rdf_type):
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
            raise Exception("Cannot find class " + class_name)


def get_class_descriptions(re):
    mod_data = []
    for x in re.load():
        for y in x.pythonClass():
            mod_data.append(y)
    return mod_data


def load_module(module_name):
    a = I.import_module(module_name)
    remap()
    return a


def reload_module(mod):
    from six.moves import reload_module
    a = reload_module(mod)
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
    return {k: v for k, v in d.items() if k in s}


def _create_property(
        owner_type,
        linkName,
        property_type,
        value_type=None,
        multiple=True,
        link=None):
    # XXX This should actually get called for all of the properties when their owner
    #    classes are defined.
    # The initialization, however, must happen with the owner object's
    # creation
    from .simpleProperty import ObjectProperty, DatatypeProperty, UnionProperty

    properties = _slice_dict(locals(), ['owner_type', 'linkName', 'multiple'])

    owner_class_name = owner_type.__name__
    property_class_name = owner_class_name + "_" + linkName

    x = None
    if property_type == 'ObjectProperty':
        x = ObjectProperty
        if value_type is None:
            value_type = Y.DataObject
        properties['value_type'] = value_type
        properties['value_rdf_type'] = value_type.rdf_type
    elif property_type == 'DatatypeProperty':
        x = DatatypeProperty
    else:
        x = UnionProperty

    if link is not None:
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
        except KeyError:
            pass
    return least.rdf_type


class Resolver(RDFTypeResolver):
    instance = None

    @classmethod
    def get_instance(cls):
        from .dataObject import DataObject
        from .rdfUtils import deserialize_rdflib_term
        if cls.instance is None:
            cls.instance = RDFTypeResolver(
                DataObject.rdf_type,
                get_most_specific_rdf_type,
                oid,
                deserialize_rdflib_term)
        return cls.instance
