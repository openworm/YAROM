from .rdfTypeResolver import RDFTypeResolver
from .mapper import Mapper


class Resolver(RDFTypeResolver):
    instance = None

    @classmethod
    def get_instance(cls):
        from .dataObject import DataObject
        from .rdfUtils import deserialize_rdflib_term
        if cls.instance is None:
            cls.instance = RDFTypeResolver(
                DataObject.rdf_type,
                Mapper.get_instance().get_most_specific_rdf_type,
                Mapper.get_instance().oid,
                deserialize_rdflib_term)
        return cls.instance
