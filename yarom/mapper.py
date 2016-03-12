from __future__ import print_function

import importlib as I
import logging
import rdflib as R
from yarom import DataUser
import yarom as Y

__all__ = [
    "MappedClass",
    "MappedPropertyClass",
    "Resolver"]

L = logging.getLogger(__name__)



class Mapper(object):
    instance = None

    @classmethod
    def get_instance(cls):
        if cls.instance is None:
            cls.instance = Mapper()
        return cls.instance

    def __init__(self):
        self.MappedClasses = dict()  # class names to classes
        # class names to parents of the related class
        self.DataObjectsParents = dict()
        self.DataObjectsChildren = dict()
        self.DataObjectProperties = dict()  # Property classes to
        self.RDFTypeTable = dict()  # class rdf types to classes
        self.instance = self

    def remap(self):
        """ Calls `map` on all of the registered classes """
        classes = set(self.MappedClasses.values())
        pclasses = set(self.DataObjectProperties.values())
        oclasses = classes - pclasses

        ordering_map = self.get_class_ordering(oclasses)
        print("oclasses", oclasses)
        sorted_oclasses = sorted(oclasses, key=lambda y: ordering_map[y.__name__])

        print("MAPPING: {}".format(sorted_oclasses))

        for x in sorted_oclasses:
            x.map()
        for x in pclasses:
            x.map()

    def get_class_ordering(self, l):
        res = dict()
        base = self.get_base_class()
        print("base class", base)
        def igen():
            i = 0
            while True:
                yield i
                i += 1

        def helper(current, gen):
            n = current.__name__
            res[n] = next(gen)
            children = self.DataObjectsChildren.get(n,())
            for c in children:
                helper(c, gen)
        helper(base, igen())
        print(res)
        return res

    def get_base_class(self):
        first = next(self.DataObjectsParents.iterkeys())
        def helper(key):
            parents = self.DataObjectsParents[key]
            if len(parents) == 0:
                return self.MappedClasses[key]
            else:
                return helper(parents[0].__name__)
        return helper(first)

    def unmap_all(self):
        for cls in self.MappedClasses:
            cls.unmap()

    def deregister_all(self):
        keys = list(self.MappedClasses.keys())
        for cname in keys:
            self.MappedClasses[cname].deregister()

    def resolve_classes_from_rdf(self, graph):
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
            self.resolve_class(x)

    def resolve_class(self, uri):
        cr = self.load_module('yarom.classRegistry')
        # look up the class in the registryCache
        if uri in self.RDFTypeTable:
            # if it is in the regCache, then return the class;
            return self.RDFTypeTable[uri]
        else:
            # otherwise, attempt to load into the cache by
            # reading the RDF graph.
            re = cr.RegistryEntry()
            re.rdfClass(uri)
            for cd in self.get_class_descriptions(re):
                # TODO: if load fails, attempt to construct the class
                return self.load_class_from_description(cd)

    def load_class_from_description(self, cd):
        # TODO: Undo the effects to YAROM of loading a class when the
        #       module doesn't, in fact, have the class being searched
        #       for.
        mod_name = cd.moduleName.one()
        class_name = cd.className.one()
        self.load_module(mod_name)
        mod = Y
        if mod is not None:
            if hasattr(mod, class_name):
                cls = getattr(mod, class_name)
                if cls is not None:
                    return cls
            else:
                raise Exception("Cannot find class " + class_name)

    def get_class_descriptions(self, re):
        mod_data = []
        for x in re.load():
            for y in x.pythonClass():
                mod_data.append(y)
        return mod_data

    def load_module(self, module_name):
        L.debug("LOADING", module_name)
        a = I.import_module(module_name)
        return a

    def reload_module(self, mod):
        from six.moves import reload_module
        L.debug("RE-LOADING", mod)
        a = reload_module(mod)
        return a

    def oid(self, identifier_or_rdf_type, rdf_type=False):
        """ Create an object from its rdf type

        Parameters
        ----------
        identifier_or_rdf_type : :class:`str` or :class:`rdflib.term.URIRef`
            If `rdf_type` is provided, then this value is used as the identifier
            for the newly created object. Otherwise, this value will be the
            :attr:`rdf_type` of the object used to determine the Python type and
            the object's identifier will be randomly generated.
        rdf_type : :class:`str`, :class:`rdflib.term.URIRef`, :const:`False`
            If provided, this will be the :attr:`rdf_type` of the newly created
            object.

        Returns
        -------
           The newly created object

        """
        identifier = identifier_or_rdf_type
        if not rdf_type:
            rdf_type = identifier_or_rdf_type
            identifier = False

        L.debug("oid making a {} with ident {}".format(rdf_type, identifier))
        c = self.RDFTypeTable[rdf_type]
        # if its our class name, then make our own object
        # if there's a part after that, that's the property name
        o = None
        if identifier:
            o = c(ident=identifier)
        else:
            o = c(generate_key=True)
        return o

    def get_most_specific_rdf_type(self, types):
        """ Gets the most specific rdf_type.

        Returns the URI corresponding to the lowest in the DataObject class
        hierarchy from among the given URIs.
        """
        # TODO: Use the MappedClasses and DataObjectsParents to get the root
        do = self.load_module('yarom.dataObject')
        least = do.DataObject
        for x in types:
            try:
                if self.RDFTypeTable[x] < least:
                    least = self.RDFTypeTable[x]
            except KeyError:
                pass
        return least.rdf_type
