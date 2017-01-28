import logging
import yarom
import rdflib as R
from .dataUser import DataUser
from .mapper import Mapper
from .mapperUtils import warn_mismapping
from .mappedProperty import MappedPropertyClass
from .utils import slice_dict

L = logging.getLogger(__name__)

ProplistToProptype = {"datatypeProperties": "DatatypeProperty",
                      "objectProperties": "ObjectProperty",
                      "_": "UnionProperty"}


class MappedClass(type):

    """A type for MappedClasses

    Sets up the graph with things needed for MappedClasses
    """
    def __init__(cls, name, bases, dct):
        L.debug("INITIALIZING %s", name)
        type.__init__(cls, name, bases, dct)
        cls.mapper = Mapper.get_instance()
        if 'auto_mapped' in dct:
            cls.mapped = True
        else:
            cls.mapped = False

        # Set the rdf_type early
        if 'rdf_type' in dct:
            cls.rdf_type = dct['rdf_type']
        else:
            cls.rdf_type = None

        if 'rdf_namespace' in dct:
            cls.rdf_namespace = dct['rdf_namespace']
        else:
            cls.rdf_namespace = None

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
        """
        Intended to be used for setting up a class from the RDF graph, for
        instance.
        """
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
        # This is just a little indirection to make sure we initialize the
        # DataUser property before using it. Initialization isn't done in
        # __init__ because I wanted to make sure you could call `connect`
        # before or after declaring your classes
        if hasattr(self, '_du'):
            return self._du
        else:
            raise Exception("You should have called `map` to get here")

    @du.setter
    def du(self, value):
        assert(isinstance(value, DataUser))
        self._du = value

    def __lt__(self, other):
        res = False
        if issubclass(other, self) and not issubclass(self, other):
            res = True
        elif issubclass(self, other) == issubclass(other, self):
            res = self.__name__ < other.__name__
        return res

    def register(cls):
        """Sets up the object graph related to this class

        :meth:`regsister` never touches the RDF graph itself.

        Also registers the properties of this DataObject
        """
        L.debug("REGISTERING %s", cls.__name__)
        cls._du = DataUser()
        cls.children = []
        cls.mapper.MappedClasses[cls.__name__] = cls
        parents = cls.__bases__
        mapped_parents = tuple(x for x in parents
                               if isinstance(x, MappedClass))
        cls.mapper.DataObjectsParents[cls.__name__] = mapped_parents

        for parent in mapped_parents:
            sibs = cls.mapper.DataObjectsChildren.get(parent.__name__, set([]))
            sibs.add(cls.__name__)
            cls.mapper.DataObjectsChildren[parent.__name__] = sibs

        for c in mapped_parents:
            c.add_child(cls)

        cls.parents = mapped_parents

        cls.addProperties('objectProperties')
        cls.addProperties('datatypeProperties')
        cls.addProperties('_')

        if getattr(yarom, cls.__name__, False):
            new_name = "_" + cls.__name__
            warn_mismapping(L,
                            'yarom module',
                            cls.__name__,
                            "nothing",
                            getattr(
                                yarom,
                                cls.__name__))
            if getattr(yarom, new_name, False):
                L.warning(
                    "Still unable to add {0} to {1}. {0} will not be "
                    "accessible through {1}".format(
                        new_name,
                        'yarom module'))
            else:
                setattr(yarom, new_name, cls)
        else:
            setattr(yarom, cls.__name__, cls)

        return cls

    def deregister(cls):
        """Removes the class from the object graph.

        Should make it possible to garbage collect

        :meth:`deregister` never touches the RDF graph itself.
        """
        L.debug("DEREGISTERING %s", cls.__name__)
        if getattr(yarom, cls.__name__) == cls:
            delattr(yarom, cls.__name__)
        elif getattr(yarom, "_" + cls.__name__) == cls:
            delattr(yarom, "_" + cls.__name__)

        if cls.__name__ in cls.mapper.MappedClasses:
            del cls.mapper.MappedClasses[cls.__name__]

        if cls.__name__ in cls.mapper.DataObjectsParents:
            del cls.mapper.DataObjectsParents[cls.__name__]

        for c in cls.parents:
            c.remove_child(cls)
            cls.mapper.DataObjectsChildren[c.__name__].remove(cls.__name__)

    def remove_child(cls, child):
        if hasattr(cls, 'children'):
            cls.children.remove(child)
        else:
            raise Exception(
                "Cannot remove child {0} from {1} as {1} has not yet "
                "been registered".format(
                    child,
                    cls))

    def add_child(cls, child):
        if hasattr(cls, 'children'):
            cls.children.append(child)
        else:
            raise Exception(
                "Cannot add child {0} to {1} "
                "as {1} has not yet been registered".format(
                    child,
                    cls))

    def map(cls):
        """
        Maps the class to the configured rdf graph.
        """
        # NOTE: Map should be quick: it runs for every DataObject sub-class
        #       created and possibly several times in testing
        L.debug("MAPPING %s", cls.__name__)
        from .dataObject import TypeDataObject
        TypeDataObject.mapped = True
        if cls.rdf_type is None:
            cls.rdf_type = cls.conf['rdf.namespace'][cls.__name__]
        if cls.rdf_namespace is None:
            cls.rdf_namespace = R.Namespace(
                cls.conf['rdf.namespace'][cls.__name__] + "/")

        cls.rdf_type_object = TypeDataObject(ident=cls.rdf_type)

        cls.mapper.RDFTypeTable[cls.rdf_type] = cls

        cls._add_parents_to_graph()
        cls._add_namespace_to_manager()
        cls.mapped = True

        return cls

    def unmap(cls):
        """
        Unmaps the class
        """
        L.debug("UNMAPPING %s", cls.__name__)
        del cls.mapper.RDFTypeTable[cls.rdf_type]
        # XXX: What else to do here?

    def _remove_namespace_from_manager(cls):
        # XXX: Only way I can think to do this is to remake the ns manager
        pass

    def _add_namespace_to_manager(cls):
        cls.du['rdf.namespace_manager'].bind(
            cls.__name__,
            cls.rdf_namespace,
            replace=True)

    def _add_parents_to_graph(cls):
        from .dataObject import RDFSSubClassOfProperty, DataObject
        L.debug('adding parents for %s', cls)
        for parent in cls.parents:
            ancestors = (x for x in parent.mro() if issubclass(x, DataObject))
            for ancestor in ancestors:
                cls.rdf_type_object.relate(
                    'rdfs_subClassOf',
                    ancestor.rdf_type_object,
                    RDFSSubClassOfProperty)

    def addProperties(cls, listName):
        # TODO: Make an option string to abbreviate these options
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
                    name = x[0]
                    p = _create_property(
                        cls,
                        name,
                        propType,
                        value_type=value_type)
                elif isinstance(x, dict):
                    if 'prop' in x:
                        p = cls.mapper.DataObjectProperties[x['prop']]
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

    def _cleanupGraph(cls):
        """
        Cleans up the graph by removing statements that can't be connected to
        typed statement.
        """
        # XXX: This might belong in DataUser instead
        q = """DELETE { ?b ?x ?y }
        WHERE
        {
            ?b ?x ?y .
            FILTER (NOT EXISTS { ?b rdf:type ?c } ) .
        }"""
        cls.du.rdf.update(q)


def _create_property(
        owner_type,
        linkName,
        property_type,
        value_type=None,
        multiple=True,
        link=None):
    # XXX: This should actually get called for all of the properties when their
    #      owner classes are defined. The initialization, however, must happen
    #      with the owner object's creation
    from .simpleProperty import ObjectProperty, DatatypeProperty, UnionProperty

    properties = slice_dict(locals(), ['owner_type', 'linkName', 'multiple'])

    owner_class_name = owner_type.__name__
    property_class_name = owner_class_name + "_" + linkName

    x = None
    if property_type == 'ObjectProperty':
        x = ObjectProperty
        if value_type is None:
            value_type = yarom.DataObject
        properties['value_type'] = value_type
    elif property_type == 'DatatypeProperty':
        x = DatatypeProperty
    else:
        x = UnionProperty

    if link is not None:
        properties['link'] = link
    elif (hasattr(owner_type, 'rdf_namespace') and
            owner_type.rdf_namespace is not None):
        properties['link'] = owner_type.rdf_namespace[linkName]
    c = MappedPropertyClass(property_class_name, (x,), properties)
    return c
