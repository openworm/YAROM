from .dataUser import DataUser

__all__ = ["Property"]


class Property(DataUser):

    """ Store a value associated with a DataObject

    Properties can be be accessed like methods. A method call like::

        a.P()

    for a property ``P`` will return values appropriate to that property for
    ``a``, the `owner` of the property.

    Parameters
    ----------
    owner : yarom.dataObject.DataObject
        The owner of this property
    name : string
        The name of this property. Can be accessed as an attribute like::

            owner.name

    """

    # Indicates whether the Property is multi-valued
    multiple = False
    link = None
    linkName = None

    def __init__(self, owner=False, **kwargs):
        super(Property, self).__init__(**kwargs)
        self.owner = owner

    def get(self, *args):
        """
        Get the things which are on the other side of this property

        The return value must be iterable. For a ``get`` that just returns
        a single value, an easy way to make an iterable is to wrap the
        value in a tuple like ``(value,)``.

        Derived classes must override.
        """

        raise NotImplementedError()

    def set(self, *args, **kwargs):
        """
        Set the value of this property

        Derived classes must override.
        """

        raise NotImplementedError()

    def one(self):
        """
        Returns a single value for the ``Property`` whether or not it is
        multivalued.
        """

        try:
            r = self.get()
            return next(iter(r))
        except StopIteration:
            return None

    def hasValue(self):
        """
        Returns true if the Property has any values set on it.

        This may be defined differently for each property
        """
        return False

    @property
    def values(self):
        raise NotImplementedError()

    def __call__(self, *args, **kwargs):
        """
        If arguments are passed to the ``Property``, its ``set`` method is
        called. Otherwise, the ``get`` method is called. If the ``multiple``
        member for the ``Property`` is set to ``True``, then a Python set
        containing the associated values is returned. Otherwise, a single bare
        value is returned.
        """

        if len(args) > 0 or len(kwargs) > 0:
            return self.set(*args, **kwargs)
        else:
            r = self.get(*args, **kwargs)
            if self.multiple:
                return set(r)
            else:
                try:
                    return next(iter(r))
                except StopIteration:
                    return None
