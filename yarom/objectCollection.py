from .dataObject import DataObject


class ObjectCollection(DataObject):

    """
    A convenience class for working with a collection of objects

    Example::

        v = ObjectCollection('unc-13 neurons and muscles')
        n = P.Neuron()
        m = P.Muscle()
        n.receptor('UNC-13')
        m.receptor('UNC-13')
        for x in n.load():
            v.value(x)
        for x in m.load():
            v.value(x)
        # Save the group for later use
        v.save()
        ...
        # get the list back
        u = ObjectCollection('unc-13 neurons and muscles')
        nm = list(u.value())


    Parameters
    ----------
    group_name : string
        A name of the group of objects

    Attributes
    ----------
    name : DatatypeProperty
        The name of the group of objects
    group_name : DataObject
        an alias for ``name``
    member : ObjectProperty
        An object in the group
    add : ObjectProperty
        an alias for ``value``

    """
    _ = ['member']
    datatypeProperties = [{'name': 'name', 'multiple': False}]

    def __init__(self, group_name=False, **kwargs):
        super(ObjectCollection, self).__init__(key=group_name, **kwargs)
        self.add = self.member
        self.group_name = self.name
        self.name(group_name)

    def identifier(self, query=False):
        return self.make_identifier(self.group_name)
