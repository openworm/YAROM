import six
import rdflib as R

import yarom as Y

# TODO Generate key for the RegistryEntry type as a combination of the
#      ClassDescription.classKey and rdfClass
# TODO Generate RegistryEntry objects for all mapped classes automatically
rns = R.Namespace("yarom/PythonClassRegistry/schema#")


class _RegistryEntryType(Y.mappedClass.MappedClass):

    def __init__(cls, *args):
        cls.rdf_type = rns["RegistryEntry"]
        cls.rdf_namespace = R.Namespace(
            cls.conf['rdf.namespace']['PythonClassRegistry'] + "/")
        super(_RegistryEntryType, cls).__init__(*args)


class _ClassDescriptionType(Y.mappedClass.MappedClass):

    def __init__(cls, *args):
        cls.rdf_type = rns["ClassDescription"]
        cls.rdf_namespace = R.Namespace(
            cls.conf['rdf.namespace']['ClassDescription'] + "/")
        super(_ClassDescriptionType, cls).__init__(*args)


class RegistryEntry(six.with_metaclass(_RegistryEntryType, Y.DataObject)):

    """ A mapping from a Python class to an RDF class.

    Objects of this type are utilized in the resolution of Python classes from
    the RDF graph
    """
    _ = ["pythonClass", "rdfClass"]


class ClassDescription(six.with_metaclass(_ClassDescriptionType, Y.DataObject)):
    _ = ["classKey", "className", "moduleName", "moduleLocation", "priority"]
