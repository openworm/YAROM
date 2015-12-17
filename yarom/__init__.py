# -*- coding: utf-8 -*-

"""
Most statements correspond to some action on the database.
Some of these actions may be complex, but intuitively ``a.B()``, the Query form,
will query against the database for the value or values that are related to ``a`` through ``B``;
on the other hand, ``a.B(c)``, the Update form, will add a statement to the database that ``a``
relates to ``c`` through ``B``. For the Update form, a Relationship object describing the
relationship stated is returned as a side-effect of the update.

The Update form can also be accessed through the set() method of a Property and the Query form through the get()
method like::

    a.B.set(c)

and::

    a.B.get()

The get() method also allows for parameterizing the query in ways specific to the Property.

Notes:

- Of course, when these methods communicate with an external database, they may fail due to the database being
  unavailable and the user should be notified if a connection cannot be established in a reasonable time. Also, some
  objects are created by querying the database; these may be made out-of-date in that case.

- ``a : {x_0,...,x_n}`` means ``a`` could have the value of any one of ``x_0`` through ``x_n``

Classes
-------
.. automodule:: yarom.dataObject
.. automodule:: yarom.dataUser
.. automodule:: yarom.data
.. automodule:: yarom.configure
.. automodule:: yarom.graphObject
.. automodule:: yarom.mapper
"""

__version__ = "0.7.2"
__author__ = 'Mark Watts'

import logging
from .configure import Configuration,Configureable,ConfigValue,BadConf
from .data import Data
from .dataUser import DataUser
from .mapper import MappedClass, remap, resolve_classes_from_rdf, reload_module, load_module, deregister_all
from .quantity import Quantity
from .yProperty import Property
from .rdfUtils import *

this_module = __import__('yarom')
this_module.connected = False

L = logging.getLogger(__name__)

def config(key=None):
    if key is None:
        return Configureable.conf
    else:
        return Configureable.conf[key]

def loadConfig(f):
    """ Load configuration for the module """
    Configureable.setConf(Data.open(f))
    return Configureable.conf

def disconnect(c=False):
    """ Close the database """
    m = this_module
    if not m.connected:
        return

    if c == False:
        c = Configureable.conf
    deregister_all() # NOTE: We do NOT unmap on disconnect
    # Note that `c' could be set in one of the previous branches;
    # don't try to simplify this logic.
    if c != False:
        c.closeDatabase()
    m.connected = False

def loadData(data, dataFormat):
    if data:
        config('rdf.graph').parse(data, format=dataFormat)

def connect(conf=False,
            do_logging=False,
            data=False,
            dataFormat='n3'):
    """Load desired configuration and open the database

    Parameters
    ----------
    conf : :class:`str`, :class:`Data <yarom.data.Data>`, :class:`Configuration <yarom.configure.Configuration>` or :class:`dict`, optional
        The configuration for the YAROM connection
    do_logging : bool, optional
        If True, turn on debug level logging. The default is False.
    data : str, optional
        If provided, specifies a file to load into the library.
    dataFormat : str, optional
        If provided, specifies the file format of the file pointed specified by `data`.

        The formats available are those accepted by RDFLib's serializer plugins. 'n3' is the default.
    """
    import atexit
    m = this_module
    if m.connected == True:
        print("yarom already connected")
        return

    if do_logging:
        logging.basicConfig(level=logging.DEBUG)


    setConf(conf)

    Configureable.conf.openDatabase()
    L.info("Connected to database")

    atexit.register(disconnect)

    if hasattr(m,'connected_before'):
        reload_module(m.dataObject)
        reload_module(m.relationship)
        reload_module(m.classRegistry)
    else:
        load_module("yarom.dataObject")
        load_module("yarom.relationship")
        load_module("yarom.classRegistry")

    resolve_classes_from_rdf(Configureable.conf['rdf.graph'])
    remap()
    m.connected = True
    m.connected_before = True
    if data:
        loadData(data, dataFormat)

def setConf(conf):
    """ Set the configuration

    Parameters
    ----------
    conf : str, Data, Configuration or dict, optional
        The configuration to load.

        If a Data object is provided, then it's used as is for the configuration.
        If either a Python dict or a Configuration object are provided, then the
        contents of that object is used to make a Data object for configuration.
        If a string is provided, then the file is read in as JSON to be parsed as
        a dict and from there is treated as if you had passed that dict to
        connect.

        The default action is to attempt to open a file called 'yarom.conf' from
        your current directory as the configuration. Failing that, an 'empty'
        config with default values will be loaded.
    """
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
        except:
            L.info("Couldn't load default configuration")
            Configureable.setConf(Data())

