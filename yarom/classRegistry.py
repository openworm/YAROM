import six
import rdflib as R

import yarom as Y
from yarom import yarom_import

DataObject = yarom_import('yarom.dataObject.DataObject')

# TODO Generate key for the RegistryEntry type as a combination of the
#      ClassDescription.classKey and rdfClass
# TODO Generate RegistryEntry objects for all mapped classes automatically
rns = R.Namespace("yarom/PythonClassRegistry/schema#")


class _RegistryEntryType(Y.mappedClass.MappedClass):

    def __init__(self, *args):
        super(_RegistryEntryType, self).__init__(*args)
        self.rdf_type = rns["RegistryEntry"]

    def on_mapper_add_class(self, mapper):
        super(_RegistryEntryType, self).on_mapper_add_class(mapper)
        self.rdf_namespace = R.Namespace(
            mapper.base_namespace['PythonClassRegistry'] + "/")


class _ClassDescriptionType(Y.mappedClass.MappedClass):

    def __init__(self, *args):
        super(_ClassDescriptionType, self).__init__(*args)
        self.rdf_type = rns["ClassDescription"]

    def on_mapper_add_class(self, mapper):
        super(_ClassDescriptionType, self).on_mapper_add_class(mapper)
        self.rdf_namespace = R.Namespace(
            mapper.base_namespace['ClassDescription'] + "/")


class RegistryEntry(six.with_metaclass(_RegistryEntryType, DataObject)):

    """ A mapping from a Python class to an RDF class.

    Objects of this type are utilized in the resolution of Python classes from
    the RDF graph
    """
    _ = ["pythonClass", "rdfClass"]


class ClassDescription(six.with_metaclass(_ClassDescriptionType, DataObject)):
    _ = ["classKey", "className", "moduleName", "moduleLocation", "priority"]
