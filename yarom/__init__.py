# -*- coding: utf-8 -*-

"""
Most statements correspond to some action on the database. Some of these
actions may be complex, but intuitively ``a.B()``, the Query form, will query
against the database for the value or values that are related to ``a`` through
``B``; on the other hand, ``a.B(c)``, the Update form, will add a statement to
the database that ``a`` relates to ``c`` through ``B``. For the Update form, a
Relationship object describing the relationship stated is returned as a side-
effect of the update.

The Update form can also be accessed through the set() method of a Property and
the Query form through the get() method like::

    a.B.set(c)

and::

    a.B.get()

The get() method also allows for parameterizing the query in ways specific to
the Property.

Notes:

- Of course, when these methods communicate with an external database, they may
  fail due to the database being unavailable and the user should be notified if
  a connection cannot be established in a reasonable time. Also, some objects
  are created by querying the database; these may be made out-of-date in that
  case.

- ``a : {x_0,...,x_n}`` means ``a`` could have the value of any one of ``x_0`` through ``x_n``

Classes
-------
.. automodule:: yarom.dataObject
.. automodule:: yarom.dataUser
.. automodule:: yarom.data
.. automodule:: yarom.zodb
.. automodule:: yarom.configure
.. automodule:: yarom.graphObject
.. automodule:: yarom.mapper
"""


import logging

from .mapper import Mapper

__version__ = "0.10.0"
__author__ = 'Mark Watts'

this_module = __import__('yarom')
this_module.connected = False

L = logging.getLogger(__name__)

DEFAULT_MODULES_TO_LOAD = ["yarom.dataObject",
                           "yarom.objectCollection",
                           "yarom.relationship",
                           "yarom.classRegistry"]

__all__ = ['setConf',
           'config',
           'loadConfig',
           'loadData',
           'connect',
           'disconnect']


MAPPER = None


def yarom_import(cname_or_mname, cnames=None):
    global MAPPER
    if cnames:
        mpart = cname_or_mname
    else:
        mpart, cpart = cname_or_mname.rsplit('.', 1)
        cnames = (cpart,)
    m = MAPPER.load_module(mpart)
    if len(cnames) == 1:
        return getattr(m, cnames[0])
    else:
        return tuple(getattr(m, cname) for cname in cnames)


def yarom_dependency(mname):
    global MAPPER
    MAPPER.add_module_dependency(mname)


def config(key=None, value=None):
    from .configure import Configureable
    if key is None:
        return Configureable.conf
    elif value is None:
        return Configureable.conf[key]
    else:
        Configureable.conf[key] = value


def loadConfig(f):
    """ Load configuration for the module """
    from .configure import Configureable
    from .data import Data
    Configureable.setConf(Data.open(f))
    return Configureable.conf


def disconnect(c=False):
    """ Close the database """
    from .configure import Configureable
    global MAPPER
    m = this_module
    if not m.connected:
        return

    if not c:
        c = Configureable.conf
    MAPPER.deregister_all()  # NOTE: We do NOT unmap on disconnect
    # Note that `c' could be set in one of the previous branches;
    # don't try to simplify this logic.
    if c:
        c.closeDatabase()
    MAPPER = None
    m.connected = False


def loadData(data, dataFormat):
    import rdflib
    if isinstance(data, str):
        config('rdf.graph').parse(data, format=dataFormat)
    elif isinstance(data, rdflib.ConjunctiveGraph):
        g = config('rdf.graph')
        for x in data.quads((None, None, None, None)):
            g.add(x)


def connect(conf=False,
            do_logging=False,
            data=False,
            dataFormat='n3',
            modulesToLoad=None):
    """Load desired configuration and open the database

    Parameters
    ----------
    conf : :class:`str`, :class:`Data <yarom.data.Data>`, :class:`Configuration <yarom.configure.Configuration>` or :class:`dict`, optional
        The configuration for the YAROM connection
    do_logging : bool, optional
        If True, turn on debug level logging. The default is False.
    data : str or rdflib.ConjunctiveGraph, optional
        If provided, specifies a file to load into the library.
    dataFormat : str, optional
        If provided, specifies the file format of the file pointed specified by
        `data`.

        The formats available are those accepted by RDFLib's serializer
        plugins. 'n3' is the default.
    """
    from .configure import Configureable
    from .data import (
        SPARQLSource,
        TrixSource,
        SerializationSource)
    import atexit
    global MAPPER
    if MAPPER is None:
        MAPPER = Mapper(('yarom.dataObject.DataObject',
                         'yarom.simpleProperty.SimpleProperty'))
    m = this_module
    if m.connected:
        print("yarom already connected")
        return

    if do_logging:
        logging.basicConfig(level=logging.DEBUG)
    if modulesToLoad is None:
        modulesToLoad = DEFAULT_MODULES_TO_LOAD

    setConf(conf)
    dbconn = Configureable.conf
    dbconn.register_source(SPARQLSource)
    dbconn.register_source(TrixSource)
    dbconn.register_source(SerializationSource)

    dbconn.openDatabase()
    L.info("Connected to database")

    atexit.register(disconnect)

    for mod in modulesToLoad:
        MAPPER.load_module(mod)

    MAPPER.remap()
    MAPPER.resolve_classes_from_rdf(dbconn['rdf.graph'])
    m.connected = True
    if data:
        loadData(data, dataFormat)


def setConf(conf):
    """ Set the configuration

    Parameters
    ----------
    conf : str, Data, Configuration or dict, optional
        The configuration to load.

        If a Data object is provided, then it's used as is for the
        configuration.

        If either a Python dict or a Configuration object are provided, then the
        contents of that object is used to make a Data object for configuration.

        If a string is provided, then the file is read in as JSON to be parsed as
        a dict and from there is treated as if you had passed that dict to
        connect.

        The default action is to attempt to open a file called 'yarom.conf' from
        your current directory as the configuration. Failing that, an 'empty'
        config with default values will be loaded.
    """
    from .configure import Configuration, Configureable
    from .data import Data
    if conf:
        if isinstance(conf, Data):
            Configureable.setConf(conf)
        elif isinstance(conf, (Configuration, dict)):
            Configureable.setConf(Data(conf))
        elif isinstance(conf, str):
            Configureable.setConf(Data.open(conf))
    else:
        try:
            Configureable.setConf(Data.open("yarom.conf"))
        except Exception:
            L.info("Couldn't load default configuration")
            Configureable.setConf(Data())
