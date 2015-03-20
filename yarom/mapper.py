import rdflib as R
from yarom import DataUser
import yarom as P
import traceback

__all__ = [ "MappedClass", "MappedPropertyClass", "MappedClasses", "DataObjectsParents",
            "RDFTypeTable", "makeDatatypeProperty", "makeObjectProperty",
            "get_most_specific_rdf_type", "oid"]

MappedClasses = dict() # class names to classes
DataObjectsParents = dict() # class names to parents of the related class
RDFTypeTable = dict() # class rdf types to classes
DataObjectProperties = dict() # Property classes to

ProplistToProptype = { "datatypeProperties" : "DatatypeProperty",
                       "objectProperties"   : "ObjectProperty",
                       "simpleProperties"   : "SimpleProperty" }

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

        cls.dataObjectProperties = []
        for x in bases:
            try:
                cls.dataObjectProperties += x.dataObjectProperties
            except AttributeError:
                pass
        cls.register()

    @classmethod
    def makeClass(cls, name, bases, objectProperties=False, datatypeProperties=False):
        """ Intended to be used for setting up a class from the RDF graph, for instance. """
        # Need to distinguish datatype and object properties...
        if not datatypeProperties:
            datatypeProperties = []
        if not objectProperties:
            objectProperties = []
        MappedClass(name, bases, dict(objectProperties=objectProperties, datatypeProperties=datatypeProperties))

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
        cls.rdf_namespace = R.Namespace(cls.rdf_type + "/")

        cls.addObjectProperties()
        cls.addDatatypeProperties()
        setattr(P, cls.__name__, cls)

        return cls

    def map(cls):
        """Sets up the object graph related to this class

        ``map`` never touches the RDF graph itself.
        """
        # NOTE: Map should be quick: it runs for every DataObject sub-class created and possibly
        #       several times in testing
        from .dataObject import DataObjectType
        cls.rdf_type_object = DataObjectType(cls.rdf_type)

        RDFTypeTable[cls.rdf_type] = cls

        cls.addParentsToGraph()
        cls.addNamespaceToManager()

        return cls

    @classmethod
    def remap(metacls):
        """ Calls `map` on all of the registered classes """
        classes = sorted(list(MappedClasses.values()))
        classes.reverse()
        for x in classes:
            x.map()

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
        #
        # This is how we create the RDF predicate that points from the owner
        # to this property
        MappedClasses[cls.__name__] = cls
        #DataObjectProperties[cls.__name__] = cls
        # XXX: Maybe have sub-properties set-up here?
        #DataObjectsParents[cls.__name__] = [x for x in cls.__bases__ if isinstance(x, MappedClass)]
        #cls.parents = DataObjectsParents[cls.__name__]

        setattr(P, cls.__name__, cls)

        return cls

    def map(cls):
        from .dataObject import PropertyDataObject,RDFSDomainProperty,RDFSRangeProperty
        cls.rdf_object = PropertyDataObject(cls.link)
        if hasattr(cls, 'owner_type'):
            cls.rdf_object.relate('rdfs_domain', cls.owner_type.rdf_type_object, RDFSDomainProperty)
        if hasattr(cls, 'value_type'):
            cls.rdf_object.relate('rdfs_range', cls.value_type.rdf_type_object, RDFSRangeProperty)

    def __lt__(cls, other):
        return issubclass(cls,other) or isinstance(other, MappedClass) or ((not issubclass(other, cls)) and cls.__name__ < other.__name__)


def oid(identifier, rdf_type=False):
    """ Load an object from the database using its type tag """
    # XXX: This is a class method because we need to get the conf
    # We should be able to extract the type from the identifier
    if rdf_type:
        uri = rdf_type
    else:
        uri = identifier

    c = RDFTypeTable[uri]
    # if its our class name, then make our own object
    # if there's a part after that, that's the property name
    o = c(ident=identifier)
    return o

def makeDatatypeProperty(*args,**kwargs):
    """ Create a SimpleProperty that has a simple type (string,number,etc) as its value

    Parameters
    ----------
    linkName : string
        The name of this Property.
    """
    return _create_property(*args,property_type='DatatypeProperty',**kwargs)

def makeObjectProperty(*args,**kwargs):
    """ Create a SimpleProperty that has a complex DataObject as its value

    Parameters
    ----------
    linkName : string
        The name of this Property.
    value_type : type
        The type of DataObject fro values of this property
    """
    return _create_property(*args,property_type='ObjectProperty',**kwargs)

def _slice_dict(d, s):
    return {k:v for k,v in d.items() if k in s}


def _create_property(owner_type, linkName, property_type, value_type=False, multiple=True, link=False):
    #XXX This should actually get called for all of the properties when their owner
    #    classes are defined.
    #    The initialization, however, must happen with the owner object's creation
    from .simpleProperty import ObjectProperty, DatatypeProperty


    properties = _slice_dict(locals(), ['owner_type', 'linkName', 'multiple'])

    owner_class_name = owner_type.__name__
    property_class_name = owner_class_name + "_" + linkName

    if value_type == False:
        value_type = P.DataObject

    x = None
    if property_type == 'ObjectProperty':
        properties['value_type'] = value_type
        x = ObjectProperty
    elif property_type == 'DatatypeProperty':
        x = DatatypeProperty
    else:
        x = SimpleProperty

    if link:
        properties['link'] = link
    else:
        properties['link'] = owner_type.rdf_namespace[linkName]
    c = MappedPropertyClass(property_class_name,(x,), properties)
    return c

def get_most_specific_rdf_type(types):
    """ Gets the most specific rdf_type.

    Returns the URI corresponding to the lowest in the DataObject class hierarchy
    from among the given URIs.
    """
    return sorted([RDFTypeTable[x] for x in types])[0].rdf_type

