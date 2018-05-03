from __future__ import print_function

import logging
import six
import rdflib as R
from .dataUser import DataUser
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
    def __init__(self, name, bases, dct):
        L.debug("INITIALIZING %s", name)
        super(MappedClass, self).__init__(name, bases, dct)
        if 'auto_mapped' in dct:
            self.mapped = True
        else:
            self.mapped = False

        self.__rdf_type = None
        # Set the rdf_type early
        if 'rdf_type' in dct:
            self.__rdf_type = dct['rdf_type']

        if self.__rdf_type is None:
            self.__rdf_type = self.base_namespace[self.__name__]

        self.__rdf_namespace = None
        rdf_ns = dct.get('rdf_namespace', None)
        if rdf_ns is not None:
            L.debug("Setting rdf_namespace to {}".format(rdf_ns))
            self.__rdf_namespace = rdf_ns

        if self.__rdf_namespace is None:
            L.debug("Setting rdf_namespace to {}".format(self.base_namespace[self.__name__]))
            self.__rdf_namespace = R.Namespace(
                self.base_namespace[self.__name__] + "/")

        self._du = None
        self.dataObjectProperties = []
        self.children = []
        for x in bases:
            try:
                self.dataObjectProperties += x.dataObjectProperties
            except AttributeError:
                pass

    @property
    def rdf_type(self):
        return self.__rdf_type

    @rdf_type.setter
    def rdf_type(self, new_type):
        if not isinstance(new_type, R.URIRef) and \
                isinstance(new_type, (str, six.text_type)):
            new_type = R.URIRef(new_type)
        self.__rdf_type = new_type

    @property
    def rdf_namespace(self):
        return self.__rdf_namespace

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
            dict(objectProperties=objectProperties,
                 datatypeProperties=datatypeProperties))

    @property
    def du(self):
        # This is just a little indirection to make sure we initialize the
        # DataUser property before using it. Initialization isn't done in
        # __init__ because I wanted to make sure you could call `connect`
        # before or after declaring your classes
        if not self._du:
            self._du = DataUser()
        return self._du

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

    def on_mapper_add_class(self, mapper):
        """ Called by :class:`yarom.mapper.Mapper`

        Registers certain properties of the class
        """
        self.mapper = mapper
        L.debug("REGISTERING %s", self.__name__)
        parents = self.__bases__
        mapped_parents = tuple(x for x in parents
                               if isinstance(x, MappedClass))

        for c in mapped_parents:
            c.add_child(self)

        self.parents = mapped_parents

        self.addProperties('objectProperties')
        self.addProperties('datatypeProperties')
        self.addProperties('_')

        return self

    def after_mapper_module_load(self, mapper):
        """ Called after all classes in a module have been loaded """

    def on_mapper_remove_class(self, mapper):
        L.debug("DEREGISTERING %s", self.__name__)

        for c in self.parents:
            c.remove_child(self)

    def remove_child(self, child):
        if hasattr(self, 'children'):
            L.debug('removing child %s@0x%x %s@0x%x',
                    self, id(self), child, id(child))
            self.children.remove(child)
        else:
            raise Exception(
                "Cannot remove child {0} from {1} as {1} has not yet "
                "been registered".format(
                    child,
                    self))

    def add_child(self, child):
        if hasattr(self, 'children'):
            L.debug('adding child %s@0x%x %s@0x%x',
                    self, id(self), child, id(child))
            self.children.append(child)
        else:
            raise Exception(
                "Cannot add child {0} to {1} "
                "as {1} has not yet been registered".format(
                    child,
                    self))

    def map(self):
        """
        Maps the class to the configured rdf graph.
        """
        # NOTE: Map should be quick: it runs for every DataObject sub-class
        #       created and possibly several times in testing
        L.debug("MAPPING %s", self.__name__)
        TypeDataObject = \
            self.mapper.lookup_class('yarom.dataObject.TypeDataObject')
        TypeDataObject.mapped = True

        self.rdf_type_object = TypeDataObject(ident=self.rdf_type)

        self._add_parents_to_graph()
        self.mapped = True

        return self

    def unmap(cls):
        """
        Unmaps the class
        """
        L.debug("UNMAPPING %s", cls.__name__)
        del cls.mapper.RDFTypeTable[cls.__rdf_type]
        # XXX: What else to do here?

    def _remove_namespace_from_manager(cls):
        # XXX: Only way I can think to do this is to remake the ns manager
        pass

    def _add_namespace_to_manager(self):
        self.du['rdf.namespace_manager'].bind(
            self.__name__,
            self.__rdf_namespace,
            replace=True)

    def _add_parents_to_graph(self):
        m = self.mapper.modules['yarom.dataObject']
        L.debug('adding parents for %s', self)
        for parent in self.parents:
            ancestors = (x for x in parent.mro()
                         if issubclass(x, m.DataObject))
            for ancestor in ancestors:
                self.rdf_type_object.relate(
                    'rdfs_subClassOf',
                    ancestor.rdf_type_object,
                    m.RDFSSubClassOfProperty)

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
                        p = cls.mapper.MappedClasses[x['prop']]
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
    mapper = owner_type.mapper
    ysp = mapper.load_module('yarom.simpleProperty')
    do = mapper.load_module('yarom.dataObject')

    properties = slice_dict(locals(), ['owner_type', 'linkName', 'multiple'])

    owner_class_name = owner_type.__name__
    property_class_name = owner_class_name + "_" + linkName

    x = None
    if property_type == 'ObjectProperty':
        x = ysp.ObjectProperty
        if value_type is None:
            value_type = do.DataObject
        properties['value_type'] = value_type
    elif property_type == 'DatatypeProperty':
        x = ysp.DatatypeProperty
    else:
        x = ysp.UnionProperty

    if link is not None:
        properties['link'] = link
    elif (hasattr(owner_type, 'rdf_namespace') and
            owner_type.rdf_namespace is not None):
        properties['link'] = owner_type.rdf_namespace[linkName]
    c = MappedPropertyClass(property_class_name, (x,), properties)
    mapper.add_class(c)
    return c
