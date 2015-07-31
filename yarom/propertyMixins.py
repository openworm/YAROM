import logging
import rdflib
from .variable import Variable

from .rdfUtils import deserialize_rdflib_term

L = logging.getLogger(__name__)

__all__ = ["DatatypePropertyMixin",
           "ObjectPropertyMixin"]


class DatatypePropertyMixin(object):

    def set(self, v):
        from .dataObject import DataObject
        if isinstance(v, DataObject):
            L.warn(
                ('You are attempting to set a DataObject "{}"'
                 ' on {} where a literal is expected.').format(v, self))
        return super(DatatypePropertyMixin, self).set(v)

    def get(self):
        for val in super(DatatypePropertyMixin, self).get():
            yield deserialize_rdflib_term(val)


class ObjectPropertyMixin(object):

    def set(self, v):
        from .dataObject import DataObject
        if not isinstance(v, (DataObject, Variable)):
            raise Exception(
                "An ObjectProperty only accepts DataObject"
                "or Variable instances. Got a " + str(type(v)) + " aka " +
                str(type(v).__bases__))
        return super(ObjectPropertyMixin, self).set(v)

    def get(self):
        from .dataObject import oid, get_most_specific_rdf_type

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

            the_type = get_most_specific_rdf_type(types)
            yield oid(ident, the_type)

class UnionPropertyMixin(object):

    """ A Property that can handle either DataObjects or basic types """

    def set(self, v):
        return super(UnionPropertyMixin, self).set(v)

    def get(self):
        from .dataObject import DataObject
        from .mapper import oid, get_most_specific_rdf_type

        for ident in super(UnionPropertyMixin, self).get():
            if isinstance(ident, rdflib.Literal):
                yield deserialize_rdflib_term(ident)
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
                the_type = DataObject.rdf_type
                if len(types) == 0:
                    L.warn(
                        'UnionProperty.get: Retrieved un-typed URI, "' +
                        ident +
                        '", for a DataObject. Creating a default-typed object')
                else:
                    try:
                        the_type = get_most_specific_rdf_type(types)
                        L.debug("the_type = {}".format(the_type))
                    except:
                        L.warn(
                            'UnionProperty.get: Couldn\'t resolve types for `{}\'. Defaulting to a DataObject typed object'.format(ident))

                yield oid(ident, the_type)

