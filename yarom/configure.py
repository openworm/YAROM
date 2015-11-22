#
# a class for modules that need outside objects to parameterize their behavior
# Modules inherit from this class and use their
# self['expected_configured_property']
import traceback


class ConfigValue(object):

    """ A value to be configured.

    Elements of a :class:`Configuration` are, in fact, :class:`ConfigValue` objects. They
    can be resolved an arbitrary time after the :class:`Configuration` object is created
    by calling :meth:`get`.
    """

    def get(self):
        """ Override this method to return a value when a configuration variable is accessed"""
        raise NotImplementedError


class _C(ConfigValue):

    """ A helper class that simply stores a value and can report it back with the get method.
        Subclasses ConfigValue and implements the get method.
    """

    def __init__(self, v):
        self.v = v

    def get(self):
        return self.v

    def __str__(self):
        return str(self.v)

    def __repr__(self):
        return repr(self.v)


class BadConf(Exception):

    """ Special exception subclass for alerting the user to a bad configuration
    """
    pass


class _link(ConfigValue):

    """ Helper class that groups values within a Configuration
    """

    def __init__(self, members, c):
        self.members = members
        self.conf = c

    def get(self):
        return self.conf[self.members[0]]


class Configuration(object):

    """ A simple configuration object.  Enables setting and getting key-value pairs"""
    # conf: is a configure instance to base this one on
    # dependencies are required for this class to be initialized (TODO)

    def __init__(self, **kwargs):
        for x in kwargs:
            if not isinstance(kwargs[x], ConfigValue):
                kwargs[x] = _C(kwargs[x])
        self._properties = kwargs

    def __setitem__(self, pname, value):
        if not isinstance(value, ConfigValue):
            value = _C(value)
        if (pname in self._properties) and isinstance(
                self._properties[pname], _link):
            for x in self._properties[pname].members:
                self._properties[x] = value
        else:
            self._properties[pname] = value

    def __getitem__(self, pname):
        return self._properties[pname].get()

    def __iter__(self):
        return iter(self._properties)

    def link(self, *names):
        """ Call link() with the names of configuration values that should
        always be the same to link them together
        """
        l = _link(names, self)
        for n in names:
            self._properties[n] = l

    def __contains__(self, thing):
        return (thing in self._properties)

    def __str__(self):
        return "\n".join(
            "%s = %s" %
            (k, self._properties[k]) for k in self._properties)

    def __repr__(self):
        return (
            "Configuration(**{\n" +
            ",\n".join(
                "{} : {}".format(
                    repr(k),
                    repr(
                        self._properties[k])) for k in self._properties) +
            "})")

    def __len__(self):
        return len(self._properties)

    @classmethod
    def open(cls, file_name):
        """ Open a configuration file and read it to build the internal state.

        Parameters
        ----------
        file_name : str
            The name of a configuration file encoded as JSON

        Returns
        -------
        Configuration
            a Configuration object with the configuration taken from the JSON file
        """
        import json
        with open(file_name) as f:
            c = Configuration()
            d = json.load(f)
            for k in d:
                c[k] = _C(d[k])
        c['configure.file_location'] = file_name
        return c

    def copy(self, other):
        """ Copy configuration values from a different object.

        Parameters
        ----------
        other : dict or Configuration
            A dict or Configuration object to copy the configuration from

        Returns
        -------
        self
        """
        if isinstance(other, Configuration):
            self._properties = dict(other._properties)
        elif isinstance(other, dict):
            for x in other:
                self[x] = other[x]
        return self

    def get(self, pname, default=None):
        """ Retrieve a configuration value.

        Parameters
        ----------
        pname : str
            The key of the value to return.
        default : object
            The value to return if there is no value corresponding to the given key

        Returns
        -------
        object
            The value corresponding to the key in pname or `default` if none is
            available and a default is provided.

        Raises
        ------
        KeyError
            If the given key has no associated value and no default is provided
        """
        if pname in self._properties:
            return self._properties[pname].get()
        elif (default is not None):
            return default
        else:
            traceback.print_stack()
            raise KeyError(pname)


class Configureable(object):

    """ An object which can be configured.

    A ``Configureable`` object can access a :class:`Configuration` object,
    ``Configureable.conf``, which is shared among all ``Configureable`` objects.

    The configuration variables which can affect the behavior of a class should
    be documented in the ``configuration_variables`` class variable. This table
    will be checked on each access of ``Configureable.conf``
    """

    conf = Configuration()
    """ The configuration """

    configuration_variables = dict()
    """ A table of configuration values used by the Configureable object for the
    purpose of documentation.

    The table is indexed by the configuration value. Among the data included in
    the table should be:

    - a "description" which describes how the configuration value is used
      *within the configureable object*: broad generalization about the variable
      shouldn't be here.

    - a "type" for the value of the config may also be included and may be a
      Python ``type`` or just a string description. This isn't at all intended
      to be used for type checking, but *is purely descriptive*.

    - a "directly_configureable" indicator which should be set to ``True`` if the
      value passed in to the object for configuration variable is used more-or-
      less directly by the object. Sanitization of the value or translation into
      a more specific form are acceptable for a variable that is nonetheless
      directly_configureable. On the other hand, a configuration variable that
      has its value set within the object should have directly_configureable set
      to ``False``.
    """

    def __init__(self, conf=None):
        pass

    @classmethod
    def setConf(cls, conf):
        cls.conf = conf

    def __getitem__(self, k):
        return self.conf.get(k)

    def __setitem__(self, k, v):
        self.conf[k] = v

    def get(self, pname, default=False):
        return self.conf.get(pname, default)
