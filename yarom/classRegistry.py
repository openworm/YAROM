import yarom as Y
import rdflib as R

# TODO Generate key for the RegistryEntry type as a combination of the ClassDescription>classKey and rdfClass
# TODO Generate RegistryEntry objects for all mapped classes automatically
rns = R.Namespace("yarom/PythonClassRegistry/schema#")


class _RegistryEntryType(Y.mapper.MappedClass):

    def __init__(cls, *args):
        cls.rdf_type = rns["RegistryEntry"]
        cls.rdf_namespace = R.Namespace(
            cls.conf['rdf.namespace']['PythonClassRegistry'] + "/")
        super().__init__(*args)


class _ClassDescriptionType(Y.mapper.MappedClass):

    def __init__(cls, *args):
        cls.rdf_type = rns["ClassDescription"]
        cls.rdf_namespace = R.Namespace(
            cls.conf['rdf.namespace']['ClassDescription'] + "/")
        super().__init__(*args)


class RegistryEntry(Y.DataObject, metaclass=_RegistryEntryType):

    """ A mapping from a Python class to an RDF class.

    Objects of this type are utilized in the resolution of Python classes from the RDF graph
    """
    _ = ["pythonClass", "rdfClass"]


class ClassDescription(Y.DataObject, metaclass=_ClassDescriptionType):
    _ = ["classKey", "className", "moduleName", "moduleLocation", "priority"]
