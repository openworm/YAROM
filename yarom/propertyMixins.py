import logging
import rdflib

L = logging.getLogger(__name__)

__all__ = ["DatatypePropertyMixin",
           "ObjectPropertyMixin",
           "UnionPropertyMixin"]


class DatatypePropertyMixin(object):

    def __init__(self, resolver, **kwargs):
        """
        Parameters
        ----------
        resolver : RDFTypeResolver
            Resolves RDF identifiers returned from :meth:`get` into objects
        """
        super(DatatypePropertyMixin, self).__init__(**kwargs)
        self._resolver = resolver

    def set(self, v):
        return super(DatatypePropertyMixin, self).set(v)

    def get(self):
        for val in super(DatatypePropertyMixin, self).get():
            yield self._resolver.deserializer(val)


class ObjectPropertyMixin(object):

    def __init__(self, resolver, **kwargs):
        """
        Parameters
        ----------
        resolver : RDFTypeResolver
            Resolves RDF identifiers returned from :meth:`get` into objects
        """
        super(ObjectPropertyMixin, self).__init__(**kwargs)
        self._resolver = resolver

    def set(self, v):
        from .graphObject import GraphObject
        if not isinstance(v, GraphObject):
            raise Exception(
                "An ObjectProperty only accepts GraphObject"
                " instances. Got a " + str(type(v)) + " aka " +
                str(type(v).__bases__))
        return super(ObjectPropertyMixin, self).set(v)

    def get(self):
        for ident in super(ObjectPropertyMixin, self).get():
            if not isinstance(ident, rdflib.URIRef):
                L.warn(
                    'ObjectProperty.get: Skipping non-URI term, "' +
                    str(ident) +
                    '", returned for a DataObject.')
                continue

            types = set()
            types.add(self.value_rdf_type)

            for rdf_type in super(ObjectPropertyMixin, self).rdf.objects(ident, rdflib.RDF['type']):
                types.add(rdf_type)

            the_type = self._resolver.type_resolver(types)
            yield self._resolver.id2ob(ident, the_type)

class UnionPropertyMixin(object):

    """ A Property that can handle either DataObjects or basic types """

    def __init__(self, resolver, **kwargs):
        """
        Parameters
        ----------
        resolver : RDFTypeResolver
            Resolves RDF identifiers into objects returned from :meth:`get`
        """
        super(UnionPropertyMixin, self).__init__(**kwargs)
        self._resolver = resolver

    def set(self, v):
        return super(UnionPropertyMixin, self).set(v)

    def get(self):
        for ident in super(UnionPropertyMixin, self).get():
            if isinstance(ident, rdflib.Literal):
                yield self._resolver.deserializer(ident)
            elif isinstance(ident, rdflib.BNode):
                L.warn(
                    'UnionProperty.get: Retrieved BNode, "' +
                    ident +
                    '". BNodes are not supported in yarom')
            else:
                types = set()
                for rdf_type in super(UnionPropertyMixin, self).rdf.objects(ident, rdflib.RDF['type']):
                    types.add(rdf_type)
                L.debug("{} <- types, {} <- ident".format(types, ident))
                the_type = self._resolver.base_type
                if len(types) == 0:
                    L.warn(
                        'UnionProperty.get: Retrieved un-typed URI, "' +
                        ident +
                        '", for a DataObject. Creating a default-typed object')
                else:
                    try:
                        the_type = self._resolver.type_resolver(types)
                        L.debug("the_type = {}".format(the_type))
                    except:
                        L.warn(
                            'UnionProperty.get: Couldn\'t resolve types for `{}\'. Defaulting to a DataObject typed object'.format(ident))

                yield self._resolver.id2ob(ident, the_type)
