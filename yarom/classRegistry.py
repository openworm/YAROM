import rdflib as R

from yarom import yarom_import

DataObject = yarom_import('yarom.dataObject.DataObject')

# TODO Generate key for the RegistryEntry type as a combination of the
#      ClassDescription.classKey and rdfClass
# TODO Generate RegistryEntry objects for all mapped classes automatically
rns = R.Namespace("yarom/PythonClassRegistry/schema#")


class RegistryEntry(DataObject):

    """ A mapping from a Python class to an RDF class.

    Objects of this type are utilized in the resolution of Python classes from
    the RDF graph
    """
    rdf_type = rns["RegistryEntry"]
    rdf_namespace = R.Namespace(rdf_type + '/')
    _ = ["pythonClass", "rdfClass"]


class ClassDescription(DataObject):
    rdf_type = rns["ClassDescription"]
    rdf_namespace = R.Namespace(rdf_type + '/')
    _ = ["classKey", "className", "moduleName", "moduleLocation", "priority"]
