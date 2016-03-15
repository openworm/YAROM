import logging
import yarom as Y

from .mapper import Mapper
from .mapperUtils import log_raise_mismapping_exception

L = logging.getLogger(__name__)


class MappedPropertyClass(type):

    def __init__(cls, name, bases, dct):
        L.debug("INITIALIZING %s", name)
        super(MappedPropertyClass, cls).__init__(name, bases, dct)
        cls.mapper = Mapper.get_instance()
        if 'link' in dct:
            cls.link = dct['link']
        cls.register()

    def register(cls):
        # This is how we create the RDF predicate that points from the owner
        # to this property
        L.debug("REGISTERING %s", cls.__name__)
        cls.mapper.MappedClasses[cls.__name__] = cls
        cls.mapper.DataObjectProperties[cls.__name__] = cls
        # XXX: Should we record class hierarchy of properties?
        setattr(Y, cls.__name__, cls)

        return cls

    def deregister(cls):
        if cls.mapper.MappedClasses.get(cls.__name__, False) == cls:
            del cls.mapper.MappedClasses[cls.__name__]
        else:
            log_raise_mismapping_exception(
                L,
                cls.mapper.MappedClasses,
                cls.__name__,
                cls)

        if cls.mapper.DataObjectProperties.get(
                cls.__name__,
                False) == cls:
            del cls.mapper.DataObjectProperties[cls.__name__]
        else:
            log_raise_mismapping_exception(
                L,
                cls.mapper.DataObjectProperties,
                cls.__name__,
                cls)

        if getattr(Y, cls.__name__) == cls:
            setattr(Y, cls.__name__, cls)
        else:
            log_raise_mismapping_exception(L, dir(Y), cls.__name__, cls)

        return cls

    @property
    def value_rdf_type(self):
        return self.value_type.rdf_type

    def map(cls):
        from .dataObject import (
            PropertyDataObject,
            RDFSDomainProperty,
            RDFSRangeProperty)

        L.debug("MAPPING %s", cls.__name__)
        if cls.link is None:
            if hasattr(cls, 'owner_type'):
                cls.link = cls.owner_type.rdf_namespace[cls.linkName]

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

    def __lt__(self, other):
        res = False
        if issubclass(other, self) and not issubclass(self, other):
            res = True
        elif issubclass(self, other) == issubclass(other, self):
            res = self.__name__ < other.__name__
        return res
