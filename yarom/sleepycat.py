import logging

from rdflib import ConjunctiveGraph
from .data import RDFSource

L = logging.getLogger(__name__)


class SleepyCatSource(RDFSource):

    """ Reads from and queries against a local Sleepycat database

        The database can be configured like::

            "rdf.source" = "Sleepycat"
            "rdf.store_conf" = <your database location here>
    """
    name = 'sleepycat'

    def open(self):
        # XXX: If we have a source that's read only, should we need to set the
        # store separately??
        g0 = ConjunctiveGraph('Sleepycat')
        self.conf['rdf.store'] = 'Sleepycat'
        g0.open(self.conf['rdf.store_conf'], create=True)
        self.graph = g0
        L.debug("Opened SleepyCatSource")
