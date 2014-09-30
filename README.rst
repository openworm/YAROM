.. image :: https://travis-ci.org/mwatts15/YAROM.png?branch=master
   :alt: Build Status
   :target: https://travis-ci.org/mwatts15/YAROM

YAROM
=====

Yet Another RDF-Object Mapper (YAROM) is a Python library useful for building Create-Read-Update-Delete (CRUD) tools and applications using Python objects and RDF. YAROM grew out of the `PyOpenWorm <https://github.com/openworm/PyOpenWorm>`_ project.

Basic Usage
-----------

If you got this library from GitHub or as a source archive, then install yarom::

    python setup.py install --user

The configuration establishes which source of RDF data you're reading from. Connect opens necessary resources and must be called before using anything that has to do with the RDF graph.

::

    >>> import yarom as P
    >>> P.connect('yarom/default.conf')
    
    # Do something...
      
    >>> P.disconnect()

Documentation
-------------
Documentation can be found at http://yarom.readthedocs.org/en/latest/
