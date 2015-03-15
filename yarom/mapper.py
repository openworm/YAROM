import rdflib as R
from yarom import DataUser
from .yProperty import *
import yarom as P
import traceback

__all__ = [ "MappedClass", "DataObjects", "DataObjectsParents", "RDFTypeTable", "makeDatatypeProperty", "makeObjectProperty"]

DataObjects = dict() # class names to classes
DataObjectsParents = dict() # class names to parents of the related class
RDFTypeTable = dict() # class rdf types to classes
DataObjectProperties = list() # Property classes to

class MappedClass(type):
    """A type for DataObjects

    Sets up the graph with things needed for DataObjects
    """
    def __init__(cls, name, bases, dct):
        type.__init__(cls,name,bases,dct)

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
        from .dataObject import DataObject,DataObjectType
        return issubclass(cls,other) or ((not issubclass(other, cls)) and cls.__name__ < other.__name__)

    def register(cls):
        """
        Registers the class as a DataObject to be included in the configured rdf graph.

        Also creates the classes for and registers the properties of this DataObject
        """
        DataObjects[cls.__name__] = cls
        DataObjectsParents[cls.__name__] = [x for x in cls.__bases__ if isinstance(x, MappedClass)]
        cls.parents = DataObjectsParents[cls.__name__]
        cls.rdf_type = cls.conf['rdf.namespace'][cls.__name__]
        cls.rdf_namespace = R.Namespace(cls.rdf_type + "/")

        cls.addObjectProperties()
        cls.addDatatypeProperties()
        setattr(P, cls.__name__, cls)

        return cls

    def map(cls):
        """Performs those actions necessary for storing the class and its instances in the graph.

        ``map`` never touches the graph itself.
        """
        # NOTE: Map should be quick: it runs for every DataObject sub-class created and possibly
        #       several times in testing
        from .dataObject import DataObjectType
        cls._du = DataUser()
        cls.rdf_type_object = DataObjectType(cls.rdf_type)

        RDFTypeTable[cls.rdf_type] = cls

        cls.addParentsToGraph()
        cls.addNamespaceToManager()

        return cls

    @classmethod
    def remap(metacls):
        """ Calls `map` on all of the registered classes """
        classes = sorted(list(DataObjects.values()))
        classes.reverse()
        for x in classes:
            x.map()
        metacls.addPropertiesToGraph()

    def addNamespaceToManager(cls):
        cls.conf['rdf.namespace_manager'].bind(cls.__name__, cls.rdf_namespace)

    @classmethod
    def addPropertiesToGraph(metacls):
        # XXX: Use the rdfs predicate for the domain
        from .dataObject import DataObjectProperty,RDFProperty,RDFTypeProperty
        for x in DataObjectProperties:
            if not hasattr(x, "rdf_object"):
                x.rdf_object = DataObjectProperty(x.link)

    def addParentsToGraph(cls):
        from .dataObject import RDFSSubClassOfProperty,DataObject
        for parent in cls.parents:
            for ancestor in [x for x in parent.mro() if issubclass(x, DataObject)]:
                cls.rdf_type_object.relate('rdfs_subClassOf', ancestor.rdf_type_object, RDFSSubClassOfProperty)

    def addObjectProperties(cls):
        try:
            if hasattr(cls, 'objectProperties'):
                assert(isinstance(cls.objectProperties,(tuple,list,set)))
                for x in cls.objectProperties:
                    p = None
                    if isinstance(x, tuple):
                        p = makeObjectProperty(cls, x[0], value_type=x[1], *x[2:])
                    elif isinstance(x, dict):
                        name = x['name']
                        value_type = x.get('type', False)
                        del x['name']
                        if 'type' in x:
                            del x['type']
                        p = makeObjectProperty(cls, name, value_type=value_type, **x)
                    else:
                        p = makeObjectProperty(cls, x)
                    cls.dataObjectProperties.append(p)
                cls._objectProperties = cls.objectProperties
                cls.objectProperties = []
        except:
            traceback.print_exc()

    def addDatatypeProperties(cls):
        # Also get all of the properites
        try:
            if hasattr(cls, 'datatypeProperties'):
                assert(isinstance(cls.datatypeProperties,(tuple,list,set)))
                for x in cls.datatypeProperties:
                    p = None
                    if isinstance(x, tuple):
                        p = makeDatatypeProperty(cls, x[0], *x[1:])
                    elif isinstance(x, dict):
                        name = x['name']
                        del x['name']
                        p = makeDatatypeProperty(cls, name, **x)
                    else:
                        p = makeDatatypeProperty(cls, x)
                    cls.dataObjectProperties.append(p)

        except:
            traceback.print_exc()

    def _cleanupGraph(cls):
        """ Cleans up the graph by removing statements that can't be connected to typed statement. """
        q = """
        DELETE { ?b ?x ?y }
        WHERE
        {
            ?b ?x ?y .
            FILTER (NOT EXISTS { ?b rdf:type ?c } ) .
        }
          """
        cls.du.rdf.update(q)

def oid2(identifier, rdf_type=False):
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
    return {k:v for k,v in d.items() if k==s}

def _create_property(owner_type, linkName, property_type, value_type=False, multiple=False, link=False):
    #XXX This should actually get called for all of the properties when their owner
    #    classes are defined.
    #    The initialization, however, must happen with the owner object's creation


    properties = _slice_dict(locals(), ['owner_type', 'linkName', 'property_type', 'multiple'])

    owner_class_name = owner_type.__name__
    property_class_name = owner_class_name + "_" + linkName

    if value_type == False:
        value_type = P.DataObject

    c = None
    if property_class_name in DataObjects:
        c = DataObjects[property_class_name]
    else:
        x = None
        if property_type == 'ObjectProperty':
            properties['value_rdf_type'] = value_type.rdf_type
            x = ObjectProperty
        else:
            properties['value_rdf_type'] = False
            x = DatatypeProperty

        if link:
            properties['link'] = link
        else:
            properties['link'] = owner_type.rdf_namespace[linkName]
        c = type(property_class_name,(x,), properties)


    # This is how we create the RDF predicate that points from the owner
    # to this property
    DataObjectProperties.append(c)
    return c

def get_most_specific_rdf_type(types):
    """ Gets the most specific rdf_type.

    Returns the URI corresponding to the lowest in the DataObject class hierarchy
    from among the given URIs.
    """
    return sorted([RDFTypeTable[x] for x in types])[0].rdf_type

